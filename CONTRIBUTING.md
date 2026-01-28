# Contributing to AgentOS

Thank you for your interest in contributing to AgentOS! We welcome contributions from the community.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow:

- Be respectful and inclusive
- Focus on constructive feedback
- Assume good intentions
- Accept responsibility for your contributions

## Getting Started

### Prerequisites

- Python 3.13+
- Git
- Basic understanding of async Python and CLI tools

### Development Setup

1. **Fork and Clone**

   ```bash
   git clone https://github.com/YOUR-USERNAME/agentos.git
   cd agentos
   ```

2. **Set Up Environment**

   ```bash
   # Using uv (recommended)
   uv sync

   # Or using pip
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Initialize Database**

   ```bash
   uv run agentos init
   ```

4. **Verify Setup**

   ```bash
   uv run agentos doctor
   uv run pytest tests/
   ```

## How to Contribute

### Types of Contributions

We welcome:

- 🐛 Bug fixes
- ✨ New features
- 📝 Documentation improvements
- 🧪 Test coverage improvements
- 🎨 UI/UX enhancements
- 🌍 Translations (i18n)

### Finding Work

- Check [Issues](https://github.com/seacow-technology/agentos/issues) labeled `good first issue`
- Look for `help wanted` labels
- Review the [roadmap](docs/ROADMAP.md) for planned features

### Before You Start

1. **Check existing issues/PRs** to avoid duplicate work
2. **Open an issue** to discuss significant changes before coding
3. **Ask questions** if anything is unclear

## Pull Request Process

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Your Changes

- Follow the [coding standards](#coding-standards)
- Add tests for new functionality
- Update documentation as needed
- Keep commits atomic and well-described

### 3. Test Your Changes

```bash
# Run all tests
uv run pytest tests/

# Run specific test
uv run pytest tests/test_your_test.py -v

# Run linting
uv run ruff check .
uv run ruff format --check .
```

### 4. Commit Your Changes

Follow conventional commits format:

```bash
git commit -m "feat: add new feature"
git commit -m "fix: resolve issue with task execution"
git commit -m "docs: update README quickstart"
```

Commit types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `chore`: Maintenance tasks

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:

- **Clear title** describing the change
- **Description** explaining what and why
- **Related issues** (e.g., "Closes #123")
- **Testing done** (how you verified it works)
- **Screenshots** (for UI changes)

### 6. Code Review

- Address reviewer feedback promptly
- Keep discussions respectful and constructive
- Be open to suggestions and improvements

## Coding Standards

### Python Style

We follow PEP 8 with some modifications:

- **Line length**: 100 characters (not 79)
- **Imports**: Organized with `ruff` (automatic sorting)
- **Type hints**: Encouraged for public APIs
- **Docstrings**: Required for public functions/classes

### Code Quality Tools

```bash
# Auto-format code
uv run ruff format .

# Check linting
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .
```

### Architecture Guidelines

AgentOS has strict architectural contracts. Please read:

- [Architecture Contracts](docs/cli/CLI_ARCHITECTURE_CONTRACTS.md) - **Required reading**
- [Validation Layers](docs/architecture/VALIDATION_LAYERS.md)
- [Mode Gates](docs/architecture/MODE_GATES.md)

**Key principles:**

1. **Task-Centric**: All operations create/manage tasks (not ad-hoc execution)
2. **Interruptible**: Tasks must pause at `open_plan` for approval
3. **Auditable**: Every action must have audit trail
4. **Mode-Aware**: Respect execution mode gates

### File Organization

```
agentos/
├── cli/          # CLI commands and interface
├── core/         # Core orchestration logic
├── webui/        # Web UI components
├── store/        # Database and persistence
├── schemas/      # Data models and validation
└── util/         # Shared utilities
```

## Testing

### Test Structure

```
tests/
├── unit/         # Unit tests (fast, isolated)
├── integration/  # Integration tests (cross-component)
└── e2e/          # End-to-end tests (full workflows)
```

### Writing Tests

- Use `pytest` framework
- Follow AAA pattern (Arrange, Act, Assert)
- Mock external dependencies (LLM calls, file system when appropriate)
- Add markers for slow tests: `@pytest.mark.slow`

Example:

```python
import pytest
from agentos.core.task import TaskManager

def test_task_creation():
    # Arrange
    manager = TaskManager()

    # Act
    task = manager.create_task("Test task", mode="planning")

    # Assert
    assert task.status == "pending"
    assert task.mode == "planning"
```

### Test Coverage

- Aim for >80% coverage on new code
- Focus on critical paths and error handling
- Run coverage report:

```bash
uv run pytest --cov=agentos --cov-report=html
```

## Documentation

### Types of Documentation

1. **Code Comments**: For complex logic
2. **Docstrings**: For all public APIs
3. **README**: Keep up-to-date with changes
4. **Architecture Docs**: For design decisions
5. **User Guides**: For new features

### Docstring Format

Use Google-style docstrings:

```python
def execute_task(task_id: str, mode: str) -> TaskResult:
    """Execute a task with specified mode.

    Args:
        task_id: Unique task identifier
        mode: Execution mode (planning/implementation)

    Returns:
        TaskResult object with execution status

    Raises:
        TaskNotFoundError: If task_id is invalid
        ModeGateError: If mode transition is invalid
    """
```

### Documentation Updates

Update docs when you:

- Add a new feature (add user guide)
- Change architecture (update architecture docs)
- Modify CLI commands (update CLI reference)
- Fix a bug (add to CHANGELOG)

## Questions?

- 💬 Open a [Discussion](https://github.com/seacow-technology/agentos/discussions)
- 🐛 Report bugs via [Issues](https://github.com/seacow-technology/agentos/issues)
- 📧 Email: dev@seacow.tech (replace with actual contact)

---

Thank you for contributing to AgentOS! 🚀
