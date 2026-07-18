## 📌 Description
Explain the changes implemented by this Pull Request and how they solve the associated issue or task.

Related Issue: # (link issue here)

## 🏗️ Architectural Impact
- [ ] Core Domain modified
- [ ] Outbound Adapter added/modified
- [ ] Inbound Adapter added/modified
- [ ] Ports contracts updated

Explain any architectural deviations or major design decisions made:

## 🧪 Testing Checklist
Verify that code has been tested:
- [ ] Unit Tests added/updated (`pytest tests/unit/`)
- [ ] Integration Tests added/updated (`pytest tests/integration/`)
- [ ] Syntax check passed (`python -m py_compile`)

Test coverage results summary:

## 🧹 Code Quality (Self-Review)
- [ ] Strict type annotations checked
- [ ] Follows Hexagonal Architecture boundary rules (no infrastructure imports in Core)
- [ ] Database credentials loaded from environment variables (no hardcoded credentials)
- [ ] Pre-commit hooks executed successfully
- [ ] No `TODO` or `pass` statements left in production code
