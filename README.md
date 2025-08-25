# Run My Pool

A comprehensive web application for managing sports pool competitions, built with FastAPI, MySQL, and modern web technologies.

## 🏈 Overview

Run My Pool is a full-featured sports pool management system designed for organizing and running weekly pick 'em competitions. Users can create entries, make weekly picks, and track their performance throughout the season.

## ✨ Features

### 🔐 Authentication & User Management
- **Secure Session-based Authentication** with Base64 encoded session tokens
- **User Registration** with password validation and email verification
- **Password Management** including reset functionality and forced password changes
- **Admin Role Management** with role-based access control
- **Account Management** with user profile and settings

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
- **Session Token Authentication** with secure cookie management
- **Password Hashing** using SHA-256
- **SQL Injection Prevention** with input validation
- **CSRF Protection** and secure headers

## 📁 Project Structure

```
runmypool/
├── main.py              # Main FastAPI application with all routes
├── models.py            # SQLAlchemy database models
├── database.py          # Database configuration and session management
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container configuration
├── run.sh              # Application startup script
├── templates/          # Jinja2 HTML templates
│   ├── dashboard.html
│   ├── admin.html
│   ├── login.html
│   ├── account.html
│   └── ...
├── static/             # Static assets
│   ├── css/           # Stylesheets
│   ├── js/            # JavaScript files
│   └── img/           # Images and logos
├── app/               # Application modules
│   ├── api/           # API route handlers
│   ├── models/        # Additional model definitions
│   ├── services/      # Business logic services
│   ├── middleware/    # Custom middleware
│   └── utils/         # Utility functions
└── k8s/               # Kubernetes deployment files
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- MySQL 8.0+
- Virtual environment (recommended)

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
   
   -- Create required tables (see Database Schema section)
   ```

5. **Configure environment variables**
   ```bash
   # Create .env file with database configuration
   DB_HOST=localhost
   DB_USER=your_username
   DB_PASSWORD=your_password
   DB_NAME=runmypool
   ```

6. **Run the application**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access the application**
   - Navigate to `http://localhost:8000`
   - Create an admin user account
   - Start managing your pools!

### Docker Deployment

```bash
# Build the Docker image
docker build -t runmypool .

# Run the container
docker run -p 8000:8000 runmypool
```

## 🗄️ Database Schema

### Core Tables
- **User_IAM** - User authentication and session management
- **User_Entitlements** - User permissions and league associations
- **League** - Pool league definitions and settings
- **Entries** - Individual user entries in leagues
- **Picks** - Weekly team selections by users
- **Teams** - NFL team information and logos
- **Schedule** - Weekly game schedules and matchups

### Required DDL
```sql
-- Add session token support
ALTER TABLE User_IAM ADD COLUMN session_token VARCHAR(256);
```

## 🌐 API Endpoints

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
- `SECRET_KEY` - Application secret key

### Application Settings
- Session timeout: 1 hour
- Password requirements: 8+ characters, numbers, uppercase
- Pick deadline enforcement
- League-specific configurations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support, please create an issue in the GitHub repository or contact the development team.

## 🎉 Acknowledgments

- NFL team data and logos
- FastAPI community for excellent documentation
- SQLAlchemy for robust ORM capabilities
