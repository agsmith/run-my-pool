#!/bin/bash

# Run pytest with coverage for the FastAPI backend

echo "🧪 Starting pytest coverage for RunMyPool API..."

# Navigate to backend directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Install test dependencies if not already installed
echo "📋 Installing test dependencies..."
pip install -q pytest pytest-cov pytest-asyncio httpx pytest-mock

# Run tests with coverage
echo "🚀 Running tests with coverage..."
python -m pytest tests/ \
    --cov=. \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=xml \
    --cov-fail-under=70 \
    -v \
    --tb=short

# Check if tests passed
if [ $? -eq 0 ]; then
    echo "✅ All tests passed!"
    echo "📊 Coverage report generated in htmlcov/index.html"
    echo "📈 XML report generated as coverage.xml"
else
    echo "❌ Some tests failed or coverage is below threshold"
    exit 1
fi

# Open coverage report in browser (optional)
if command -v open &> /dev/null && [ -f "htmlcov/index.html" ]; then
    echo "🌐 Opening coverage report in browser..."
    open htmlcov/index.html
elif command -v xdg-open &> /dev/null && [ -f "htmlcov/index.html" ]; then
    echo "🌐 Opening coverage report in browser..."
    xdg-open htmlcov/index.html
fi
