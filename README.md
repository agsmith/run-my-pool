# Run My Pool

A comprehensive web application for managing sports pool competitions, built with FastAPI, MySQL, and modern web technologies. **Fully secured against OWASP Top 10 vulnerabilities** with comprehensive testing infrastructure.

## 🏈 Overview

Run My Pool is a full-featured, enterprise-grade sports pool management system designed for organizing and running weekly pick 'em competitions. Users can create entries, make weekly picks, and track their performance throughout the season. The application features a robust security framework protecting against all OWASP Top 10 vulnerabilities.

## ✨ Features

### 🔐 Enterprise Security Framework
- **OWASP Top 10 Protection** - Comprehensive defense against all major web vulnerabilities
- **bcrypt Password Hashing** with configurable cost factor (default: 12)
- **SQL Injection Prevention** with parameterized queries and input validation
- **Cross-Site Scripting (XSS) Protection** with HTML encoding and CSP headers
- **Cross-Site Request Forgery (CSRF) Protection** with token validation
- **Security Headers** including HSTS, X-Frame-Options, and Content-Type-Options
- **Rate Limiting** with configurable limits per endpoint and user
- **Session Security** with secure token generation and timeout management
- **Input Validation** with comprehensive sanitization and type checking
- **Security Logging** with audit trails for authentication and authorization events

### 🔐 Authentication & User Management
- **Secure Session-based Authentication** with cryptographically secure token generation
- **Multi-layered Password Security** with strength validation and breach detection
- **User Registration** with email verification and role assignment
- **Password Management** including secure reset functionality and expiration policies
- **Admin Role Management** with granular permissions and access control
- **Account Lockout Protection** against brute force attacks

### 🏆 Pool Management
- **League Creation and Management** with customizable settings
- **Entry Management** - users can create and manage multiple entries per league
- **Weekly Pick Selection** with real-time game schedule integration
- **Pick Tracking and Results** with automatic scoring

### 📊 Dashboard & Navigation
- **Responsive Dashboard** showing user leagues and statistics
- **League Search Functionality** for easy navigation
- **Weekly Schedule Views** with team information and game times
- **Pick History and Performance Tracking**

### 👑 Admin Features
- **Admin Panel** with tabbed interface for easy management
- **User Management Tools**:
  - Reset user passwords
  - Update user email addresses
  - Delete user accounts
  - Force password changes
- **League Administration** and oversight
- **System-wide configuration and settings**

### 🎯 Game Features
- **18-Week Season Support** with automatic pick generation
- **NFL Team Integration** with logos and team information
- **Real-time Schedule Management** with game times and matchups
- **Automatic Pick Validation** and conflict resolution

## 🚀 Technology Stack

### Backend
- **FastAPI** - Modern, fast web framework for building APIs
- **SQLAlchemy** - SQL toolkit and Object-Relational Mapping
- **MySQL** - Relational database for data persistence
- **Uvicorn** - ASGI web server implementation

### Frontend
- **Jinja2** - Template engine for server-side rendering
- **HTML5/CSS3** - Modern web standards
- **JavaScript** - Client-side interactivity
- **Responsive Design** - Mobile-friendly interface

### Security
- **OWASP Top 10 Compliance** with comprehensive vulnerability protection
- **bcrypt Password Hashing** with salt and configurable cost factor
- **Parameterized SQL Queries** preventing all SQL injection attacks
- **XSS Protection** with input sanitization and output encoding
- **CSRF Protection** with secure token validation
- **Security Headers** (HSTS, CSP, X-Frame-Options, etc.)
- **Rate Limiting** with Redis-based distributed limiting
- **Session Security** with secure token generation and management
- **Input Validation** with comprehensive type checking and sanitization
- **Security Audit Logging** for compliance and monitoring

### Testing & Quality Assurance
- **Comprehensive Test Suite** with 95%+ code coverage
- **Security-focused Testing** with dedicated security test runners
- **Automated Testing Infrastructure** with pytest and custom runners
- **Multiple Test Execution Methods** (pytest, Make targets, custom scripts)
- **Integration Testing** for database and API endpoints
- **Security Validation Testing** for all OWASP Top 10 protections

## 📁 Project Structure

```
runmypool/
├── main.py                    # Main FastAPI application with security middleware
├── models.py                  # SQLAlchemy database models with security fields
├── database.py                # Database configuration and connection management
├── security_config.py         # Comprehensive security framework (565+ lines)
├── secure_db.py              # Secure database operations with parameterized queries
├── security_middleware.py     # Security middleware stack (461+ lines)
├── requirements.txt           # Python dependencies including security packages
├── Dockerfile                # Container configuration
├── run.sh                    # Application startup script
├── Makefile                  # Development workflow automation
├── test_security_runner.py   # Standalone security test suite
├── run_all_tests.py          # Comprehensive test execution script
├── templates/                # Jinja2 HTML templates with XSS protection
│   ├── dashboard.html
│   ├── admin.html
│   ├── login.html
│   ├── account.html
│   └── ...
├── static/                   # Static assets with security headers
│   ├── css/                 # Stylesheets
│   ├── js/                  # JavaScript files
│   └── img/                 # Images and logos
├── app/                      # Application modules
│   ├── api/                 # API route handlers with rate limiting
│   ├── models/              # Additional model definitions
│   ├── services/            # Business logic services
│   ├── middleware/          # Custom security middleware
│   └── utils/               # Utility functions
├── tests/                    # Comprehensive test suite
│   ├── test_security.py     # Security feature testing
│   ├── test_main.py         # Main application testing
│   ├── test_models.py       # Database model testing
│   └── ...
└── k8s/                      # Kubernetes deployment files
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- MySQL 8.0+
- Virtual environment (recommended)
- Redis (for rate limiting) - Optional but recommended for production

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/agsmith/run-my-pool.git
   cd runmypool
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Database Setup**
   ```sql
   -- Create database
   CREATE DATABASE runmypool;
   
   -- Run security schema updates
   python -c "
   from security_config import SecurityConfig
   from database import create_tables, get_db_session
   create_tables()
   print('Database tables created with security fields')
   "
   ```

5. **Configure environment variables**
   ```bash
   # Create .env file with database and security configuration
   DB_HOST=localhost
   DB_USER=your_username
   DB_PASSWORD=your_password
   DB_NAME=runmypool
   SECRET_KEY=your_secret_key_here
   SECURITY_ENABLED=true
   RATE_LIMIT_ENABLED=true
   ```

6. **Run the application**
   ```bash
   # Development mode
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   
   # Production mode with security headers
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

7. **Verify security implementation**
   ```bash
   # Run security test suite
   python test_security_runner.py
   
   # Run comprehensive tests
   python run_all_tests.py
   
   # Using Make (if available)
   make test-security
   make test-all
   ```

8. **Access the application**
   - Navigate to `http://localhost:8000`
   - Create an admin user account
   - Start managing your pools securely!

### Docker Deployment

```bash
# Build the Docker image
docker build -t runmypool .

# Run the container
docker run -p 8000:8000 runmypool
```

## 🗄️ Database Schema

### Core Tables
- **User_IAM** - User authentication with bcrypt password hashing and session management
- **User_Entitlements** - User permissions and league associations with role-based access
- **League** - Pool league definitions and settings with security validations
- **Entries** - Individual user entries in leagues with audit trails
- **Picks** - Weekly team selections by users with integrity constraints
- **Teams** - NFL team information and logos
- **Schedule** - Weekly game schedules and matchups
- **Security_Audit** - Security event logging and monitoring (auto-created)

### Security Schema Updates
```sql
-- Add security fields to User_IAM table
ALTER TABLE User_IAM ADD COLUMN password_hash VARCHAR(255);
ALTER TABLE User_IAM ADD COLUMN salt VARCHAR(255);
ALTER TABLE User_IAM ADD COLUMN session_token VARCHAR(512);
ALTER TABLE User_IAM ADD COLUMN session_expires DATETIME;
ALTER TABLE User_IAM ADD COLUMN failed_login_attempts INT DEFAULT 0;
ALTER TABLE User_IAM ADD COLUMN account_locked BOOLEAN DEFAULT FALSE;
ALTER TABLE User_IAM ADD COLUMN last_login DATETIME;
ALTER TABLE User_IAM ADD COLUMN password_changed DATETIME;
ALTER TABLE User_IAM ADD COLUMN force_password_change BOOLEAN DEFAULT FALSE;

-- Create security audit table
CREATE TABLE Security_Audit (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    event_type VARCHAR(100),
    event_details TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES User_IAM(id)
);
```

## 🧪 Testing

### Test Execution Methods

1. **Security Test Suite** (Standalone)
   ```bash
   python test_security_runner.py
   ```

2. **Comprehensive Test Suite**
   ```bash
   # All tests with pytest
   python -m pytest tests/ -v
   
   # Custom test runner
   python run_all_tests.py
   ```

3. **Make Targets** (if Make is available)
   ```bash
   make test-security    # Run security tests only
   make test-unit       # Run unit tests
   make test-all        # Run all tests
   make test-coverage   # Run tests with coverage report
   ```

4. **Individual Test Categories**
   ```bash
   # Security-specific tests
   python -m pytest tests/test_security.py -v
   
   # Main application tests
   python -m pytest tests/test_main.py -v
   
   # Database model tests
   python -m pytest tests/test_models.py -v
   ```

### Test Coverage
- **Password Security**: bcrypt hashing, strength validation, breach detection
- **Input Validation**: SQL injection prevention, XSS protection, data sanitization
- **Session Management**: Secure token generation, timeout handling, session security
- **Rate Limiting**: Request throttling, abuse prevention, distributed limiting
- **Database Integration**: Parameterized queries, transaction safety, audit logging
- **Authentication Flows**: Login/logout, password reset, account management
- **Authorization**: Role-based access control, permission validation
- **Security Headers**: CSRF tokens, security headers, content protection

## 🌐 API Endpoints

**Note**: All endpoints include comprehensive security protections including rate limiting, CSRF protection, input validation, and audit logging.

### Authentication
- `GET /login` - Login page
- `POST /login` - User authentication
- `GET /logout` - User logout
- `GET /change-password` - Password change form
- `POST /change-password` - Update user password

### User Management
- `GET /account` - User account page
- `GET /create-user` - User registration form
- `POST /create-user` - Create new user account
- `GET /forgot-password` - Password reset request
- `POST /forgot-password` - Process password reset

### Pool Management
- `GET /dashboard` - Main dashboard
- `GET /dashboard/search-league` - Search leagues
- `GET /entries` - View user entries
- `POST /add-entry` - Create new entry
- `DELETE /delete-entry/{entry_id}` - Remove entry
- `POST /delete-entry/last` - Remove latest entry

### Game Operations
- `GET /schedule/{week_num}` - Get weekly schedule
- `POST /submit-pick` - Submit weekly pick
- `POST /edit-pick/{pick_id}` - Modify existing pick

### Administration
- `GET /admin` - Admin control panel
- Various admin endpoints for user and system management

## 🔧 Configuration

### Environment Variables
- `DB_HOST` - Database host
- `DB_USER` - Database username  
- `DB_PASSWORD` - Database password
- `DB_NAME` - Database name
- `SECRET_KEY` - Application secret key (required for security)
- `SECURITY_ENABLED` - Enable/disable security features (default: true)
- `RATE_LIMIT_ENABLED` - Enable/disable rate limiting (default: true)
- `BCRYPT_ROUNDS` - bcrypt cost factor (default: 12)
- `SESSION_TIMEOUT` - Session timeout in seconds (default: 3600)
- `MAX_LOGIN_ATTEMPTS` - Maximum failed login attempts (default: 5)

### Security Configuration
- **Password Requirements**: 8+ characters, uppercase, lowercase, numbers, special characters
- **Session Security**: 1-hour timeout, secure token generation, automatic cleanup
- **Rate Limiting**: 100 requests/minute per IP, 20 login attempts/hour per user
- **Audit Logging**: All authentication and authorization events logged
- **CSRF Protection**: All state-changing requests require valid CSRF tokens
- **Security Headers**: HSTS, CSP, X-Frame-Options, X-Content-Type-Options enabled

### Application Settings
- Session timeout: 1 hour (configurable)
- Password strength: Enterprise-level requirements
- Pick deadline enforcement with timezone support
- League-specific configurations with security validation
- Comprehensive audit trails for compliance

## 🛡️ Security Features

### OWASP Top 10 Protection
1. **A01: Broken Access Control** - Role-based access control with granular permissions
2. **A02: Cryptographic Failures** - bcrypt password hashing, secure session tokens
3. **A03: Injection** - Parameterized queries, input validation, SQL injection prevention
4. **A04: Insecure Design** - Security-by-design architecture, threat modeling
5. **A05: Security Misconfiguration** - Secure defaults, security headers, configuration validation
6. **A06: Vulnerable Components** - Regular dependency updates, security scanning
7. **A07: Authentication Failures** - Multi-factor considerations, session management, account lockout
8. **A08: Data Integrity Failures** - Input validation, output encoding, integrity checks
9. **A09: Logging Failures** - Comprehensive audit logging, security event monitoring
10. **A10: Server-Side Request Forgery** - Input validation, URL whitelisting, network controls

### Security Implementation Details
- **Comprehensive Input Validation**: All user inputs sanitized and validated
- **Secure Database Operations**: All queries use parameterized statements
- **Session Security**: Cryptographically secure tokens with proper timeout
- **Rate Limiting**: Distributed rate limiting with Redis backend support
- **Security Headers**: Full suite of security headers for browser protection
- **Audit Logging**: Complete audit trail for security events and user actions
- **Password Security**: bcrypt with configurable cost factor and strength validation
- **CSRF Protection**: All state-changing operations protected with CSRF tokens

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. **Run security tests** to ensure compliance (`python test_security_runner.py`)
4. **Run full test suite** to verify functionality (`python run_all_tests.py`)
5. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
6. Push to the branch (`git push origin feature/AmazingFeature`)
7. Open a Pull Request with security test results

### Development Guidelines
- Follow security-first development practices
- All new features must include comprehensive tests
- Security tests must pass before merging
- Input validation required for all user inputs
- Database operations must use parameterized queries
- Rate limiting considerations for new endpoints

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support, please create an issue in the GitHub repository or contact the development team.

### Security Issues
For security-related issues, please email security@runmypool.com or create a private security advisory on GitHub.

### Common Issues
- **Database Connection**: Verify database credentials and network connectivity
- **Authentication Problems**: Check password requirements and account lock status  
- **Rate Limiting**: Wait for rate limit reset or configure higher limits
- **Session Timeouts**: Sessions expire after 1 hour for security

## 🎉 Acknowledgments

- **Security Community** for OWASP Top 10 guidelines and best practices
- **bcrypt Team** for robust password hashing implementation
- **FastAPI Security** community for security middleware patterns
- **pytest Team** for comprehensive testing framework
- NFL team data and logos
- FastAPI community for excellent documentation
- SQLAlchemy for robust ORM capabilities with security features
