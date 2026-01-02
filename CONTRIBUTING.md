# Contributing to Financial Email Agent

Thank you for your interest in contributing to the Financial Email Agent project! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

### Suggesting Enhancements

Enhancement suggestions are welcome! Please create an issue with:
- Clear description of the proposed feature
- Use cases and benefits
- Potential implementation approach (if applicable)

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following the coding standards below
3. **Add tests** for new functionality
4. **Update documentation** as needed
5. **Ensure all tests pass** (`pytest`)
6. **Run linting** (`flake8`, `black`, `isort`)
7. **Submit a pull request** with a clear description

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/financial-email-agent.git
cd financial-email-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://pep8.org/) style guide
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Use [flake8](https://flake8.pycqa.org/) for linting

### Code Formatting

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Check linting
flake8 src/ tests/
```

### Type Hints

- Use type hints for function parameters and return values
- Use `mypy` for type checking

```python
def extract_invoice_data(email: dict) -> dict:
    """Extract structured data from invoice email."""
    pass
```

### Documentation

- Write clear docstrings for all functions and classes
- Use Google-style docstrings

```python
def classify_email(email_content: str) -> tuple[str, float]:
    """
    Classify email into financial categories.
    
    Args:
        email_content: The email body text to classify
        
    Returns:
        A tuple of (category, confidence_score)
        
    Raises:
        ValueError: If email_content is empty
    """
    pass
```

### Testing

- Write unit tests for new functionality
- Maintain test coverage above 80%
- Use pytest fixtures for common test setup

```python
def test_invoice_extraction():
    """Test invoice data extraction."""
    sample_email = load_test_email("invoice_sample.txt")
    result = extract_invoice_data(sample_email)
    assert result["invoice_number"] == "INV-001"
    assert result["total_amount"] == 1500.00
```

## Project Structure

```
src/
├── main.py              # Entry point
├── config/              # Configuration management
├── email/               # Email monitoring
├── classifier/          # Email classification
├── extractors/          # Data extraction
│   ├── invoice.py
│   ├── receipt.py
│   ├── bank_statement.py
│   └── expense_report.py
├── database/            # MongoDB integration
├── llm/                 # Llama model integration
└── utils/               # Utility functions

tests/
├── unit/                # Unit tests
├── integration/         # Integration tests
└── fixtures/            # Test data and fixtures
```

## Commit Message Guidelines

Use clear, descriptive commit messages:

```
feat: Add bank statement extraction module
fix: Resolve OAuth token refresh issue
docs: Update installation instructions
test: Add tests for receipt extractor
refactor: Simplify email classification logic
```

Prefix types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or changes
- `refactor`: Code refactoring
- `style`: Code style changes (formatting)
- `chore`: Maintenance tasks

## Branch Naming

Use descriptive branch names:
- `feature/invoice-extraction`
- `fix/gmail-auth-error`
- `docs/api-documentation`
- `test/classifier-tests`

## Review Process

1. All pull requests require review before merging
2. Address review comments promptly
3. Keep pull requests focused and reasonably sized
4. Ensure CI/CD checks pass

## License

By contributing, you agree that your contributions will be licensed under the GPL-3.0 License.

## Questions?

Feel free to open an issue for any questions about contributing!