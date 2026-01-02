# Testing Guide for Financial Email Agent

This document provides comprehensive information about testing the Financial Email Agent.

## Table of Contents

1. [Test Structure](#test-structure)
2. [Running Tests](#running-tests)
3. [Test Coverage](#test-coverage)
4. [Writing Tests](#writing-tests)
5. [Continuous Integration](#continuous-integration)

## Test Structure

The project uses `pytest` for testing with the following structure:

```
tests/
├── __init__.py
├── unit/                    # Unit tests for individual components
│   ├── test_classifier.py   # Email classifier tests
│   ├── test_extractor.py    # Data extractor tests
│   └── test_email.py        # Email service tests
├── integration/             # Integration tests
│   └── test_workflow.py     # End-to-end workflow tests
└── fixtures/                # Test fixtures and sample data
```

## Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
# Using the test runner script
python run_tests.py

# Or directly with pytest
pytest tests/ -v
```

### Run Specific Test Types

```bash
# Unit tests only
python run_tests.py unit

# Integration tests only
python run_tests.py integration

# Specific test file
pytest tests/unit/test_classifier.py -v

# Specific test function
pytest tests/unit/test_classifier.py::TestEmailClassifier::test_classify_invoice_success -v
```

### Run with Coverage

```bash
# Generate coverage report
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# View HTML coverage report
# Open htmlcov/index.html in your browser
```

### Run in Quiet Mode

```bash
python run_tests.py -q
```

## Test Coverage

### Current Coverage Goals

- **Overall**: > 80%
- **Core Services**: > 90%
- **Utilities**: > 85%
- **MCP Servers**: > 75%

### Viewing Coverage Reports

After running tests with coverage:

1. **Terminal Report**: Shows coverage summary in the terminal
2. **HTML Report**: Detailed coverage report in `htmlcov/index.html`

```bash
# Generate and open HTML report (Windows)
pytest tests/ --cov=src --cov-report=html
start htmlcov/index.html

# Linux/Mac
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

## Writing Tests

### Unit Test Example

```python
import pytest
from unittest.mock import Mock
from src.classifier.service import EmailClassifier

@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    return Mock()

@pytest.fixture
def classifier(mock_llm_client, mock_config):
    """Create a classifier instance."""
    return EmailClassifier(mock_llm_client, mock_config)

def test_classify_invoice(classifier, mock_llm_client):
    """Test invoice classification."""
    # Arrange
    mock_llm_client.generate.return_value = '{"category": "invoice", "confidence": 0.95}'
    email_data = {"subject": "Invoice #123", "body": "..."}
    
    # Act
    result = classifier.classify(email_data)
    
    # Assert
    assert result["category"] == "invoice"
    assert result["confidence"] == 0.95
```

### Integration Test Example

```python
import pytest
from src.main import FinancialEmailAgent

def test_complete_workflow(mock_dependencies):
    """Test complete email processing workflow."""
    # Arrange
    agent = FinancialEmailAgent(config)
    email_data = {...}
    
    # Act
    result = agent.process_email(email_data)
    
    # Assert
    assert result["status"] == "success"
    assert "classification" in result
    assert "extracted_data" in result
```

### Test Fixtures

Create reusable test data in `tests/fixtures/`:

```python
# tests/fixtures/sample_emails.py
SAMPLE_INVOICE_EMAIL = {
    "subject": "Invoice #12345",
    "from": "vendor@example.com",
    "body": "Please find attached invoice...",
    "attachments": ["invoice.pdf"]
}
```

### Mocking Guidelines

1. **Mock External Services**: Always mock external APIs (Gmail, Ollama, MongoDB)
2. **Mock File I/O**: Mock file operations to avoid filesystem dependencies
3. **Use Fixtures**: Create reusable fixtures for common mocks
4. **Patch at Import**: Patch dependencies where they're imported, not where they're defined

```python
# Good: Patch where it's used
@patch('src.main.MongoDBConnection')
def test_something(mock_db):
    ...

# Bad: Patch where it's defined
@patch('src.database.connection.MongoDBConnection')
def test_something(mock_db):
    ...
```

## Test Categories

### Unit Tests

Test individual components in isolation:

- **Classifier Tests**: Email classification logic
- **Extractor Tests**: Data extraction and validation
- **Email Service Tests**: Email parsing and operations
- **Utility Tests**: Helper functions and utilities

### Integration Tests

Test component interactions:

- **Workflow Tests**: Complete email processing pipeline
- **Database Tests**: Database operations and queries
- **MCP Server Tests**: MCP server tool execution

### End-to-End Tests

Test complete user scenarios:

- **Invoice Processing**: Full invoice workflow
- **Receipt Processing**: Full receipt workflow
- **Batch Processing**: Multiple email processing

## Continuous Integration

### GitHub Actions (Example)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run tests
        run: python run_tests.py
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure you're in the project root
   cd /path/to/financial-email-agent
   
   # Install in development mode
   pip install -e .
   ```

2. **Mock Not Working**
   ```python
   # Make sure to patch where the object is used, not where it's defined
   @patch('src.main.LLMClient')  # Correct
   @patch('src.llm.client.LLMClient')  # Incorrect
   ```

3. **Fixture Not Found**
   ```python
   # Ensure fixture is defined in conftest.py or the same file
   # tests/conftest.py
   @pytest.fixture
   def common_fixture():
       return "value"
   ```

4. **Database Connection Errors**
   ```python
   # Always mock database connections in tests
   @patch('src.main.MongoDBConnection')
   def test_with_db(mock_db):
       ...
   ```

## Best Practices

1. **Test Naming**: Use descriptive names that explain what is being tested
   - Good: `test_classify_invoice_with_high_confidence`
   - Bad: `test_1`

2. **Arrange-Act-Assert**: Structure tests clearly
   ```python
   def test_something():
       # Arrange: Set up test data
       data = {...}
       
       # Act: Execute the code being tested
       result = function(data)
       
       # Assert: Verify the results
       assert result == expected
   ```

3. **One Assertion Per Test**: Focus each test on a single behavior
   - Exception: Related assertions that test the same behavior

4. **Test Independence**: Tests should not depend on each other
   - Use fixtures for setup
   - Clean up after tests

5. **Mock External Dependencies**: Never make real API calls or database connections in tests

6. **Test Edge Cases**: Test boundary conditions, errors, and unusual inputs

## Performance Testing

For performance testing:

```bash
# Run with timing information
pytest tests/ --durations=10

# Profile slow tests
pytest tests/ --profile
```

## Debugging Tests

```bash
# Run with print statements visible
pytest tests/ -s

# Drop into debugger on failure
pytest tests/ --pdb

# Run last failed tests only
pytest tests/ --lf

# Run specific test with verbose output
pytest tests/unit/test_classifier.py::test_name -vv
```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)

---

For questions or issues with testing, please open an issue on GitHub.