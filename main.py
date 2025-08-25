from fastapi.responses import JSONResponse
import pytz
from datetime import datetime

from fastapi import HTTPException
import hashlib


from fastapi import Form
from fastapi.responses import RedirectResponse
# Basic Auth login page routes

import uvicorn
from fastapi import FastAPI, Request, status, Depends
from fastapi import Response
import secrets
from pydantic import BaseModel
from typing import Annotated

from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import models
from database import engine, SessionLocal, text
from sqlalchemy.orm import Session, defer

import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)



app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
models.Base.metadata.create_all(bind=engine)

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


def get_current_user(request: Request, db: Session = Depends(get_db)):
    import base64
    session_cookie = request.cookies.get("session-token")
    if not session_cookie:
        return None
    
    try:
        # Decode the base64 session cookie
        decoded_session = base64.b64decode(session_cookie).decode()
        username, session_token = decoded_session.split(':', 1)
        
        # Validate session token in database
        user = db.execute(
            text(f"SELECT username, admin_role FROM User_IAM WHERE username='{username}' AND session_token='{session_token}'")
        ).fetchone()
        
        if user:
            return {"username": user[0], "admin_role": user[1]}
        else:
            return None
    except Exception:
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
    user_row = db.execute(text(f"SELECT user_id, email FROM User_IAM WHERE username='{username}'")).fetchone()
    user_id = user_row[0] if user_row else None
    email = user_row[1] if user_row else None
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
    import re
    # Validation
    if new_password != confirm_password:
        return templates.TemplateResponse("change_password.html", {"request": request, "username": username, "error": "Passwords do not match."})
    elif len(new_password) < 8:
        return templates.TemplateResponse("change_password.html", {"request": request, "username": username, "error": "Password must be at least 8 characters long."})
    elif not re.search(r"[0-9]", new_password):
        return templates.TemplateResponse("change_password.html", {"request": request, "username": username, "error": "Password must contain at least one number."})
    elif not re.search(r"[A-Z]", new_password):
        return templates.TemplateResponse("change_password.html", {"request": request, "username": username, "error": "Password must contain at least one uppercase letter."})
    # Verify current password
    user = db.execute(text(f"SELECT password FROM User_IAM WHERE username='{username}'")).fetchone()
    if user:
        current_hashed = hashlib.sha256(current_password.encode()).hexdigest()
        if not secrets.compare_digest(user[0], current_hashed):
            return templates.TemplateResponse("change_password.html", {"request": request, "username": username, "error": "Current password is incorrect."})
        # Update password
        new_hashed = hashlib.sha256(new_password.encode()).hexdigest()
        db.execute(text(f"UPDATE User_IAM SET password='{new_hashed}', force_password_change=0 WHERE username='{username}'"))
        db.commit()
        response = RedirectResponse(url="/", status_code=302)
        return response
    return templates.TemplateResponse("change_password.html", {"request": request, "username": username, "error": "User not found."})


@app.get("/create-user", response_class=templates.TemplateResponse)
async def create_user_form(request: Request):
    return templates.TemplateResponse("create_user.html", {"request": request, "error": None})


@app.post("/create-user", response_class=templates.TemplateResponse)
async def create_user_post(request: Request, db: Session = Depends(get_db), username: str = Form(...), email: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)):
    import re
    # Input validation
    if not re.match(r'^[A-Za-z0-9_.-]{3,128}$', username):
        return templates.TemplateResponse("create_user.html", {"request": request, "error": "Invalid username format."})
    if len(password) > 256:
        return templates.TemplateResponse("create_user.html", {"request": request, "error": "Password too long."})
    if password != confirm_password:
        return templates.TemplateResponse("create_user.html", {"request": request, "error": "Passwords do not match."})
    # Check if user already exists
    existing_user = db.execute(text(f"SELECT username FROM User_IAM WHERE username='{username}' OR email='{email}'")).fetchone()
    if existing_user:
        return templates.TemplateResponse("create_user.html", {"request": request, "error": "Username or email already exists."})
    # Create user
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    db.execute(
        text(f"INSERT INTO User_IAM (username, email, password, admin_role, force_password_change, created_time) VALUES ('{username}', '{email}', '{hashed_pw}', 0, 0, NOW())")
    )
    db.commit()
    return templates.TemplateResponse("create_user.html", {"request": request, "success": "User created successfully! You can now log in."})


@app.get("/dashboard", response_class=templates.TemplateResponse)
async def get_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    username = user["username"]
    admin_role = user["admin_role"]
    # Find user_id from User_IAM table
    user_row = db.execute(text(f"SELECT user_id FROM User_IAM WHERE username='{username}'")).fetchone()
    user_id = user_row[0] if user_row else None
    leagues = []
    if user_id:
        # Get associated leagues from User_Entitlements table
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
    user_row = db.execute(text(f"SELECT user_id FROM User_IAM WHERE username='{username}'")).fetchone()
    user_id = user_row[0] if user_row else None
    leagues = []
    if user_id:
        league_ids = db.query(models.User_Entitlements.league_id).filter_by(user_id=user_id).distinct().all()
        league_ids = [lid[0] for lid in league_ids]
        if league_ids:
            leagues_query = db.query(models.League).filter(models.League.league_id.in_(league_ids))
            if query:
                leagues_query = leagues_query.filter(
                    (models.League.league_name.ilike(f"%{query}%")) |
                    (models.League.league_id == query)
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
    # Get user role from User_Entitlements
    user_row = db.execute(text(f"SELECT user_id FROM User_IAM WHERE username='{username}'")).fetchone()
    user_id = user_row[0] if user_row else None
    # Set role based on admin_role boolean
    role = "admin" if admin_role else "user"
    if user_id:
        ent_row = db.query(models.User_Entitlements).filter_by(user_id=user_id).first()
        if ent_row:
            role = ent_row.role
    return templates.TemplateResponse("home.html", {"request": request, "entries": entries, "picks": picks, "teams": teams, "games": games, "username": username, "role": role})


@app.get("/forgot-password", response_class=templates.TemplateResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request, "error": None})


@app.post("/forgot-password", response_class=templates.TemplateResponse)
async def forgot_password_post(request: Request, db: Session = Depends(get_db), email: str = Form(...)):
    import secrets
    # TODO: Implement email sending functionality
    # For now, just check if user exists and set a reset token
    user = db.execute(text(f"SELECT username FROM User_IAM WHERE email='{email}'")).fetchone()
    if user:
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        # Store token in database (you'd need to add a reset_token column)
        # For demo purposes, we'll just return success
        return templates.TemplateResponse("forgot_password.html", {"request": request, "success": "If an account with that email exists, a password reset link has been sent."})
    else:
        # Don't reveal if email exists or not for security
        return templates.TemplateResponse("forgot_password.html", {"request": request, "success": "If an account with that email exists, a password reset link has been sent."})


@app.get("/login", response_class=templates.TemplateResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("basic_login.html", {"request": request, "error": None})


@app.post("/login", response_class=templates.TemplateResponse)
async def login_post(request: Request, db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...)):
    # Input validation to prevent SQL injection
    import re
    import base64
    if not re.match(r'^[A-Za-z0-9_.-]{3,128}$', username):
        return templates.TemplateResponse("basic_login.html", {"request": request, "error": "Invalid username format."})
    if len(password) > 256:
        return templates.TemplateResponse("basic_login.html", {"request": request, "error": "Password too long."})
    user = db.execute(text(f"SELECT password, force_password_change, admin_role FROM User_IAM WHERE username='{username}'")).fetchone()
    if user:
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        if secrets.compare_digest(user[0], hashed_pw):
            # Generate session token
            session_token = secrets.token_urlsafe(32)
            
            # Update user with session token and last login time
            db.execute(
                text(f"UPDATE User_IAM SET session_token='{session_token}', last_logged_in_time=NOW() WHERE username='{username}'")
            )
            db.commit()
            
            # Create base64 encoded session cookie
            session_data = f"{username}:{session_token}"
            encoded_session = base64.b64encode(session_data.encode()).decode()
            
            if user[1]:
                # Redirect to password change page
                response = RedirectResponse(url=f"/change-password?username={username}", status_code=302)
                response.set_cookie(key="session-token", value=encoded_session, httponly=True, max_age=3600)
                return response
            
            response = RedirectResponse(url="/", status_code=302)
            response.set_cookie(key="session-token", value=encoded_session, httponly=True, max_age=3600)
            return response
    return templates.TemplateResponse("basic_login.html", {"request": request, "error": "Invalid username or password."})


@app.get("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    import base64
    session_cookie = request.cookies.get("session-token")
    if session_cookie:
        try:
            # Decode the session cookie to get username
            decoded_session = base64.b64decode(session_cookie).decode()
            username, session_token = decoded_session.split(':', 1)
            
            # Clear the session token in the database
            db.execute(
                text(f"UPDATE User_IAM SET session_token=NULL WHERE username='{username}'")
            )
            db.commit()
        except Exception:
            pass  # If decoding fails, just proceed with logout
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session-token")
    return response


@app.get("/reset-password", response_class=templates.TemplateResponse)
async def reset_password_page(request: Request, token: str = ""):
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "error": None})


@app.post("/reset-password", response_class=templates.TemplateResponse)
async def reset_password_post(request: Request, db: Session = Depends(get_db), username: str = Form(...), token: str = Form(...), new_password: str = Form(...)):
    import re
    # Validate password
    if len(new_password) < 8:
        return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "error": "Password must be at least 8 characters long."})
    elif not re.search(r"[0-9]", new_password):
        return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "error": "Password must contain at least one number."})
    elif not re.search(r"[A-Z]", new_password):
        return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "error": "Password must contain at least one uppercase letter."})
    
    # TODO: Validate reset token here
    # For now, just update the password
    try:
        hashed_pw = hashlib.sha256(new_password.encode()).hexdigest()
        db.execute(text(f"UPDATE User_IAM SET password='{hashed_pw}', force_password_change=0 WHERE username='{username}'"))
        db.commit()
        return templates.TemplateResponse("basic_login.html", {"request": request, "success": "Password reset successfully! You can now log in with your new password."})
    except Exception:
        return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "error": "An error occurred. Please try again."})


@app.get("/schedule/{week_num}")
async def get_week_schedule(week_num: int, db: Session = Depends(get_db)):
    games = db.query(models.Schedule).filter_by(week=week_num).all()
    teams = db.query(models.Teams).all()
    team_dict = {team.team_id: team for team in teams}
    result = []
    picked_teams = []
    
    for game in games:
        home_team = team_dict.get(game.home_team_id)
        away_team = team_dict.get(game.away_team_id)
        
        if home_team and away_team:
            result.append({
                "game_id": game.game_id,
                "home_team": {
                    "team_id": home_team.team_id,
                    "abbrv": home_team.abbrv,
                    "location": home_team.location,
                    "team_name": home_team.team_name
                },
                "away_team": {
                    "team_id": away_team.team_id,
                    "abbrv": away_team.abbrv,
                    "location": away_team.location,
                    "team_name": away_team.team_name
                },
                "game_time": game.game_time.isoformat() if game.game_time else None
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
    # Update the pick for the given pick_id and week_num
    pick = db.query(models.Picks).filter_by(pick_id=pick_id).first()
    if not pick:
        return JSONResponse(content={"error": "Pick not found"}, status_code=404)
    pick.team_id = team_obj.team_id
    db.commit()
    return JSONResponse(content={"success": True, "message": f"Pick updated for week {week_num}"})


if __name__ == "__main__":
    logger.info("starting server with dev configuration")
    uvicorn.run(app, host="127.0.0.1", port=9000)
