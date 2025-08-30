#!/bin/bash
# Run My Pool - Local Development Setup Script

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running from project root
if [[ ! -f "main.py" ]]; then
    log_error "Please run this script from the project root directory"
    exit 1
fi

log_info "Setting up Run My Pool for local development..."

# 1. Check Python version
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
log_info "Python version: $PYTHON_VERSION"

# 2. Create virtual environment
if [[ ! -d "venv" ]]; then
    log_info "Creating virtual environment..."
    python3 -m venv venv
    log_success "Virtual environment created"
else
    log_info "Virtual environment already exists"
fi

# 3. Activate virtual environment and install dependencies
log_info "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Create .env file if it doesn't exist
if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        log_info "Creating .env file from .env.example..."
        cp .env.example .env
        log_warning "Please edit .env file with your local database configuration"
    else
        log_info "Creating basic .env file..."
        cat > .env << EOF
# Development Environment Variables
ENVIRONMENT=dev
DB_HOST=localhost
DB_USER=runmypool
DB_PASSWORD=your-password-here
DB_NAME=runmypool
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
SECURITY_ENABLED=true
RATE_LIMIT_ENABLED=false
BCRYPT_ROUNDS=12
EOF
        log_warning "Please edit .env file with your database configuration"
    fi
else
    log_info ".env file already exists"
fi

# 5. Check database connection
log_info "Checking database connection..."
if python3 -c "
import os
import sys
sys.path.append('.')
try:
    from database import get_db_session
    db = get_db_session()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
    log_success "Database connection successful"
else
    log_warning "Database connection failed. Please check your database configuration in .env"
    log_info "To set up MySQL locally:"
    echo "  1. Install MySQL: brew install mysql"
    echo "  2. Start MySQL: brew services start mysql"
    echo "  3. Create database: mysql -u root -e 'CREATE DATABASE runmypool;'"
    echo "  4. Create user: mysql -u root -e \"CREATE USER 'runmypool'@'localhost' IDENTIFIED BY 'your-password';\""
    echo "  5. Grant privileges: mysql -u root -e \"GRANT ALL PRIVILEGES ON runmypool.* TO 'runmypool'@'localhost';\""
fi

# 6. Create database tables
log_info "Creating database tables..."
if python3 -c "
import sys
sys.path.append('.')
try:
    from database import create_tables
    create_tables()
    print('Database tables created successfully')
except Exception as e:
    print(f'Failed to create database tables: {e}')
    sys.exit(1)
" 2>/dev/null; then
    log_success "Database tables created"
else
    log_warning "Failed to create database tables. Please check your database connection."
fi

# 7. Run security tests
log_info "Running security tests..."
if python3 test_security_runner.py; then
    log_success "Security tests passed"
else
    log_warning "Some security tests failed. Check the output above."
fi

# 8. Show startup instructions
log_success "🎉 Local development setup complete!"
echo
echo "=== Next Steps ==="
echo "1. Review and update .env file with your database configuration"
echo "2. Start the development server:"
echo "   source venv/bin/activate"
echo "   uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo "3. Open http://localhost:8000 in your browser"
echo "4. Create an admin user account"
echo
echo "=== Useful Commands ==="
echo "• Run tests: python -m pytest tests/ -v"
echo "• Run security tests: python test_security_runner.py"
echo "• Check code style: flake8 ."
echo "• Run all tests: python run_all_tests.py"
echo
log_info "Happy coding! 🚀"
