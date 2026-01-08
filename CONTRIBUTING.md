# Contributing to AWS API Factory

Thank you for your interest in contributing to AWS API Factory! This document provides guidelines and instructions for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## Code of Conduct

Please be respectful and constructive in all interactions. We're all here to build something great together.

## Development Setup

### Prerequisites

- **Python 3.9+** installed
- **Node.js 18+** (for AWS CDK CLI)
- **Docker** (for App Runner testing)
- **Git** configured with your identity

### Initial Setup

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/aws-api-factory.git
cd aws-api-factory

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install in development mode with all dependencies
pip install -e ".[dev]"

# 4. Install AWS CDK CLI globally
npm install -g aws-cdk

# 5. Install pre-commit hooks
pre-commit install

# 6. Verify setup
pytest --collect-only  # Should find test files
factory --help         # Should show CLI help
```

### IDE Configuration

We recommend VS Code with these extensions:
- Python (Microsoft)
- Pylance
- Black Formatter
- YAML

## Development Workflow

### Branch Naming

Use descriptive branch names:
- `feature/add-aurora-support` — New features
- `fix/config-validation-error` — Bug fixes
- `docs/update-readme` — Documentation changes
- `refactor/simplify-resolver` — Code refactoring

### Making Changes

```bash
# 1. Create a feature branch from main
git checkout main
git pull origin main
git checkout -b feature/your-feature

# 2. Make your changes
# ... edit files ...

# 3. Run pre-commit hooks
pre-commit run --all-files

# 4. Run tests
pytest

# 5. Commit with conventional commit message
git commit -m "feat: add support for custom domains"

# 6. Push and create PR
git push origin feature/your-feature
```

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat` — New feature
- `fix` — Bug fix
- `docs` — Documentation only
- `style` — Formatting, no code change
- `refactor` — Code change that neither fixes a bug nor adds a feature
- `test` — Adding or updating tests
- `chore` — Maintenance tasks

**Examples:**
```
feat(config): add support for custom IAM statements
fix(cli): handle missing factory.yaml gracefully
docs(readme): update installation instructions
test(auth): add integration tests for Cognito auth
```

## Code Standards

### Python Style

- **Formatter:** Black (enforced by pre-commit)
- **Line Length:** 88 characters (Black default)
- **Imports:** Sorted with isort (Black-compatible profile)
- **Type Hints:** Required for all public functions and methods

### Docstrings

Use Google-style docstrings:

```python
def deploy_stack(
    config: FactoryConfig,
    environment: str,
    *,
    dry_run: bool = False,
) -> DeploymentResult:
    """Deploy the API Factory stack to AWS.

    Args:
        config: Validated factory configuration.
        environment: Target environment name (e.g., 'dev', 'prod').
        dry_run: If True, synthesize but don't deploy.

    Returns:
        DeploymentResult containing stack outputs and status.

    Raises:
        DeploymentError: If deployment fails.
        ConfigurationError: If config is invalid for the environment.
    """
```

### File Headers

All Python files should include the license header:

```python
# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Module description here."""
```

## Testing

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/config/test_models.py

# Run tests matching a pattern
pytest -k "test_validate"

# Run with verbose output
pytest -v

# Run only unit tests (fast)
pytest -m unit

# Run integration tests (requires AWS credentials)
pytest -m integration
```

### Test Organization

```
tests/
├── conftest.py           # Shared fixtures
├── config/
│   ├── test_models.py    # Config model tests
│   ├── test_loader.py    # YAML loading tests
│   └── fixtures/         # Test YAML files
├── cli/
│   └── test_commands.py  # CLI command tests
└── constructs/
    └── test_rest_api.py  # CDK construct tests
```

### Writing Tests

```python
import pytest
from aws_api_factory.config import FactoryConfig


class TestFactoryConfig:
    """Tests for FactoryConfig model."""

    def test_minimal_valid_config(self, minimal_config_dict: dict) -> None:
        """Test that minimal valid config loads successfully."""
        config = FactoryConfig(**minimal_config_dict)
        assert config.project.name == "test-api"
        assert config.profile == "minimal"

    def test_missing_required_field_raises_error(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError, match="project"):
            FactoryConfig(profile="minimal")
```

### Coverage Requirements

- Minimum 85% code coverage required
- New features must include tests
- Bug fixes should include regression tests

## Pull Request Process

### Before Submitting

1. ✅ All pre-commit hooks pass
2. ✅ All tests pass with `pytest`
3. ✅ Coverage meets minimum threshold (85%)
4. ✅ Documentation updated if needed
5. ✅ Commit messages follow conventions

### PR Template

When creating a PR, include:

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested your changes.

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Pre-commit hooks pass
- [ ] Ready for review
```

### Review Process

1. Create PR against `main` branch
2. Automated CI checks must pass
3. At least one maintainer approval required
4. Squash and merge preferred

## Release Process

Releases are managed by maintainers:

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create GitHub release with tag
4. CI automatically publishes to PyPI

## Questions?

- Open a [GitHub Issue](https://github.com/seanmeehan/aws-api-factory/issues)
- Start a [Discussion](https://github.com/seanmeehan/aws-api-factory/discussions)

Thank you for contributing! 🙏
