# Roadmap

This roadmap outlines the future development of the DSPy Compounding Engineering project. Our goal is to create a truly self-improving engineering system.

## 🚀 Upcoming Releases

### v1.0: Core Compounding Loops (Current)
- [x] **DSPy Integration**: Full migration to DSPy primitives.
- [x] **Workflows**: `review`, `triage`, `working` (plan+act).
- [x] **Knowledge Base**: Basic keyword-based retrieval and storage.
- [x] **Parallel Execution**: Safe worktree-based parallel task execution.

### v0.1.2: Reliability & Security (Current Work)
Focus on hardening the core system for internal pre-production use.
- [ ] **Security Hardening** (#42): Command execution allowlist and path traversal validation.
- [ ] **Data Integrity** (#43): Transaction safety and PII scrubbing.
- [ ] **Logging Standardization** (#48): Unified logging framework.
- [ ] **Fork PR Handling** (#10): Fix GitService for fork repository support.
- [ ] **Complexity Refactoring** (#46): Address depth/C901 issues.
- [ ] **One-Liner Installer** (#30): Add uv-based installer script.

### v0.1.3: Performance & DX
Focus on speed, cost optimization, testing, and contributor documentation.
- **[#49] Agent Consolidation & Selection**: Reduce token cost by combining agent calls and allow targeted reviews.
- **[#44] Performance Optimization**: Batch embeddings and search efficiency.
- [ ] **Improve Test Coverage** (#12): Target 80%+ code coverage for agents.
- [ ] **API Documentation** (#21): Auto-generated docs.
- [ ] **Dynamic Docs** (#31): Integrate `get-md` tool.

### v0.1.4: Automation & Tooling
Standardizing tools and closing the autonomous loops.
- [ ] **MCP Integration** (#9): Implement Model Context Protocol for tools.
- [ ] **Test Runner Integration** (#16): Automated logic loop verification.
- [ ] **Auto-Triage** (#6): Pattern-based finding promotion.
- [ ] **Intelligent Gardening** (#50): Focus on high-value facts and systemic patterns.

### v1.0.0: Production Build
Final milestone for general consumption and managed services.
- [ ] **GitHub App** (#15): Foundational support for seamless integration.
- [ ] **Learning Analytics** (#13): Dashboard showing growth and reuse metrics.
- [ ] **Auto-Triage Loop** (#45): Final UI/UX for autonomous workflow closure.

### Future / Backlog
- [ ] **Dynamic Docs** (#31): Integrate `get-md` tool.
- [ ] **API Documentation** (#21): Auto-generated docs.
- [ ] **IDE Extensions** (#17, #7): VS Code and JetBrains plugins.
- [ ] **Incremental Indexing** (#35): CocoIndex-powered code indexer.
- [ ] **Real-time Streaming** (#20): Stream agent thoughts in real-time.

## 💡 Feature Requests

Have an idea? Please [open an issue](https://github.com/Strategic-Automation/dspy-compounding-engineering/issues) or discuss it in our [Discussions](https://github.com/Strategic-Automation/dspy-compounding-engineering/discussions).
