# Testing Guide for RunMyPool Backend

This document describes how to run tests and check code coverage for the RunMyPool FastAPI backend.

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- Virtual environment activated
- Dependencies installed from `requirements.txt`

### Run All Tests with Coverage
```bash
# Navigate to backend directory
cd rmp/backend

# Run the test script
./run-tests.sh
```

## 📋 Manual Testing Commands

### Basic Test Run
```bash
python -m pytest tests/ -v
```

### Run Tests with Coverage
```bash
python -m pytest tests/ --cov=. --cov-report=html --cov-report=term-missing
```

### Run Specific Test Categories
```bash
# Run only unit tests
python -m pytest tests/ -m unit

# Run only integration tests  
python -m pytest tests/ -m integration

# Skip slow tests
python -m pytest tests/ -m "not slow"
```

### Run Specific Test Files
```bash
# Test authentication only
python -m pytest tests/test_auth.py -v

# Test pool functionality
python -m pytest tests/test_pools.py -v

# Test message board
python -m pytest tests/test_message_board.py -v
```

## 📊 Coverage Reports

### HTML Coverage Report
After running tests with coverage, open:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage Configuration
Coverage settings are in `.coveragerc`:
- **Minimum Coverage**: 70% (configurable)
- **Excluded Files**: Tests, migrations, virtual environment
- **Reports**: HTML, XML, and terminal output

## 🧪 Test Structure

### Test Files
```
tests/
├── __init__.py
├── conftest.py              # Test fixtures and configuration
├── test_main.py             # Application startup tests
├── test_auth.py             # Authentication tests
├── test_pools.py            # Pool management tests
├── test_message_board.py    # Message board tests
├── test_models.py           # Database model tests
└── test_utils.py            # Utility function tests
```

### Test Categories

#### Unit Tests (`@pytest.mark.unit`)
- Test individual functions and classes
- Mock external dependencies
- Fast execution (< 1s per test)

#### Integration Tests (`@pytest.mark.integration`)
- Test component interactions
- Use test database
- Slower execution but more realistic

### Key Fixtures

#### `client`
FastAPI test client for API testing:
```python
def test_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
```

#### `authenticated_client`
Pre-authenticated client with test user:
```python
def test_protected_endpoint(authenticated_client):
    client, user_data = authenticated_client
    response = client.get("/pools/my-pools")
    assert response.status_code == 200
```

#### `db_session`
Test database session:
```python
def test_model(db_session):
    user = User(email="test@example.com")
    db_session.add(user)
    db_session.commit()
```

## 🔧 Writing New Tests

### Test Naming Convention
- File names: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`

### Example Test
```python
import pytest

class TestNewFeature:
    """Test new feature functionality"""
    
    def test_feature_success(self, authenticated_client):
        """Test successful feature operation"""
        client, _ = authenticated_client
        
        response = client.post("/new-feature", json={"data": "test"})
        
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    def test_feature_validation(self, client):
        """Test feature input validation"""
        response = client.post("/new-feature", json={"invalid": "data"})
        
        assert response.status_code == 422
    
    @pytest.mark.integration
    def test_feature_database_integration(self, db_session):
        """Test feature database operations"""
        # Test database interactions
        pass
```

### Mocking External Dependencies
```python
from unittest.mock import patch

@patch('module.external_function')
def test_with_mock(mock_function, client):
    mock_function.return_value = "mocked_value"
    
    response = client.get("/endpoint-using-external-function")
    
    assert response.status_code == 200
    mock_function.assert_called_once()
```

## 🐛 Debugging Tests

### Run Tests with Output
```bash
python -m pytest tests/ -v -s  # -s shows print statements
```

### Run Single Test with Debugging
```bash
python -m pytest tests/test_auth.py::test_login_success -v -s --pdb
```

### Check Test Coverage for Specific Files
```bash
python -m pytest tests/ --cov=auth --cov-report=term-missing
```

## ⚙️ CI/CD Integration

Tests run automatically on:
- **Push to main/develop**: Full test suite
- **Pull Requests**: Full test suite with coverage reporting
- **Multiple Python versions**: 3.9, 3.10, 3.11

### GitHub Actions Workflow
See `.github/workflows/backend-tests.yml` for:
- Automated testing on multiple Python versions
- Coverage reporting to Codecov
- Code quality checks (Black, isort, flake8, mypy)

## 📈 Coverage Goals

### Current Targets
- **Minimum Coverage**: 70%
- **Goal Coverage**: 85%+
- **Critical Modules**: Authentication, Pools, Message Board should have 90%+ coverage

### Coverage by Module
| Module | Target Coverage | Critical Features |
|--------|----------------|-------------------|
| `auth.py` | 90%+ | Login, Registration, JWT |
| `pools.py` | 90%+ | Pool CRUD, Permissions |
| `message_board.py` | 85%+ | Messages, Access Control |
| `models.py` | 80%+ | Data Models, Relationships |
| `main.py` | 75%+ | App Configuration |

## 🚨 Common Issues

### Database Connection Errors
```bash
# Ensure test database is properly configured
export DATABASE_URL=sqlite:///./test.db
```

### Import Errors
```bash
# Add backend directory to Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/backend"
```

### Fixture Conflicts
- Check `conftest.py` for fixture scope issues
- Use `pytest --fixtures` to debug fixture dependencies

### Slow Tests
- Use `@pytest.mark.slow` for tests taking > 5 seconds
- Skip slow tests during development: `pytest -m "not slow"`

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing Patterns](https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#joining-a-session-into-an-external-transaction)
