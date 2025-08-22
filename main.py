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


def get_current_user(request: Request):
    username = request.cookies.get("username")
    if not username:
        return None
    return username

db_depends = Annotated[Session, Depends(get_db)]




@app.get("/", response_class=templates.TemplateResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    username = get_current_user(request)
    if not username:
        return RedirectResponse(url="/login", status_code=302)
    entries = db.query(models.Entries).all()
    picks = db.query(models.Picks).all()
    teams = db.query(models.Teams).all()
    return templates.TemplateResponse("home.html", {"request": request, "entries": entries, "picks": picks, "teams": teams, "username": username})




@app.post("/edit-pick/{pick_id}", response_class=templates.TemplateResponse)
async def edit_pick(request: Request, pick_id: int, db: Session = Depends(get_db)):
    username = get_current_user(request)
    if not username:
        return RedirectResponse(url="/login", status_code=302)
    picks = db.query(models.Picks).all()
    return templates.TemplateResponse("weekly_picks.html", { "request": request, "picks": picks, "username": username })




@app.post("/addEntry", response_model=None)
async def add_entry(entry: EntryBase, db: Session = Depends(get_db), request: Request = None):
    username = get_current_user(request)
    if not username:
        return RedirectResponse(url="/login", status_code=302)
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


@app.delete("/delEntry/{entry_id}", response_model=None)
async def del_entry(entry_id: int, db: Session = Depends(get_db), request: Request = None):
    username = get_current_user(request)
    if not username:
        return RedirectResponse(url="/login", status_code=302)
    # Find entry and related picks
    entry = db.query(models.Entries).filter_by(entry_id=entry_id).first()
    if not entry:
        logger.warning(f"Entry not found: {entry_id}")
        return None
    picks = db.query(models.Picks).filter_by(entry_id=entry_id).all()
    for pick in picks:
        db.delete(pick)
    db.commit()
    db.delete(entry)
    db.commit()
    logger.info(f"Deleted entry: {entry_id}")
    return entry



@app.get("/login", response_class=templates.TemplateResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("basic_login.html", {"request": request, "error": None})


@app.post("/login", response_class=templates.TemplateResponse)
async def login_post(request: Request, db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...)):
    # Input validation to prevent SQL injection
    import re
    if not re.match(r'^[A-Za-z0-9_.-]{3,128}$', username):
        return templates.TemplateResponse("basic_login.html", {"request": request, "error": "Invalid username format."})
    if len(password) > 256:
        return templates.TemplateResponse("basic_login.html", {"request": request, "error": "Password too long."})
    user = db.execute(text(f"SELECT password, force_password_change, admin_role FROM User_IAM WHERE username='{username}'")).fetchone()
    if user:
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        if secrets.compare_digest(user[0], hashed_pw):
            if user[1]:
                # Redirect to password change page
                response = RedirectResponse(url=f"/change-password?username={username}", status_code=302)
                response.set_cookie(key="username", value=username, httponly=True, max_age=3600)
                return response
            # Update last_logged_in_time
            db.execute(
                text(f"UPDATE User_IAM SET last_logged_in_time=NOW() WHERE username='{username}'")
            )
            db.commit()
            response = RedirectResponse(url="/", status_code=302)
            response.set_cookie(key="username", value=username, httponly=True, max_age=3600)
            if user[2]:
                response.set_cookie(key="role", value="Admin", httponly=True, max_age=3600)
            else:
                response.set_cookie(key="role", value="User", httponly=True, max_age=3600)
            return response
    return templates.TemplateResponse("basic_login.html", {"request": request, "error": "Invalid username or password."})
# Password change API
@app.get("/change-password", response_class=templates.TemplateResponse)
async def change_password_form(request: Request, username: str):
    return templates.TemplateResponse("change_password.html", {"request": request, "username": username, "error": None})

@app.post("/change-password", response_class=templates.TemplateResponse)
async def change_password_post(request: Request, db: Session = Depends(get_db), username: str = Form(...), new_password: str = Form(...)):
    # Input validation to prevent SQL injection
    import re
    if not re.match(r'^[A-Za-z0-9_.-]{3,128}$', username):
        return templates.TemplateResponse("change_password.html", {"request": request, "username": username, "error": "Invalid username format."})
    if len(new_password) > 256:
        return templates.TemplateResponse("change_password.html", {"request": request, "username": username, "error": "Password too long."})
    # Password strength validation
    error = None
    if len(new_password) < 8:
        error = "Password must be at least 8 characters."
    elif not re.search(r"[A-Z]", new_password):
        error = "Password must contain at least one uppercase letter."
    elif not re.search(r"[a-z]", new_password):
        error = "Password must contain at least one lowercase letter."
    elif not re.search(r"[0-9]", new_password):
        error = "Password must contain at least one digit."
    elif not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\",.<>/?]", new_password):
        error = "Password must contain at least one special character."
    if error:
        return templates.TemplateResponse("change_password.html", {"request": request, "username": username, "error": error})
    hashed_pw = hashlib.sha256(new_password.encode()).hexdigest()
    db.execute(
        text(f"UPDATE User_IAM SET password='{hashed_pw}', force_password_change=FALSE WHERE username='{username}'")
    )
    db.commit()
    response = RedirectResponse(url="/login", status_code=302)
    return response

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("username")
    return response

# Create User API
@app.get("/create-user", response_class=templates.TemplateResponse)
async def create_user_form(request: Request):
    return templates.TemplateResponse("create_user.html", {"request": request, "error": None})

@app.post("/create-user", response_class=templates.TemplateResponse)
async def create_user_post(request: Request, db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...), email: str = Form(...)):
    # Input validation to prevent SQL injection
    import re
    if not re.match(r'^[A-Za-z0-9_.-]{3,128}$', username):
        return templates.TemplateResponse("create_user.html", {"request": request, "error": "Invalid username format."})
    if len(password) > 256:
        return templates.TemplateResponse("create_user.html", {"request": request, "error": "Password too long."})
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return templates.TemplateResponse("create_user.html", {"request": request, "error": "Invalid email address format."})
    # Check if user exists
    existing = db.execute(text(f"SELECT user_id FROM User_IAM WHERE username='{username}'")).fetchone()
    if existing:
        return templates.TemplateResponse("create_user.html", {"request": request, "error": "Username already exists."})
    # Hash password
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    db.execute(
        text(f"INSERT INTO User_IAM (username, password, email, account_created_time, force_password_change) VALUES ('{username}', '{hashed_pw}', '{email}', NOW(), FALSE)")
    )
    db.commit()
    return RedirectResponse(url="/login", status_code=302)

# Delete last entry API
@app.post("/delEntry/last", response_model=None)
async def del_last_entry(db: Session = Depends(get_db), request: Request = None):
    username = get_current_user(request)
    if not username:
        return RedirectResponse(url="/login", status_code=302)
    last_entry = db.query(models.Entries).order_by(models.Entries.entry_id.desc()).first()
    if not last_entry:
        logger.warning("No entries to delete.")
        return RedirectResponse(url="/", status_code=302)
    picks = db.query(models.Picks).filter_by(entry_id=last_entry.entry_id).all()
    for pick in picks:
        db.delete(pick)
    db.commit()
    db.delete(last_entry)
    db.commit()
    logger.info(f"Deleted last entry: {last_entry.entry_id}")
    return RedirectResponse(url="/", status_code=302)

@app.get("/forgot-password", response_class=templates.TemplateResponse)
async def forgot_password_form(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request, "error": None})

@app.post("/forgot-password", response_class=templates.TemplateResponse)
async def forgot_password_post(request: Request, db: Session = Depends(get_db), email: str = Form(...)):
    import re
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return templates.TemplateResponse("forgot_password.html", {"request": request, "error": "Invalid email address format."})
    user = db.execute(text(f"SELECT username FROM User_IAM WHERE email='{email}'")).fetchone()
    if not user:
        return templates.TemplateResponse("forgot_password.html", {"request": request, "error": "No user found with that email address."})
    # Generate a password reset token (simple example, use secure method in production)
    import secrets
    token = secrets.token_urlsafe(32)
    # Store token in DB or cache (not implemented here)
    # Send email to user with reset link
    reset_link = f"http://yourdomain.com/reset-password?token={token}&username={user[0]}"
    # TODO: Integrate with real email service
    print(f"Send email to {email} with link: {reset_link}")
    return templates.TemplateResponse("forgot_password.html", {"request": request, "error": None, "message": "A password reset link has been sent to your email address."})

@app.get("/reset-password", response_class=templates.TemplateResponse)
async def reset_password_form(request: Request, token: str, username: str):
    # Validate token (not implemented)
    return templates.TemplateResponse("reset_password.html", {"request": request, "username": username, "token": token, "error": None})

@app.post("/reset-password", response_class=templates.TemplateResponse)
async def reset_password_post(request: Request, db: Session = Depends(get_db), username: str = Form(...), token: str = Form(...), new_password: str = Form(...)):
    # Validate token (not implemented)
    # Password strength validation (reuse logic)
    import re
    error = None
    if len(new_password) < 8:
        error = "Password must be at least 8 characters."
    elif not re.search(r"[A-Z]", new_password):
        error = "Password must contain at least one uppercase letter."
    elif not re.search(r"[a-z]", new_password):
        error = "Password must contain at least one lowercase letter."
    elif not re.search(r"\d", new_password):
        error = "Password must contain at least one digit."
    elif not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\",.<>/?]", new_password):
        error = "Password must contain at least one special character."
    if error:
        return templates.TemplateResponse("reset_password.html", {"request": request, "username": username, "token": token, "error": error})
    hashed_pw = hashlib.sha256(new_password.encode()).hexdigest()
    db.execute(text(f"UPDATE User_IAM SET password='{hashed_pw}', force_password_change=FALSE WHERE username='{username}'"))
    db.commit()
    return RedirectResponse(url="/login", status_code=302)


# API endpoint to get schedule for a given week
@app.get("/api/schedule/{week_num}")
async def get_schedule(week_num: int, db: Session = Depends(get_db), pick_id: int = None):
    from fastapi import Request
    import urllib.parse
    # Get pick_id from query params if not passed as function arg
    import inspect
    frame = inspect.currentframe()
    request = None
    while frame:
        if 'request' in frame.f_locals:
            request = frame.f_locals['request']
            break
        frame = frame.f_back
    if request is None:
        import sys
        request = sys.modules.get('fastapi').Request
    # Try to get pick_id from query params
    if pick_id is None and request:
        try:
            pick_id = int(request.query_params.get('pick_id'))
        except:
            pick_id = None
    # Get all games for the week
    games = db.query(models.Schedule).filter_by(week_num=week_num).all()
    teams = {team.team_id: team for team in db.query(models.Teams).all()}
    result = []
    picked_teams = []
    if pick_id:
        pick = db.query(models.Picks).filter_by(pick_id=pick_id).first()
        if pick:
            entry_id = pick.entry_id
            entry_picks = db.query(models.Picks).filter_by(entry_id=entry_id).all()
            for ep in entry_picks:
                team = teams.get(ep.team_id)
                if team:
                    picked_teams.append(team.team_id)
    for game in games:
        home = teams.get(game.home_team)
        away = teams.get(game.away_team)
        est = pytz.timezone('US/Eastern')
        formatted_time = ""
        if game.start_time:
            dt_est = game.start_time.astimezone(est)
            formatted_time = dt_est.strftime('%a %b %d, %-I:%M %p')
        if home.team_id in picked_teams:
            home.logo = f"/static/img/{home.abbrv}_gray.gif".lower()
            home_selectable = False
        else:
            home_selectable = True
        if away.team_id in picked_teams:
            away.logo = f"/static/img/{away.abbrv}_gray.gif".lower()
            away_selectable = False
        else:
            away_selectable = True
        result.append({
            "home": home.name if home else "",
            "away": away.name if away else "",
            "homeAbbrv": home.abbrv if home else "",
            "awayAbbrv": away.abbrv if away else "",
            "homeLogo": home.logo if home else "",
            "awayLogo": away.logo if away else "",
            "homeSelectable": home_selectable,
            "awaySelectable": away_selectable,
            "game_time": formatted_time
        })
    return JSONResponse(content={"games": result, "pickedTeams": picked_teams})


@app.post("/submit-pick", response_class=JSONResponse)
async def submit_pick(request: Request, db: Session = Depends(get_db), pick_id: str = Form(...), week_num: str = Form(...), team: str = Form(...)):
    username = get_current_user(request)
    if not username:
        return JSONResponse(content={"error": "Not logged in"}, status_code=401)
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
    return JSONResponse(content={"success": True, "team_id": team_obj.team_id})


if __name__ == "__main__":
    logger.info("starting server with dev configuration")
    uvicorn.run(app, host="127.0.0.1", port=9000)