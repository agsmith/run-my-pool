# Makefile for RunMyPool Backend Testing

.PHONY: install test test-cov test-fast test-unit test-integration lint format clean help

# Default target
help:
	@echo "RunMyPool Backend Testing Commands"
	@echo "=================================="
	@echo "install      Install test dependencies"
	@echo "test         Run all tests"
	@echo "test-cov     Run tests with coverage report"
	@echo "test-fast    Run tests excluding slow ones"
	@echo "test-unit    Run only unit tests"
	@echo "test-integration  Run only integration tests"
	@echo "lint         Run code quality checks"
	@echo "format       Format code with black and isort"
	@echo "clean        Clean up test artifacts"
	@echo "serve-cov    Serve coverage report locally"

# Install test dependencies
install:
	@echo "📦 Installing test dependencies..."
	pip install pytest pytest-cov pytest-asyncio httpx pytest-mock
	pip install black isort flake8 mypy

# Run all tests
test:
	@echo "🧪 Running all tests..."
	python -m pytest tests/ -v

# Run tests with coverage
test-cov:
	@echo "📊 Running tests with coverage..."
	python -m pytest tests/ \
		--cov=. \
		--cov-report=html \
		--cov-report=term-missing \
		--cov-report=xml \
		--cov-fail-under=70 \
		-v

# Run fast tests only (exclude slow ones)
test-fast:
	@echo "⚡ Running fast tests only..."
	python -m pytest tests/ -v -m "not slow"

# Run unit tests only
test-unit:
	@echo "🔬 Running unit tests..."
	python -m pytest tests/ -v -m "unit"

# Run integration tests only
test-integration:
	@echo "🔗 Running integration tests..."
	python -m pytest tests/ -v -m "integration"

# Lint and format code
lint:
	@echo "🔍 Running code quality checks..."
	@echo "Running Black..."
	black --check .
	@echo "Running isort..."
	isort --check-only .
	@echo "Running flake8..."
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	@echo "Running mypy..."
	mypy . --ignore-missing-imports || true

# Format code
format:
	@echo "✨ Formatting code..."
	black .
	isort .

# Clean up test artifacts
clean:
	@echo "🧹 Cleaning up test artifacts..."
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Serve coverage report locally
serve-cov: test-cov
	@echo "🌐 Serving coverage report on http://localhost:8080"
	@if command -v python3 > /dev/null 2>&1; then \
		cd htmlcov && python3 -m http.server 8080; \
	else \
		cd htmlcov && python -m http.server 8080; \
	fi

# Development workflow
dev: format lint test-fast
	@echo "✅ Development checks complete!"

# CI workflow  
ci: test-cov lint
	@echo "🚀 CI checks complete!"

# Quick smoke test
smoke:
	@echo "💨 Running smoke tests..."
	python -m pytest tests/test_main.py -v
