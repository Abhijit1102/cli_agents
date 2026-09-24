# CLI Agents Improvement Roadmap

This document turns the current project assessment into an engineering plan.

## Current Assessment

| Dimension | Current | Target |
| --- | ---: | ---: |
| Concept and ambition | 8/10 | 9/10 |
| Architecture | 6.5/10 | 8/10 |
| Implementation maturity | 5.5/10 | 8/10 |
| Security | 3/10 | 8/10 |
| Production readiness | 3/10 | 7/10 |
| Portfolio value | 8/10 | 9/10 |

The project is an intermediate-level Python developer-tooling project: an async LLM orchestration layer, terminal UI, filesystem and shell tools, and optional MCP integrations.

## Priority Order

1. Make dangerous actions enforceable in code.
2. Add tests around the agent loop and every security boundary.
3. Separate orchestration, policy, tools, and presentation more cleanly.
4. Improve reliability, cancellation, observability, and configuration.
5. Document the architecture and demonstrate it with reproducible examples.

---

## Phase 1: Security Baseline

### 1. Enforce project-root boundaries

- Resolve every filesystem path against `config.project_root`.
- Reject paths that escape the project root, including `..`, absolute paths, and symlink escapes.
- Apply the same policy to `read_file`, `write_file`, `list_folder`, `search_project`, image analysis, and command working directories.
- Add explicit exceptions for paths the user deliberately approves.

Done when:

- Tests prove that in-root paths work.
- Tests prove that parent traversal, absolute paths, and symlink escapes fail.
- Error messages explain the rejected path and allowed root.

### 2. Replace prompt-only approval with a policy layer

The system prompt says that writes and commands require approval, but the controller currently executes tools directly. Add a real `PermissionPolicy` or `ApprovalManager` between the model and tool executors.

- Classify tools as read-only, write, execute, network, or external-service actions.
- Require approval for writes, shell commands, MCP calls, and image API calls when appropriate.
- Support `approve once`, `approve for this session`, and `deny`.
- Make non-interactive mode fail closed.
- Log the tool name, arguments, decision, and result without logging secrets.

Done when:

- A model tool call cannot bypass the policy.
- A denied operation never reaches the executor.
- Approval behavior is covered by automated tests.

### 3. Harden shell execution

- Default the command working directory to the project root, not the process directory.
- Validate the requested `cwd` with the same root policy.
- Add a command timeout cap and reject invalid or extreme timeout values.
- Return structured command results: exit code, stdout, stderr, timed out, and duration.
- Add an explicit setting for whether network access is allowed.
- Clearly document that this is not a sandbox unless a real sandbox is added.

## Phase 2: Correctness and Tests

### 4. Add a real test suite

Create tests for:

- Configuration precedence and invalid configuration.
- Conversation memory message shapes.
- Tool-call parsing and malformed JSON.
- Maximum reasoning iterations.
- API failures and empty responses.
- Tool success, timeout, denial, and executor failure.
- Project-root path validation.
- MCP connection failures and shutdown.
- Slash commands and clean exit behavior.

Use fake API clients and fake tool executors. Tests must not require a real API key, network, MCP server, or shell mutation.

Done when:

- `pytest` runs without credentials or network access.
- CI runs the test suite on every change.
- The most dangerous tools have both allowed and denied test cases.

### 5. Stop hiding errors in strings

Replace string-prefix checks such as `"[Tool Error:]"` with typed results or exceptions.

A tool result should distinguish at least:

- success
- validation error
- permission denied
- timeout
- executor failure
- unavailable external service

Malformed tool arguments should produce a validation error and should not execute the tool.

### 6. Make the agent loop robust

- Handle missing choices and missing message fields safely.
- Validate tool arguments against the tool schema before execution.
- Preserve assistant and tool messages in the exact API-compatible shape.
- Make the maximum iteration count configurable.
- Add cancellation handling so Ctrl+C stops an active API request or tool call cleanly.
- Add a context-window strategy: truncate, summarize, or persist old history.

## Phase 3: Architecture and Maintainability

### 7. Define clear boundaries

Recommended modules:

- `core/controller.py`: model/tool loop only
- `core/policy.py`: permissions and approval decisions
- `core/protocol.py`: internal events instead of control-character strings
- `tools/registry.py`: schemas and executor registration
- `tools/context.py`: project root and execution context
- `ui/app.py`: rendering and user interaction only

Use typed event objects such as `ToolStarted`, `ToolFinished`, `AssistantText`, and `AgentError` instead of delimiter strings like `TOOL_START:name:args`.

### 8. Remove global state where practical

- Pass configuration or an execution context into tools explicitly.
- Avoid relying on `global_config` for image analysis and other tool behavior.
- Avoid creating a second synchronous OpenAI client inside a tool.
- Reuse the configured async client or inject a dedicated provider interface.

### 9. Make configuration predictable

- Validate all settings with useful error messages.
- Use one documented precedence rule for environment variables and JSON settings.
- Avoid loading secrets into process environment variables when they are only needed in memory.
- Redact API keys and authorization headers from logs and `/config` output.
- Make the image-analysis model configurable instead of hardcoding it.

## Phase 4: Production Readiness

### 10. Add operational behavior

- Structured logging with log levels.
- Request IDs and tool-call IDs.
- API retry policy with bounded backoff.
- Clear shutdown behavior for MCP, API clients, and active tasks.
- Graceful handling of terminal resize, Ctrl+C, and broken pipes.
- A non-interactive mode suitable for scripts and CI.
- Exit codes that distinguish user cancellation, configuration failure, tool failure, and agent failure.

### 11. Add quality automation

- Configure `ruff` for linting and formatting.
- Configure `mypy` or another type checker for public interfaces.
- Add coverage reporting with a minimum threshold.
- Add a CI workflow for tests, linting, type checking, and package building.
- Test installation from the built wheel, not only from the source tree.

### 12. Fix documentation drift

Keep the README synchronized with the code:

- Make `/sandbox` documentation match its actual implementation.
- Use the same project-instruction filename everywhere.
- Document which tools require approval and how approval works.
- Document path restrictions and shell limitations honestly.
- Add an architecture diagram and a short troubleshooting section.

## Phase 5: Portfolio Strength

### 13. Demonstrate the project with evidence

Add a short terminal recording or screenshots showing:

- Project startup and trust flow.
- A read-only request.
- A denied write or command.
- An approved change with a rendered diff.
- A failed tool call with a useful error.
- An MCP tool call, if MCP is enabled.

### 14. Add a reproducible demo mode

Provide a fake provider or scripted mode so someone can run the UI without an API key. This makes the project easier to review and proves the orchestration code independently of a paid model.

### 15. Explain the engineering decisions

Add a design document covering:

- Why the agent loop is bounded.
- How permissions are enforced.
- Why the project-root policy exists.
- How MCP tools are isolated and named.
- What the system does not guarantee.

## Suggested Milestones

### Milestone 1: Safe to experiment with

- Root-bound filesystem tools.
- Approval layer for writes and shell commands.
- Typed tool results.
- Tests for all of the above.

### Milestone 2: Reliable for daily personal use

- Robust agent loop.
- Cancellation and shutdown.
- Context management.
- Structured logging.
- CI with tests, linting, and type checking.

### Milestone 3: Strong public portfolio project

- Reproducible demo mode.
- Architecture documentation.
- Screenshots or recording.
- Clear security limitations.
- Package installation tested from a clean environment.

## Definition Of a Strong Version 2

A strong version 2 is not defined by more UI themes or more integrations. It is defined by this behavior:

1. The model requests an action.
2. The policy layer classifies and validates it.
3. The user approves or denies it when required.
4. The executor runs only within the allowed project boundary.
5. The result is typed, logged, displayed, and appended to memory correctly.
6. Tests prove each step without calling a real model or changing the host machine.
