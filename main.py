from fastapi.responses import JSONResponse
import pytz
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException
import hashlib
import base64
import secrets
import os
import logging

from fastapi import Form
from fastapi.responses import RedirectResponse
# Basic Auth login page routes

import uvicorn
from fastapi import FastAPI, Request, status, Depends
from fastapi import Response
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from typing import Annotated, Optional

from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import models
from database import engine, SessionLocal, text
from sqlalchemy.orm import Session, defer

# Import security modules
from security_config import SecurityConfig, SecurityValidators, PasswordSecurity, SessionSecurity, AuditLogger, RateLimiter
from security_middleware import setup_security_middleware, SecurityUtils
from secure_db import SecureDBOperations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Security logger
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.WARNING)
security_handler = logging.FileHandler('security.log')
security_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
security_logger.addHandler(security_handler)

app = FastAPI(

    
    title="Run My Pool",
    description="Secure NFL Pool Management System",
    version="1.0.0",
    docs_url=None if SecurityConfig.is_production() else "/docs",  # Disable docs in production
    redoc_url=None if SecurityConfig.is_production() else "/redoc"
)

# Add session middleware with secure configuration
app.add_middleware(
    SessionMiddleware, 
    secret_key=SecurityConfig.get_secret_key(),
    max_age=SecurityConfig.SESSION_TIMEOUT_HOURS * 3600,
    same_site="strict",
    https_only=SecurityConfig.is_production()
)

# Setup security middleware
setup_security_middleware(app)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
models.Base.metadata.create_all(bind=engine)

# Initialize secure database operations
secure_db = SecureDBOperations()

class UserBase(BaseModel):
    email: str
    display_name: str
    role: str

class EntryBase(BaseModel):
    entry_name: str
    user_id: int
    active_status: str
    entry_id: int = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Health check endpoint for load balancer
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint for load balancer and monitoring"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "runmypool",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "runmypool",
                "database": "disconnected",
                "error": str(e)
            }
        )


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Get current authenticated user with security validation"""
    import base64
    try:
        session_cookie = request.cookies.get("session-token")
        if not session_cookie:
            return None
        
        try:
            # Decode the base64 session cookie
            decoded_session = base64.b64decode(session_cookie).decode()
            # Session format: username|session_token|timestamp
            parts = decoded_session.split('|')
            if len(parts) != 3:
                logger.warning(f"Invalid session cookie format: expected 3 parts, got {len(parts)}")
                return None
            
            username, session_token, timestamp = parts
            
            # Validate username format
            is_valid, _ = SecurityValidators.validate_username(username)
            if not is_valid:
                logger.warning(f"Invalid username format in session: {username}")
                return None
            
            # Use secure database operation
            user = SecureDBOperations.get_user_by_session_token(db, username, session_token)
            
            if user:
                # Check session expiry
                if user.get("session_token_expiry") and user["session_token_expiry"] < datetime.utcnow():
                    SecureDBOperations.clear_session_token(db, username)
                    return None
                
                return {
                    "user_id": user["user_id"],
                    "username": user["username"],
                    "admin_role": bool(user["admin_role"])
                }
            
            return None
            
        except (ValueError, UnicodeDecodeError) as e:
            logger.warning(f"Invalid session cookie format: {e}")
            return None
        
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}")
        return None

db_depends = Annotated[Session, Depends(get_db)]


# ==== API ENDPOINTS (ALPHABETICALLY ORDERED) ====

@app.get("/", response_class=RedirectResponse)
async def read_root(request: Request):
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/account", response_class=templates.TemplateResponse)
async def account_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    username = user["username"]
    admin_role = user["admin_role"]
    
    # Use secure database operations to prevent SQL injection
    user_data = secure_db.get_user_by_username(db, username)
    user_id = user_data.get("user_id") if user_data else None
    email = user_data.get("email") if user_data else None
    
    # Set role based on admin_role boolean
    role = "admin" if admin_role else "user"
    return templates.TemplateResponse("account.html", {"request": request, "username": username, "role": role, "user_id": user_id, "email": email})


@app.post("/add-entry", response_model=None)
async def add_entry(entry: EntryBase, db: Session = Depends(get_db), request: Request = None):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    username = user["username"]
    admin_role = user["admin_role"]
    # Create entry
    db_entry = models.Entries(
        entry_name=entry.entry_name,
        active_status=entry.active_status,
        user_id=entry.user_id
    )
    db.add(db_entry)
    db.commit()
    # Create picks for all weeks in a loop
    picks = [
        models.Picks(entry_id=db_entry.entry_id, week_num=week, team_id=99, result='open')
        for week in range(1, 19)
    ]
    db.add_all(picks)
    db.commit()
    db.refresh(db_entry)
    logger.info(f"Created entry: {db_entry.entry_name}")
    return db_entry


@app.get("/admin", response_class=templates.TemplateResponse)
async def admin_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    username = user["username"]
    admin_role = user["admin_role"]
    if not admin_role:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("admin.html", {"request": request, "username": username, "role": "admin"})


@app.get("/change-password", response_class=templates.TemplateResponse)
async def change_password_page(request: Request, username: str):
    return templates.TemplateResponse("change_password.html", {"request": request, "username": username, "error": None})


@app.post("/change-password", response_class=templates.TemplateResponse)
async def change_password_post(request: Request, db: Session = Depends(get_db), username: str = Form(...), current_password: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...)):
    # Input validation using security validators
    validation_error = SecurityValidators.validate_password_input(username, current_password, new_password, confirm_password)
    if validation_error:
        return templates.TemplateResponse("change_password.html", {"request": request, "username": username, "error": validation_error})
    
    # Verify current password using secure database operations
    user_data = secure_db.get_user_by_username(db, username)
    if not user_data:
        return templates.TemplateResponse("change_password.html", {"request": request, "username": username, "error": "User not found."})
    
    # Verify current password
    if not PasswordSecurity.verify_password(current_password, user_data["password"], user_data.get("salt", "")):
        # Log failed password change attempt
        security_logger.warning(f"Failed password change attempt for user: {username}")
        return templates.TemplateResponse("change_password.html", {"request": request, "username": username, "error": "Current password is incorrect."})
    
    # Update password securely
    if secure_db.update_user_password(db, username, new_password):
        security_logger.info(f"Password changed successfully for user: {username}")
        response = RedirectResponse(url="/", status_code=302)
        return response
    else:
        return templates.TemplateResponse("change_password.html", {"request": request, "username": username, "error": "Failed to update password."})


@app.get("/create-user", response_class=templates.TemplateResponse)
async def create_user_form(request: Request):
    return templates.TemplateResponse("create_user.html", {"request": request, "error": None})


@app.post("/create-user", response_class=templates.TemplateResponse)
async def create_user_post(request: Request, db: Session = Depends(get_db), username: str = Form(...), email: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)):
    # Input validation using security validators
    validation_error = SecurityValidators.validate_user_creation_input(username, email, password, confirm_password)
    if validation_error:
        return templates.TemplateResponse("create_user.html", {"request": request, "error": validation_error})
    
    # Check if user already exists using secure database operations
    if secure_db.get_user_by_username(db, username) or secure_db.get_user_by_email(db, email):
        return templates.TemplateResponse("create_user.html", {"request": request, "error": "Username or email already exists."})
    
    # Create user securely
    if secure_db.create_user(db, username, email, password):
        security_logger.info(f"New user created: {username}")
        return templates.TemplateResponse("create_user.html", {"request": request, "success": "User created successfully! You can now log in."})
    else:
        return templates.TemplateResponse("create_user.html", {"request": request, "error": "Failed to create user."})


@app.get("/dashboard", response_class=templates.TemplateResponse)
async def get_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    username = user["username"]
    admin_role = user["admin_role"]
    
    # Get user data securely
    user_data = secure_db.get_user_by_username(db, username)
    user_id = user_data.get("user_id") if user_data else None
    
    leagues = []
    if user_id:
        # Get associated leagues from User_Entitlements table (using ORM - safe)
        league_ids = db.query(models.User_Entitlements.league_id).filter_by(user_id=user_id).distinct().all()
        league_ids = [lid[0] for lid in league_ids]
        if league_ids:
            leagues = db.query(models.League).filter(models.League.league_id.in_(league_ids)).all()
    
    # Set role based on admin_role boolean
    role = "admin" if admin_role else "user"
    return templates.TemplateResponse("dashboard.html", {"request": request, "username": username, "leagues": leagues, "role": role})


@app.get("/dashboard/search-league", response_class=templates.TemplateResponse)
async def search_league(request: Request, db: Session = Depends(get_db), query: str = ""):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    username = user["username"]
    admin_role = user["admin_role"]
    
    # Get user data securely
    user_data = secure_db.get_user_by_username(db, username)
    user_id = user_data.get("user_id") if user_data else None
    
    leagues = []
    if user_id:
        league_ids = db.query(models.User_Entitlements.league_id).filter_by(user_id=user_id).distinct().all()
        league_ids = [lid[0] for lid in league_ids]
        if league_ids:
            leagues_query = db.query(models.League).filter(models.League.league_id.in_(league_ids))
            if query:
                # Validate query input to prevent injection
                sanitized_query = SecurityValidators.sanitize_search_input(query)
                if sanitized_query:
                    leagues_query = leagues_query.filter(
                        (models.League.league_name.ilike(f"%{sanitized_query}%")) |
                        (models.League.league_id == sanitized_query if sanitized_query.isdigit() else False)
                    )
            leagues = leagues_query.all()
    
    # Set role based on admin_role boolean
    role = "admin" if admin_role else "user"
    return templates.TemplateResponse("dashboard.html", {"request": request, "username": username, "leagues": leagues, "role": role, "search_query": query})


@app.post("/delete-entry/last", response_model=None)
async def del_last_entry(db: Session = Depends(get_db), request: Request = None):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    username = user["username"]
    admin_role = user["admin_role"]
    last_entry = db.query(models.Entries).order_by(models.Entries.entry_id.desc()).first()
    if not last_entry:
        logger.warning("No entries to delete.")
        return RedirectResponse(url="/entries", status_code=302)
    picks = db.query(models.Picks).filter_by(entry_id=last_entry.entry_id).all()
    for pick in picks:
        db.delete(pick)
    db.commit()
    db.delete(last_entry)
    db.commit()
    logger.info(f"Deleted last entry: {last_entry.entry_id}")
    return RedirectResponse(url="/entries", status_code=302)


@app.delete("/delete-entry/{entry_id}", response_model=None)
async def del_entry(entry_id: int, db: Session = Depends(get_db), request: Request = None):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    username = user["username"]
    admin_role = user["admin_role"]
    # Find entry and related picks
    entry = db.query(models.Entries).filter_by(entry_id=entry_id).first()
    if not entry:
        logger.warning(f"Entry not found: {entry_id}")
        return RedirectResponse(url="/home.html", status_code=302)
    picks = db.query(models.Picks).filter_by(entry_id=entry_id).all()
    for pick in picks:
        db.delete(pick)
    db.commit()
    db.delete(entry)
    db.commit()
    logger.info(f"Deleted entry: {entry_id}")
    return RedirectResponse(url="/home.html", status_code=302)


@app.post("/edit-pick/{pick_id}", response_class=templates.TemplateResponse)
async def edit_pick(request: Request, pick_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    username = user["username"]
    admin_role = user["admin_role"]
    picks = db.query(models.Picks).all()
    # return templates.TemplateResponse("weekly_picks.html", { "request": request, "picks": picks, "username": username })


@app.get("/entries", response_class=templates.TemplateResponse)
async def get_entries(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    username = user["username"]
    admin_role = user["admin_role"]
    entries = db.query(models.Entries).all()
    picks = db.query(models.Picks).all()
    teams = db.query(models.Teams).all()
    games = db.query(models.Schedule).all()
    
    # Check which picks have games that have already started and weekly deadlines
    current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
    picks_with_game_status = []
    
    for pick in picks:
        # Find the game for this pick
        game = db.query(models.Schedule).filter_by(game_id=pick.game_id).first()
        game_started = False
        
        if game and game.start_time:
            # Handle timezone for game start time
            if game.start_time.tzinfo is None:
                game_time_utc = game.start_time.replace(tzinfo=timezone.utc)
            else:
                game_time_utc = game.start_time
            game_started = current_time >= game_time_utc
        
        # Check if weekly deadline has passed
        weekly_deadline_passed = False
        weekly_lock = db.query(models.Weekly_Locks).filter_by(week_num=pick.week_num).first()
        if weekly_lock and weekly_lock.deadline:
            # Handle timezone for deadline
            if weekly_lock.deadline.tzinfo is None:
                deadline_utc = weekly_lock.deadline.replace(tzinfo=timezone.utc)
            else:
                deadline_utc = weekly_lock.deadline
            weekly_deadline_passed = current_time >= deadline_utc
        
        # Create a pick object with game_started and deadline_passed attributes
        pick_with_status = {
            'pick_id': pick.pick_id,
            'entry_id': pick.entry_id,
            'team_id': pick.team_id,

            'week_num': pick.week_num,
            'result': pick.result,
            'game_id': pick.game_id,
            'game_started': game_started,
            'deadline_passed': weekly_deadline_passed
        }
        picks_with_game_status.append(pick_with_status)
    
    # Get user role from User_Entitlements
    user_data = secure_db.get_user_by_username(db, username)
    user_id = user_data.get("user_id") if user_data else None
    # Set role based on admin_role boolean
    role = "admin" if admin_role else "user"
    if user_id:
        ent_row = db.query(models.User_Entitlements).filter_by(user_id=user_id).first()
        if ent_row:
            role = ent_row.role
    return templates.TemplateResponse("home.html", {"request": request, "entries": entries, "picks": picks_with_game_status, "teams": teams, "games": games, "username": username, "role": role})


@app.get("/forgot-password", response_class=templates.TemplateResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request, "error": None})


@app.post("/forgot-password", response_class=templates.TemplateResponse)
async def forgot_password_post(request: Request, db: Session = Depends(get_db), email: str = Form(...)):
    # Validate email input
    is_valid, email_error = SecurityValidators.validate_email(email)
    if not is_valid:
        return templates.TemplateResponse("forgot_password.html", {"request": request, "error": email_error})
    
    # Check if user exists using secure database operations
    user_data = secure_db.get_user_by_email(db, email)
    
    # Always return success message to prevent email enumeration
    success_message = "If an account with that email exists, a password reset link has been sent."
    
    if user_data:
        # Generate reset token and log the attempt
        reset_token = PasswordSecurity.generate_secure_token()
        security_logger.info(f"Password reset requested for email: {email}")
        # TODO: Store token in database and send email
        # For now, just log the token generation
        
    return templates.TemplateResponse("forgot_password.html", {"request": request, "success": success_message})


@app.get("/login", response_class=templates.TemplateResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("basic_login.html", {"request": request, "error": None})


@app.post("/login", response_class=templates.TemplateResponse)
async def login_post(request: Request, db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...)):
    # Input validation using security validators
    validation_error = SecurityValidators.validate_login_input(username, password)
    if validation_error:
        security_logger.warning(f"Invalid login input for username: {username}")
        return templates.TemplateResponse("basic_login.html", {"request": request, "error": "Invalid input format."})
    
    # Rate limiting check
    if RateLimiter.is_user_rate_limited(username, "login"):
        security_logger.warning(f"Rate limited login attempt for username: {username}")
        return templates.TemplateResponse("basic_login.html", {"request": request, "error": "Too many login attempts. Please try again later."})
    
    # Authenticate user using secure database operations
    auth_result = secure_db.authenticate_user(db, username, password)
    
    if auth_result["success"]:
        user_data = auth_result["user"]
        # Generate secure session token
        session_token = PasswordSecurity.generate_secure_token()
        
        # Update user with session token securely
        if secure_db.update_user_session(db, username, session_token):
            # Create secure session cookie
            session_cookie = SessionSecurity.create_session_cookie(username, session_token)
            
            # Log successful login
            security_logger.info(f"Successful login for user: {username}")
            
            if user_data.get("force_password_change"):
                # Redirect to password change page
                response = RedirectResponse(url=f"/change-password?username={username}", status_code=302)
                response.set_cookie(
                    key="session-token", 
                    value=session_cookie, 
                    httponly=True, 
                    secure=SecurityConfig.is_production(),
                    samesite="strict",
                    max_age=SecurityConfig.SESSION_TIMEOUT_HOURS * 3600
                )
                return response
            
            response = RedirectResponse(url="/", status_code=302)
            response.set_cookie(
                key="session-token", 
                value=session_cookie, 
                httponly=True, 
                secure=SecurityConfig.is_production(),
                samesite="strict",
                max_age=SecurityConfig.SESSION_TIMEOUT_HOURS * 3600
            )
            return response
    
    # Log failed login attempt
    security_logger.warning(f"Failed login attempt for username: {username}")
    RateLimiter.record_user_failed_attempt(username, "login")
    
    return templates.TemplateResponse("basic_login.html", {"request": request, "error": "Invalid username or password."})


@app.get("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    session_cookie = request.cookies.get("session-token")
    if session_cookie:
        try:
            # Validate and decode session cookie securely
            session_data = SessionSecurity.validate_session_cookie(session_cookie)
            if session_data:
                username = session_data["username"]
                
                # Clear the session token in the database securely
                secure_db.clear_user_session(db, username)
                security_logger.info(f"User logged out: {username}")
                
        except Exception as e:
            logger.warning(f"Error during logout: {e}")
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session-token")
    return response


@app.get("/reset-password", response_class=templates.TemplateResponse)
async def reset_password_page(request: Request, token: str = ""):
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "error": None})


@app.post("/reset-password", response_class=templates.TemplateResponse)
async def reset_password_post(request: Request, db: Session = Depends(get_db), username: str = Form(...), token: str = Form(...), new_password: str = Form(...)):
    # Validate inputs using security validators
    validation_error = SecurityValidators.validate_password_reset_input(username, token, new_password)
    if validation_error:
        return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "error": validation_error})
    
    # TODO: Implement proper token validation
    # For now, just update the password securely
    try:
        if secure_db.update_user_password(db, username, new_password):
            security_logger.info(f"Password reset successfully for user: {username}")
            return templates.TemplateResponse("basic_login.html", {"request": request, "success": "Password reset successfully! You can now log in with your new password."})
        else:
            return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "error": "Failed to reset password. Please try again."})
    except Exception as e:
        logger.error(f"Error resetting password for user {username}: {e}")
        return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "error": "An error occurred. Please try again."})


@app.get("/schedule/{week_num}")
async def get_week_schedule(week_num: int, request: Request, db: Session = Depends(get_db)):
    games = db.query(models.Schedule).filter_by(week_num=week_num).all()
    teams = db.query(models.Teams).all()
    team_dict = {team.team_id: team for team in teams}
    result = []
    picked_teams = []
    
    # Get current time for comparison
    from datetime import datetime, timezone
    current_time = datetime.now(timezone.utc)
    
    # Get pick_id from query parameters
    pick_id = request.query_params.get('pick_id')
    
    # Check if the current pick's game has already started
    current_pick_game_started = False
    if pick_id:
        try:
            pick_id_int = int(pick_id)
            current_pick = db.query(models.Picks).filter_by(pick_id=pick_id_int).first()
            if current_pick and current_pick.game_id:
                current_game = db.query(models.Schedule).filter_by(game_id=current_pick.game_id).first()
                if current_game and current_game.start_time:
                    # Handle timezone for current game start time
                    if current_game.start_time.tzinfo is None:
                        current_game_time_utc = current_game.start_time.replace(tzinfo=timezone.utc)
                    else:
                        current_game_time_utc = current_game.start_time
                    
                    current_pick_game_started = current_time >= current_game_time_utc
        except (ValueError, TypeError):
            pass
    
    # If current pick's game has started, return error
    if current_pick_game_started:
        return JSONResponse(content={"error": "Cannot change pick - the current game has already started", "currentGameStarted": True}, status_code=400)
    
    # Check if weekly deadline has passed
    weekly_lock = db.query(models.Weekly_Locks).filter_by(week_num=week_num).first()
    if weekly_lock and weekly_lock.deadline:
        # Handle timezone for deadline
        if weekly_lock.deadline.tzinfo is None:
            deadline_utc = weekly_lock.deadline.replace(tzinfo=timezone.utc)
        else:
            deadline_utc = weekly_lock.deadline
        
        if current_time >= deadline_utc:
            return JSONResponse(content={"error": "Cannot change pick - the weekly deadline has passed", "deadlinePassed": True}, status_code=400)
    
    # Get already picked teams for this entry
    if pick_id:
        try:
            pick_id = int(pick_id)
            # Find the entry_id for this pick
            current_pick = db.query(models.Picks).filter_by(pick_id=pick_id).first()
            if current_pick:
                # Get all picks for this entry
                entry_picks = db.query(models.Picks).filter_by(entry_id=current_pick.entry_id).all()
                picked_teams = [pick.team_id for pick in entry_picks if pick.team_id and pick.team_id != 98]  # Exclude BYE week (team_id 98)
        except (ValueError, TypeError):
            pass  # Invalid pick_id, continue without filtering
    
    for game in games:
        home_team = team_dict.get(game.home_team)
        away_team = team_dict.get(game.away_team)
        
        if home_team and away_team:
            # Check if teams are already picked by this entry
            home_already_picked = home_team.team_id in picked_teams
            away_already_picked = away_team.team_id in picked_teams
            
            # Check if game has already started
            game_started = False
            if game.start_time:
                # Assume start_time is stored in UTC or convert to UTC if needed
                if game.start_time.tzinfo is None:
                    # If no timezone info, assume it's UTC
                    game_time_utc = game.start_time.replace(tzinfo=timezone.utc)
                else:
                    game_time_utc = game.start_time
                game_started = current_time >= game_time_utc
            
            # Teams are disabled if already picked OR if game has started
            home_disabled = home_already_picked or game_started
            away_disabled = away_already_picked or game_started
            
            result.append({
                "game_id": game.game_id,
                "home_team": {
                    "team_id": home_team.team_id,
                    "name": home_team.name,
                    "abbrv": home_team.abbrv,
                    "logo": home_team.logo
                },
                "away_team": {
                    "team_id": away_team.team_id,
                    "name": away_team.name,
                    "abbrv": away_team.abbrv,
                    "logo": away_team.logo
                },
                "game_time": game.start_time.isoformat() if game.start_time else None,
                "homeSelectable": not home_disabled,
                "awaySelectable": not away_disabled,
                "homeDisabled": home_disabled,
                "awayDisabled": away_disabled,
                "gameStarted": game_started
            })
    return JSONResponse(content={"games": result, "pickedTeams": picked_teams})


@app.post("/submit-pick", response_class=JSONResponse)
async def submit_pick(request: Request, db: Session = Depends(get_db), pick_id: str = Form(...), week_num: str = Form(...), team: str = Form(...), game_id: str = Form(None)):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse(content={"error": "Not logged in"}, status_code=401)
    username = user["username"]
    admin_role = user["admin_role"]
    # Convert pick_id and week_num to int
    try:
        pick_id = int(pick_id)
        week_num = int(week_num)
    except (TypeError, ValueError):
        return JSONResponse(content={"error": "Invalid pick_id or week_num"}, status_code=422)
    # Find the team_id for the selected team abbreviation
    team_obj = db.query(models.Teams).filter_by(abbrv=team).first()
    if not team_obj:
        return JSONResponse(content={"error": "Invalid team"}, status_code=400)
    
    # Get the current pick to find the entry_id
    pick = db.query(models.Picks).filter_by(pick_id=pick_id).first()
    if not pick:
        return JSONResponse(content={"error": "Pick not found"}, status_code=404)
    
    # Check if the current pick's game has already started
    if pick.game_id:
        current_game = db.query(models.Schedule).filter_by(game_id=pick.game_id).first()
        if current_game and current_game.start_time:
            current_time = datetime.now(timezone.utc)
            
            # Handle timezone for current game start time
            if current_game.start_time.tzinfo is None:
                current_game_time_utc = current_game.start_time.replace(tzinfo=timezone.utc)
            else:
                current_game_time_utc = current_game.start_time
            
            if current_time >= current_game_time_utc:
                return JSONResponse(content={"error": "Cannot change pick - the current game has already started"}, status_code=400)
    
    # Check if weekly deadline has passed
    current_time = datetime.now(timezone.utc)
    weekly_lock = db.query(models.Weekly_Locks).filter_by(week_num=week_num).first()
    if weekly_lock and weekly_lock.deadline:
        # Handle timezone for deadline
        if weekly_lock.deadline.tzinfo is None:
            deadline_utc = weekly_lock.deadline.replace(tzinfo=timezone.utc)
        else:
            deadline_utc = weekly_lock.deadline
        
        if current_time >= deadline_utc:
            return JSONResponse(content={"error": "Cannot change pick - the weekly deadline has passed"}, status_code=400)
    
    # Check if this team is already picked by this entry
    existing_pick = db.query(models.Picks).filter_by(
        entry_id=pick.entry_id, 
        team_id=team_obj.team_id
    ).filter(models.Picks.pick_id != pick_id).first()  # Exclude current pick
    
    if existing_pick:
        return JSONResponse(content={"error": f"Team {team} has already been selected for this entry"}, status_code=400)
    
    # Check if the new game has already started (if game_id is provided)
    if game_id:
        try:
            game_id = int(game_id)
            new_game = db.query(models.Schedule).filter_by(game_id=game_id).first()
            if new_game and new_game.start_time:
                current_time = datetime.now(timezone.utc)
                
                # Handle timezone for new game start time
                if new_game.start_time.tzinfo is None:
                    new_game_time_utc = new_game.start_time.replace(tzinfo=timezone.utc)
                else:
                    new_game_time_utc = new_game.start_time
                
                if current_time >= new_game_time_utc:
                    return JSONResponse(content={"error": f"Cannot select team {team} - game has already started"}, status_code=400)
        except (ValueError, TypeError):
            pass  # Invalid game_id, continue without time check
    
    # Update the pick for the given pick_id and week_num
    pick.team_id = team_obj.team_id
    if game_id:
        try:
            pick.game_id = int(game_id)
        except (ValueError, TypeError):
            pass  # Keep existing game_id if new one is invalid
    db.commit()
    return JSONResponse(content={"success": True, "message": f"Pick updated for week {week_num}"})


@app.get("/admin/get-admin-users")
async def get_admin_users(request: Request, db: Session = Depends(get_db)):
    """Get list of all admin users"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not user["admin_role"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all admin users from both tables
    admin_users = db.query(models.Users).filter(models.Users.admin == True).all()
    
    admin_list = []
    for user_record in admin_users:
        # Get additional info from User_IAM if available
        user_iam = db.query(models.User_IAM).filter(models.User_IAM.user_id == user_record.user_id).first()
        admin_list.append({
            "user_id": user_record.user_id,
            "name": user_record.name,
            "username": user_record.username,
            "email": user_iam.email if user_iam else "N/A"
        })
    
    return JSONResponse(content={"admins": admin_list})


@app.post("/admin/assign-admin")
async def assign_admin(request: Request, db: Session = Depends(get_db)):
    """Assign admin access to a user"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not user["admin_role"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Parse request data
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        
        if not username:
            return JSONResponse(content={"success": False, "message": "Username is required"})
        
        # Find user by username
        target_user = db.query(models.Users).filter(models.Users.username == username).first()
        if not target_user:
            return JSONResponse(content={"success": False, "message": f"User '{username}' not found"})
        
        # Check if user is already admin
        if target_user.admin:
            return JSONResponse(content={"success": False, "message": f"User '{username}' is already an admin"})
        
        # Assign admin access
        target_user.admin = True
        
        # Also update User_IAM table if the user exists there
        user_iam = db.query(models.User_IAM).filter(models.User_IAM.user_id == target_user.user_id).first()
        if user_iam:
            user_iam.admin_role = True
        
        db.commit()
        
        logger.info(f"Admin access assigned to user {username} by {user['username']}")
        return JSONResponse(content={"success": True, "message": f"Admin access granted to {username}"})
        
    except Exception as e:
        logger.error(f"Error assigning admin access: {str(e)}")
        return JSONResponse(content={"success": False, "message": "Failed to assign admin access"})


@app.post("/admin/revoke-admin")
async def revoke_admin(request: Request, db: Session = Depends(get_db)):
    """Revoke admin access from a user"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not user["admin_role"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Parse request data
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        
        if not username:
            return JSONResponse(content={"success": False, "message": "Username is required"})
        
        # Find user by username
        target_user = db.query(models.Users).filter(models.Users.username == username).first()
        if not target_user:
            return JSONResponse(content={"success": False, "message": f"User '{username}' not found"})
        
        # Check if user is admin
        if not target_user.admin:
            return JSONResponse(content={"success": False, "message": f"User '{username}' is not an admin"})
        
        # Prevent user from revoking their own admin access
        if target_user.username == user["username"]:
            return JSONResponse(content={"success": False, "message": "Cannot revoke your own admin access"})
        
        # Revoke admin access
        target_user.admin = False
        
        # Also update User_IAM table if the user exists there
        user_iam = db.query(models.User_IAM).filter(models.User_IAM.user_id == target_user.user_id).first()
        if user_iam:
            user_iam.admin_role = False
        
        db.commit()
        
        logger.info(f"Admin access revoked from user {username} by {user['username']}")
        return JSONResponse(content={"success": True, "message": f"Admin access revoked from {username}"})
        
    except Exception as e:
        logger.error(f"Error revoking admin access: {str(e)}")
        return JSONResponse(content={"success": False, "message": "Failed to revoke admin access"})


if __name__ == "__main__":
    logger.info("starting server with dev configuration")
    uvicorn.run(app, host="127.0.0.1", port=9000)
