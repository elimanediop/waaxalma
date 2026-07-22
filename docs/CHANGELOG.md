# Changelog

## [0.2.0] - 2026-07-23

### Added

- Introduced a unified `BaseAgent` execution contract.
- Added `AgentInput`, `AgentResult`, and `SessionContext`.
- Added `AgentOrchestrator` as the central agent execution layer.
- Added agent registration and lookup through `AgentManager`.
- Added orchestration support for text translation, speech generation,
  text interpretation, and voice interpretation.

### Changed

- Migrated `TranslationAgent` to the unified `execute()` contract.
- Migrated `InterpreterAgent` to the unified `execute()` contract.
- Routed all text, interpreter, and voice API endpoints through
  `AgentOrchestrator`.
- Centralized execution duration and error handling in the orchestrator.
- Removed direct agent execution from API routes.

### Validation

- Verified the complete Streamlit workflow.
- Preserved existing HTTP response contracts.
- Confirmed text and voice flows operate without regression.