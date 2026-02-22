import os
import shutil
import subprocess

from ..io.logger import logger
from ..io.safe import run_safe_command


class GitService:
    """Helper service for Git and GitHub CLI operations."""

    IGNORE_FILES = [
        "uv.lock",
        "package-lock.json",
        "yarn.lock",
        "poetry.lock",
        "Gemfile.lock",
    ]

    @staticmethod
    def filter_diff(diff_text: str) -> str:
        """Filter out ignored files from a git diff."""
        if not diff_text:
            return ""

        sections = diff_text.split("diff --git ")
        filtered_sections = []

        for section in sections:
            if not section.strip():
                continue

            # First line usually: a/path/to/file b/path/to/file
            first_line = section.split("\n", 1)[0]

            is_ignored = False
            for ignored in GitService.IGNORE_FILES:
                if f"a/{ignored}" in first_line or f"b/{ignored}" in first_line:
                    is_ignored = True
                    break

            if not is_ignored:
                filtered_sections.append(section)

        if not filtered_sections:
            return ""

        # Reconstruct
        result = "diff --git " + "diff --git ".join(filtered_sections)
        # Handle case where split created an empty first element (common)
        if diff_text.startswith("diff --git") and not result.startswith("diff --git"):
            # If our reconstruction missed the prefix because the first section was filtered?
            # No, if we append "diff --git " to join, we are good.
            # But if the original text started with it, the first split element is empty string.
            pass

        return result

    @staticmethod
    def _get_github_client():
        """Get PyGithub client using GITHUB_TOKEN or GH_TOKEN."""
        try:
            from github import Github
            from github import Auth

            token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
            if token:
                auth = Auth.Token(token)
                return Github(auth=auth)
            # Fallback to unauthenticated
            return Github()
        except ImportError:
            return None

    @staticmethod
    def _get_repo_from_remote():
        """Get the 'owner/repo' string from git remote."""
        try:
            result = run_safe_command(
                ["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True
            )
            url = result.stdout.strip()
            if "github.com" in url:
                if url.startswith("git@"):
                    path = url.split("github.com:", 1)[1]
                else:
                    path = url.split("github.com/", 1)[1]
                if path.endswith(".git"):
                    path = path[:-4]
                return path
        except Exception:
            pass
        return None

    @staticmethod
    def is_git_repo() -> bool:
        """Check if current directory is a git repo."""
        return (
            run_safe_command(
                ["git", "rev-parse", "--is-inside-work-tree"], capture_output=True
            ).returncode
            == 0
        )

    @staticmethod
    def get_diff(target: str = "HEAD") -> str:
        """Get git diff for a target (commit, branch, staged, or file path)."""
        try:
            # 1. Handle special keywords and PRs
            if target == "staged":
                return GitService._get_staged_diff()

            if target.startswith("http") or target.isdigit():
                return GitService.get_pr_diff(target)

            # 2. Check if target is a file path that exists
            if os.path.isfile(target):
                return GitService._get_path_diff(target)

            # 3. Default to branch/commit/tag diff
            return GitService._get_branch_diff(target)

        except Exception as e:
            logger.debug(f"Git diff failed for target '{target}': {e}")
            return ""

    @staticmethod
    def _get_staged_diff() -> str:
        """Helper to get staged diff."""
        cmd = ["git", "diff", "--staged", "-M", "--", "."]
        for ignore in GitService.IGNORE_FILES:
            cmd.append(f":!{ignore}")
        result = run_safe_command(cmd, capture_output=True, text=True, check=True)
        return result.stdout

    @staticmethod
    def _get_path_diff(target: str) -> str:
        """Helper to get diff for a specific file path."""
        cmd = ["git", "diff", "-M", "HEAD", "--", target]
        result = run_safe_command(cmd, capture_output=True, text=True, check=True)
        diff = result.stdout

        if not diff:
            # Check if it's tracked
            tracked = (
                run_safe_command(
                    ["git", "ls-files", "--error-unmatch", target],
                    capture_output=True,
                    check=False,
                ).returncode
                == 0
            )
            if not tracked:
                # Construct a "new file" diff
                try:
                    with open(target, "r") as f:
                        content = f.read()
                    lines = content.splitlines()
                    diff = (
                        f"diff --git a/{target} b/{target}\n"
                        f"new file mode 100644\n"
                        f"--- /dev/null\n"
                        f"+++ b/{target}\n"
                        f"@@ -0,0 +1,{len(lines)} @@\n"
                    )
                    diff += "\n".join([f"+{line}" for line in lines])
                except Exception as e:
                    logger.error(f"Error reading untracked file {target}: {e}")
                    return ""

        if diff:
            diff = f"File: {target}\n\n{diff}"
        return diff

    @staticmethod
    def _get_branch_diff(target: str) -> str:
        """Helper to get diff for a branch, commit, or tag."""
        # Use simple diff for HEAD, merge-base diff for others
        if target == "HEAD":
            cmd = ["git", "diff", "-M", "HEAD", "--", "."]
        else:
            cmd = ["git", "diff", "-M", f"HEAD...{target}", "--", "."]

        for ignore in GitService.IGNORE_FILES:
            cmd.append(f":!{ignore}")

        result = run_safe_command(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0 and target != "HEAD":
            # Fallback to direct diff for non-HEAD targets if merge-base fails
            cmd[3] = f"HEAD..{target}"
            result = run_safe_command(cmd, capture_output=True, text=True, check=True)

        return result.stdout

    @staticmethod
    def get_file_status_summary(target: str = "HEAD") -> str:
        """
        Get a summary of file statuses (Added, Modified, Deleted, Renamed).
        Useful for providing high-level context to LLMs before the full diff.
        """
        try:
            cmd = ["git", "diff", "--name-status", "-M", target, "--", "."]
            for ignore in GitService.IGNORE_FILES:
                cmd.append(f":!{ignore}")

            result = run_safe_command(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError:
            return "Could not retrieve file status summary."

    @staticmethod
    def get_git_log_search(query: str, path: str = ".") -> str:
        """
        Deep git log analysis: Search for a string in commit history (git log -S).
        Returns commit hashes, dates, authors, and subjects where the query was added/removed.
        """
        try:
            cmd = [
                "git", "log", "-S", query, 
                "--pretty=format:%h - %an, %ar : %s",
                "-n", "30",
                "--", path
            ]
            result = run_safe_command(cmd, capture_output=True, text=True, check=True)
            return result.stdout if result.stdout else f"No commits found altering '{query}'"
        except subprocess.CalledProcessError as e:
            return f"Failed to search git log: {e.stderr}"

    @staticmethod
    def get_git_blame(file_path: str) -> str:
        """
        Get git blame for a file to see who last modified each line and when.
        """
        if not os.path.isfile(file_path):
            return f"File not found: {file_path}"
            
        try:
            # -w ignores whitespace, -M detects moved lines within a file
            cmd = ["git", "blame", "-w", "-M", file_path]
            result = run_safe_command(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Failed to run git blame: {e.stderr}"

    @staticmethod
    def get_pr_diff(pr_id_or_url: str) -> str:
        """Fetch PR diff using gh CLI."""
        if not shutil.which("gh"):
            raise RuntimeError("GitHub CLI (gh) is not installed")

        try:
            cmd = ["gh", "pr", "diff", pr_id_or_url]
            result = run_safe_command(cmd, capture_output=True, text=True, check=True)
            return GitService.filter_diff(result.stdout)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to fetch PR diff: {e.stderr}") from e

    @staticmethod
    def get_pr_details(pr_id_or_url: str) -> dict:
        """Fetch PR details (title, body, author) using gh CLI."""
        if not shutil.which("gh"):
            raise RuntimeError("GitHub CLI (gh) is not installed")

        try:
            cmd = [
                "gh",
                "pr",
                "view",
                pr_id_or_url,
                "--json",
                "title,body,author,number,url,headRefName,headRepositoryOwner",
            ]
            import json

            result = run_safe_command(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to fetch PR details: {e.stderr}") from e

    @staticmethod
    def get_issue_details(issue_id_or_url: str) -> dict:
        """Fetch issue details (title, body) using gh CLI."""
        if not shutil.which("gh"):
            raise RuntimeError("GitHub CLI (gh) is not installed")

        try:
            # Check if it's a URL or ID
            target = str(issue_id_or_url)
            cmd = ["gh", "issue", "view", target, "--json", "title,body,number"]
            import json

            result = run_safe_command(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.debug(f"Failed to fetch issue details: {e.stderr}")
            return {}

    @staticmethod
    def get_current_branch() -> str:
        """Get current branch name."""
        try:
            result = run_safe_command(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"

    @staticmethod
    def get_pr_branch(pr_id_or_url: str) -> str:
        """Get the branch name for a PR using gh CLI."""
        if not shutil.which("gh"):
            raise RuntimeError("GitHub CLI (gh) is not installed")

        try:
            # Get the headRefName (branch name)
            cmd = ["gh", "pr", "view", pr_id_or_url, "--json", "headRefName"]
            import json

            result = run_safe_command(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            return data.get("headRefName", "")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to fetch PR branch: {e.stderr}") from e

    @staticmethod
    def checkout_pr_worktree(pr_id_or_url: str, worktree_path: str) -> None:
        """
        Checkout a PR into a worktree.
        Uses direct ref fetching to avoid disrupting the main directory's branch.
        Handles forks by adding a remote and tracking the fork's branch.
        """
        try:
            pr_number = None
            is_fork = False
            head_ref_name = None
            head_repo_clone_url = None
            fork_owner = None

            # 1. Try to get PR details via gh CLI
            if shutil.which("gh"):
                try:
                    details = GitService.get_pr_details(pr_id_or_url)
                    pr_number = details.get("number")
                    
                    head_repo_owner = details.get("headRepositoryOwner", {}).get("login")
                    repo_name = GitService._get_repo_from_remote()
                    if repo_name and head_repo_owner:
                        base_owner = repo_name.split('/')[0]
                        if base_owner.lower() != head_repo_owner.lower():
                            is_fork = True
                            head_ref_name = details.get("headRefName")
                            fork_owner = head_repo_owner
                            # Use ssh or https based on current remote style, default https
                            head_repo_clone_url = f"https://github.com/{head_repo_owner}/{repo_name.split('/')[1]}.git"
                except Exception as e:
                    logger.debug(f"gh CLI failed to fetch PR details: {e}")

            # 2. Add fallback to PyGithub
            if not pr_number:
                gh_client = GitService._get_github_client()
                if gh_client:
                    repo_str = GitService._get_repo_from_remote()
                    if repo_str:
                        repo = gh_client.get_repo(repo_str)
                        try:
                            if "pull/" in str(pr_id_or_url):
                                pr_num = int(str(pr_id_or_url).split("pull/")[-1].split("/")[0])
                            else:
                                pr_num = int(pr_id_or_url)
                            
                            pr = repo.get_pull(pr_num)
                            pr_number = pr.number
                            if pr.head.repo and pr.head.repo.full_name != repo.full_name:
                                is_fork = True
                                head_ref_name = pr.head.ref
                                fork_owner = pr.head.repo.owner.login
                                head_repo_clone_url = pr.head.repo.clone_url
                        except Exception as e:
                            logger.debug(f"PyGithub failed to fetch PR: {e}")

            if not pr_number:
                raise RuntimeError(f"Could not determine PR number for: {pr_id_or_url}. Ensure 'gh' CLI is installed or 'PyGithub' works.")

            local_review_branch = f"review-pr-{pr_number}"

            if is_fork and head_ref_name and head_repo_clone_url and fork_owner:
                logger.info(f"PR is from a fork ({fork_owner}). Adding remote and fetching...", to_cli=True)
                fork_remote = f"fork-{fork_owner}"
                
                # Check if remote exists
                remotes = run_safe_command(["git", "remote"], capture_output=True, text=True).stdout.splitlines()
                if fork_remote not in remotes:
                    run_safe_command(["git", "remote", "add", fork_remote, head_repo_clone_url], check=True)
                
                # Fetch the branch from the fork remote
                run_safe_command(["git", "fetch", fork_remote, head_ref_name], check=True)
                
                # Setup proper tracking so the user can push back to the fork
                start_point = f"{fork_remote}/{head_ref_name}"
                
                logger.info(f"Creating worktree at {worktree_path} tracking {start_point}...", to_cli=True)
                cmd = ["git", "worktree", "add", "-B", local_review_branch, worktree_path, start_point]
                run_safe_command(cmd, check=True)
            else:
                # Standard inner-repo PR
                ref = f"pull/{pr_number}/head:{local_review_branch}"
                logger.info(f"Fetching {ref} into isolated branch...", to_cli=True)
                run_safe_command(["git", "fetch", "origin", ref, "-f"], check=True)
                
                cmd = ["git", "worktree", "add", worktree_path, local_review_branch]
                run_safe_command(cmd, check=True)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to setup PR worktree: {e.stderr}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error creating PR worktree: {e}") from e

    @staticmethod
    def create_feature_worktree(branch_name: str, worktree_path: str) -> None:
        """Create a worktree for a feature branch (creating branch if needed)."""
        try:
            # Check if branch exists
            branch_exists = (
                run_safe_command(
                    ["git", "rev-parse", "--verify", branch_name], capture_output=True
                ).returncode
                == 0
            )

            cmd = ["git", "worktree", "add"]
            if not branch_exists:
                # Create new branch
                # Syntax: git worktree add -b <new_branch> <path> <start_point>
                # We'll default start_point to HEAD if not specified
                cmd.extend(["-b", branch_name, worktree_path])
            else:
                # Existing branch
                # Syntax: git worktree add <path> <branch>
                cmd.extend([worktree_path, branch_name])

            run_safe_command(cmd, check=True, capture_output=True)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create feature worktree: {e.stderr}") from e
