# Roadmap

This roadmap outlines the future development of the DSPy Compounding Engineering project. Our goal is to create a truly self-improving engineering system.

## 🚀 Upcoming Releases

### v1.0: Core Compounding Loops (Current)
- [x] **DSPy Integration**: Full migration to DSPy primitives.
- [x] **Workflows**: `review`, `triage`, `working` (plan+act).
- [x] **Knowledge Base**: Basic keyword-based retrieval and storage.
- [x] **Parallel Execution**: Safe worktree-based parallel task execution.

### v1.1: Foundations of Reliability & Integration
Focus on robustness, testing, and basic GitHub connectivity.
- [ ] **Test Runner Integration** (#16): Integrate test running into the standard `work` workflow.
- [ ] **Improve Test Coverage** (#12): Enhance coverage for Agents and Workflows.
- [ ] **Security Hardening** (#38): Implement markdown sanitization and path masking.
- [ ] **Data Integrity** (#40): Atomic Knowledge Base updates and reconciliation.
- [ ] **One-Liner Installer** (#30): Add uv-based installer and install script.
- [ ] **Fork PR Handling** (#10): Fix GitService to correctly handle PRs from forks.
- [ ] **GitHub App** (#15): Foundational support for seamless integration.

### v1.2: Enhanced Intelligence & Connectivity
Making the system smarter and more connected to the ecosystem.
- [ ] **MCP Integration** (#9): Implement Model Context Protocol for standardized tool access.
- [x] **Vector Embeddings** (#8): Semantically indexed Knowledge Base (ChromaDB/Qdrant).
- [x] **Smart Context** (#11): Context gathering with semantic filtering.
- [x] **Knowledge Gardening** (#19): Agent for refining and compressing the Knowledge Base.
- [ ] **Code Search Tool** (#33): Add active code search capabilities to Work agents.
- [ ] **Dynamic Docs** (#31): Integrate `get-md` tool for fetching third-party documentation.
- [ ] **Incremental Indexing** (#35): CocoIndex-powered incremental code indexer.
- [ ] **Performance Optimization** (#39): LLM compression caching and batching.
- [ ] **Auto-Triage** (#14, #6): Pattern-based auto-approval/rejection of findings.

### v2.0: Deep Compounding & Analytics
- [ ] **Learning Analytics** (#13): Dashboard showing knowledge growth and reuse metrics.
- [ ] **Claude OS Architecture** (#36): Memory systems, skills library & real-time Kanban.
- [ ] **Cross-Project Knowledge**: Share learnings across different repositories.

### Future / Backlog
- [ ] **Multi-LLM Support** (#18): Expand provider support beyond current set.
- [ ] **Real-time Streaming** (#20): Stream agent thoughts and outputs in real-time.
- [ ] **API Documentation** (#21): Comprehensive auto-generated API docs.
- [ ] **IDE Extensions** (#17, #7): VS Code and JetBrains plugins.
- [ ] **Action Runners**: Run as a GitHub Action.

## 💡 Feature Requests

Have an idea? Please [open an issue](https://github.com/Strategic-Automation/dspy-compounding-engineering/issues) or discuss it in our [Discussions](https://github.com/Strategic-Automation/dspy-compounding-engineering/discussions).
