import json
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo
import boto3
from sqlalchemy import create_engine, and_, func, or_
from sqlalchemy.orm import sessionmaker
import requests
import mysql.connector

# Import models at the top level
from models import Base, Schedule, Team, Pick, Entry, Pool

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# SSM parameter that stores the date when all games for the week were finalised.
# Format: "YYYY-MM-DD"  (ET date)
SSM_GAMES_DONE_PARAM = os.environ.get(
    "SSM_GAMES_DONE_PARAM", "/runmypool/nfl-games-done-date"
)

ssm_client = boto3.client("ssm", region_name="us-east-1")
EASTERN = ZoneInfo("America/New_York")


def get_et_date_str() -> str:
    """Return today's date as YYYY-MM-DD in US Eastern Time."""
    return datetime.now(timezone.utc).astimezone(EASTERN).date().isoformat()


def all_games_final_for_week(db, week: int) -> bool:
    """
    Return True if every game scheduled for the current week has a determined
    winner (winning_team_id is neither null nor the unresolved sentinel 99).
    Returns False if any game is still unresolved or in-progress.
    """
    unresolved = (
        db.query(Schedule)
        .filter(
            and_(
                Schedule.week_num == week,
                or_(Schedule.winning_team_id == 99, Schedule.winning_team_id.is_(None)),
            )
        )
        .count()
    )
    logger.info(f"Week {week}: {unresolved} game(s) still unresolved in DB")
    return unresolved == 0


def is_done_for_today() -> bool:
    """
    Check SSM to see if we already recorded all games final for today's ET date.
    Returns True (skip processing) if the flag matches today's date.
    """
    today = get_et_date_str()
    try:
        resp = ssm_client.get_parameter(Name=SSM_GAMES_DONE_PARAM)
        stored = resp["Parameter"]["Value"]
        if stored == today:
            logger.info(f"All games already final for {today} — skipping")
            return True
    except ssm_client.exceptions.ParameterNotFound:
        pass
    except Exception as e:
        logger.warning(f"Could not read SSM param {SSM_GAMES_DONE_PARAM}: {e}")
    return False


def mark_done_for_today() -> None:
    """Write today's ET date to SSM to signal all games are final."""
    today = get_et_date_str()
    try:
        ssm_client.put_parameter(
            Name=SSM_GAMES_DONE_PARAM,
            Value=today,
            Type="String",
            Overwrite=True,
        )
        logger.info(f"Marked all games final for {today} in SSM")
    except Exception as e:
        logger.warning(f"Could not write SSM param {SSM_GAMES_DONE_PARAM}: {e}")


def get_current_nfl_context(db, now=None):
    """Resolve the active season/week from the stored schedule."""
    current = now or datetime.now(timezone.utc)
    current_naive = current.astimezone(timezone.utc).replace(tzinfo=None)
    nearby_games = (
        db.query(Schedule)
        .filter(
            Schedule.start_time >= current_naive - timedelta(days=4),
            Schedule.start_time <= current_naive + timedelta(days=4),
        )
        .all()
    )
    if not nearby_games:
        raise RuntimeError("No scheduled NFL games found near the current date")
    nearest = min(
        nearby_games,
        key=lambda game: abs((game.start_time - current_naive).total_seconds()),
    )
    season = nearest.start_time.year - (1 if nearest.start_time.month <= 2 else 0)
    return season, nearest.week_num


def get_current_nfl_week(db, now=None) -> int:
    """Resolve the active week from the stored schedule rather than a guessed date."""
    return get_current_nfl_context(db, now)[1]


def is_nfl_game_time(now=None, current_week=None) -> bool:
    """
    Check if current time is during typical NFL game hours
    Returns True if it's likely that NFL games are being played
    """
    now_utc = now or datetime.now(timezone.utc)
    local_now = now_utc.astimezone(EASTERN)
    et_hour = local_now.hour
    et_weekday = local_now.weekday()  # 0=Monday, 6=Sunday

    # Check if we're in NFL season (September through February)
    if local_now.month not in [9, 10, 11, 12, 1, 2]:
        return False

    # Sunday (weekday 6): 1:00 PM - 11:30 PM ET
    if et_weekday == 6 and 13 <= et_hour <= 23:
        return True

    # Monday (weekday 0): 8:00 PM - 11:30 PM ET (Monday Night Football)
    if et_weekday == 0 and 20 <= et_hour <= 23:
        return True

    # Thursday (weekday 3): 8:00 PM - 11:30 PM ET (Thursday Night Football)
    if et_weekday == 3 and 20 <= et_hour <= 23:
        return True

    # Continue polling shortly after midnight for games that ran late.
    if et_hour <= 1 and et_weekday in {0, 1, 4}:
        return True

    # Saturday games are normally late-season only. Scheduler may invoke on
    # earlier Saturdays, but the application gate keeps those runs inexpensive.
    if et_weekday == 5 and 13 <= et_hour <= 23 and (current_week or 0) >= 15:
        return True
    if et_weekday == 6 and et_hour <= 1 and (current_week or 0) >= 15:
        return True

    return False


def lambda_handler(event, context):
    """
    AWS Lambda function to check NFL game results and update database

    This function:
    1. Skips if not during NFL game hours
    2. Skips if SSM flag says all games are already final for today
    3. Fetches current NFL game results from ESPN API
    4. Updates game results in the schedule table
    5. Updates picks with win/loss status
    6. Eliminates entries based on losing picks
    7. If all games for the week are now final, sets SSM flag to stop
       further invocations until the next game day
    """
    try:
        event = event or {}
        logger.info("Starting NFL game results update process")

        # Check SSM flag — skip if all games were already marked final today
        if not event.get("force") and is_done_for_today():
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "Skipped - all games already final for today",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ),
            }

        # Get database connection
        engine = get_database_engine()
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        try:
            # Get current week
            season, current_week = get_current_nfl_context(db)
            logger.info(f"Processing {season} season, week {current_week}")

            if not event.get("force") and not is_nfl_game_time(current_week=current_week):
                logger.info("Not during NFL game time, skipping update")
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": "Skipped - not during NFL game time",
                        "week": current_week,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }),
                }

            # Fetch game results from ESPN API
            game_results = fetch_nfl_game_results(current_week, season)
            logger.info(
                f"Fetched {len(game_results)} game results for week {current_week}"
            )

            # Update database with results
            updates_made = update_game_results(db, game_results)

            # Update picks based on game results
            picks_updated = update_picks_results(db, game_results)

            # Reconcile Survivor elimination, including official corrections.
            entries_reconciled = reconcile_survivor_entries(db)

            # Commit all changes
            db.commit()

            # Check if all games for this week are now final — if so, set the
            # SSM flag so we skip all remaining invocations today
            games_done = all_games_final_for_week(db, current_week)
            if games_done:
                mark_done_for_today()

            response = {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "Successfully updated NFL game results",
                        "week": current_week,
                        "games_updated": updates_made,
                        "picks_updated": picks_updated,
                        "entries_reconciled": entries_reconciled,
                        "all_games_final": games_done,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ),
            }

            logger.info(f"Process completed successfully: {response['body']}")
            return response

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    except Exception as e:
        # Raising is intentional: EventBridge Scheduler can only retry and send
        # the invocation to its DLQ when Lambda reports a failed invocation.
        logger.exception("Error processing NFL game results")
        raise


def get_database_engine():
    """Get database engine with proper configuration"""
    secrets_manager = boto3.client(
        "secretsmanager",
        config=boto3.session.Config(connect_timeout=10, read_timeout=10),
        endpoint_url="https://secretsmanager.us-east-1.amazonaws.com",
    )

    secret_name = os.environ["SECRETS_MANAGER_ARN"]

    try:
        response = secrets_manager.get_secret_value(SecretId=secret_name)
        database_url = response["SecretString"]

        # Create engine with proper configuration
        engine = create_engine(
            database_url, pool_pre_ping=True, pool_recycle=3600, echo=False
        )

        # Bind metadata to engine
        Base.metadata.bind = engine

        return engine
    except Exception as e:
        logger.error(
            f"Failed to retrieve database credentials from Secrets Manager: {e}"
        )
        raise


def fetch_nfl_game_results(week: int, season: Optional[int] = None) -> List[Dict]:
    """
    Fetch NFL game results from ESPN API
    Returns list of game results with team IDs and scores
    """
    try:
        # ESPN API endpoint for NFL scoreboard
        # This is a free API that provides real-time NFL scores
        url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

        # You can also specify week and season if needed
        params = {
            "week": week,
            "seasontype": 2,  # Regular season
            "year": season or datetime.now(timezone.utc).astimezone(EASTERN).year,
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        game_results = []

        for event in data.get("events", []):
            # Only process completed games
            if event["status"]["type"]["name"] not in [
                "STATUS_FINAL",
                "STATUS_IN_PROGRESS",
            ]:
                continue

            competition = event["competitions"][0]

            # Extract team information
            home_team = None
            away_team = None
            home_score = 0
            away_score = 0

            for competitor in competition["competitors"]:
                team_abbrv = competitor["team"]["abbreviation"]
                score = int(competitor.get("score", 0))

                if competitor["homeAway"] == "home":
                    home_team = team_abbrv
                    home_score = score
                else:
                    away_team = team_abbrv
                    away_score = score

            # Determine winner
            winning_team = home_team if home_score > away_score else away_team
            game_status = event["status"]["type"]["name"]

            game_result = {
                "home_team_abbrv": home_team,
                "away_team_abbrv": away_team,
                "home_score": home_score,
                "away_score": away_score,
                "winning_team_abbrv": winning_team,
                "status": game_status,
                "week": week,
                "game_date": event.get("date"),
            }

            game_results.append(game_result)

        return game_results

    except requests.RequestException as e:
        logger.error(f"Failed to fetch game results from ESPN API: {e}")
        raise
    except Exception as e:
        logger.error(f"Error processing game results: {e}")
        raise


def update_game_results(db, game_results: List[Dict]) -> int:
    """Update schedule table with game results"""
    updates_made = 0

    for game in game_results:
        if game["status"] == "STATUS_FINAL":
            try:
                # Find the game in our schedule table
                home_team = (
                    db.query(Team)
                    .filter(
                        func.lower(Team.abbrv) == func.lower(game["home_team_abbrv"])
                    )
                    .first()
                )
                away_team = (
                    db.query(Team)
                    .filter(
                        func.lower(Team.abbrv) == func.lower(game["away_team_abbrv"])
                    )
                    .first()
                )
                print(home_team)
                if not home_team or not away_team:
                    logger.warning(
                        f"Team not found for game: {game['home_team_abbrv']} vs {game['away_team_abbrv']}"
                    )
                    continue

                # Find the scheduled game
                scheduled_game = (
                    db.query(Schedule)
                    .filter(
                        and_(
                            Schedule.home_team_id == home_team.id,
                            Schedule.away_team_id == away_team.id,
                            Schedule.week_num == game["week"],
                        )
                    )
                    .first()
                )

                if not scheduled_game:
                    logger.warning(
                        f"Scheduled game not found: {game['home_team_abbrv']} vs {game['away_team_abbrv']}, Week {game['week']}"
                    )
                    continue

                # Update winning team
                if game["winning_team_abbrv"].lower() == home_team.abbrv.lower():
                    scheduled_game.winning_team_id = home_team.id
                    updates_made += 1
                else:
                    scheduled_game.winning_team_id = away_team.id
                    updates_made += 1

            except Exception as e:
                logger.error(f"Error updating game result for {game}: {e}")
                continue

    return updates_made


def update_picks_results(db, game_results: List[Dict]) -> int:
    """Reconcile Survivor and Pick 'Em picks with final game outcomes."""
    picks_updated = 0

    # Get the week from game results (they should all be the same week)
    current_week = game_results[0]["week"] if game_results else None
    if not current_week:
        logger.warning("No game results provided for pick updates")
        return 0

    logger.info(
        f"Updating picks for week {current_week} based on {len(game_results)} completed games"
    )

    # Create a mapping of team abbreviations to winning status
    team_results = {}
    for game in game_results:
        if game["status"] == "STATUS_FINAL":
            # Mark winner as 'win' and loser as 'loss'
            winning_team = game["winning_team_abbrv"].lower()
            team_results[winning_team] = "win"

            # Determine the losing team
            home_team = game["home_team_abbrv"].lower()
            away_team = game["away_team_abbrv"].lower()
            loser = home_team if winning_team != home_team else away_team
            team_results[loser] = "loss"

            logger.info(f"Game result: {winning_team} beat {loser}")

    logger.info(f"Processing results for {len(team_results)} teams")

    # Update picks based on results
    for team_abbrv, result in team_results.items():
        try:
            # Find the team (case-insensitive match)
            team = (
                db.query(Team)
                .filter(func.lower(Team.abbrv) == team_abbrv.lower())
                .first()
            )
            if not team:
                logger.warning(f"Team not found in database: {team_abbrv}")
                continue

            # Include previously resolved picks so official scoring corrections
            # propagate to both Survivor and Pick 'Em pools.
            picks = (
                db.query(Pick)
                .filter(
                    and_(
                        func.lower(Pick.team) == team.abbrv.lower(),
                        Pick.week == current_week,
                    )
                )
                .all()
            )

            logger.info(
                f"Found {len(picks)} pending picks for {team_abbrv} in week {current_week}"
            )

            for pick in picks:
                if pick.result == result:
                    continue
                old_result = pick.result
                pick.result = result
                picks_updated += 1
                logger.info(
                    f"Updated pick: Entry {pick.entry_id}, Week {pick.week}, Team {team_abbrv}, {old_result} → {result}"
                )

        except Exception as e:
            logger.error(f"Error updating picks for team {team_abbrv}: {e}")
            continue

    logger.info(f"Total picks updated: {picks_updated}")
    return picks_updated


def reconcile_survivor_entries(db) -> int:
    """Make Survivor entry status agree with its complete resolved pick history.

    This handles both ordinary elimination and an official score correction that
    changes an entry's only loss back to a win. Pick 'Em entries are never
    eliminated.
    """
    changed = 0
    survivor_entries = (
        db.query(Entry)
        .join(Pool, Pool.id == Entry.pool_id)
        .filter(Pool.pool_type == "survivor")
        .all()
    )
    for entry in survivor_entries:
        has_loss = db.query(Pick.id).filter(
            Pick.entry_id == entry.id,
            Pick.result == "loss",
        ).first() is not None
        should_be_alive = not has_loss
        if entry.alive != should_be_alive:
            logger.info(
                "Reconciled Survivor entry %s alive status: %s -> %s",
                entry.id,
                entry.alive,
                should_be_alive,
            )
            entry.alive = should_be_alive
            changed += 1
    return changed


def eliminate_losing_entries(db) -> int:
    """Mark entries as eliminated if they have any losing picks"""
    entries_eliminated = 0

    try:
        # Find all active entries that have losing picks
        losing_entries = (
            db.query(Entry)
            .join(Pick)
            .join(Pool, Pool.id == Entry.pool_id)
            .filter(and_(
                Entry.alive == True,
                Pick.result == "loss",
                Pool.pool_type == "survivor",
            ))
            .distinct()
            .all()
        )

        for entry in losing_entries:
            entry.alive = False
            entries_eliminated += 1

            # Log the elimination for audit trail
            losing_picks = (
                db.query(Pick)
                .filter(and_(Pick.entry_id == entry.id, Pick.result == "loss"))
                .all()
            )

            losing_teams = [
                pick.team_obj.abbrv for pick in losing_picks if pick.team_obj
            ]
            logger.info(
                f"Eliminated entry {entry.id} (User: {entry.user_id}) due to losing pick(s): {', '.join(losing_teams)}"
            )

        return entries_eliminated

    except Exception as e:
        logger.error(f"Error eliminating losing entries: {e}")
        return 0


def create_audit_log(db, action: str, details: str, user_id: str = None):
    """Create an audit log entry"""
    from models import AuditLog
    import uuid

    try:
        audit_entry = AuditLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            action=action,
            details=details,
            created_at=datetime.now(timezone.utc),
        )
        db.add(audit_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")


# Additional helper functions for testing and manual operations


def test_api_connection():
    """Test function to verify API connectivity"""
    try:
        response = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"API connection test failed: {e}")
        return False


def manual_game_result_update(game_id: int, winning_team_id: int):
    """Manual function to update a specific game result (for corrections)"""
    engine = get_database_engine()
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        from models import Schedule

        game = db.query(Schedule).filter(Schedule.game_id == game_id).first()
        if game:
            game.winning_team_id = str(winning_team_id)
            db.commit()
            logger.info(
                f"Manually updated game {game_id} winner to team {winning_team_id}"
            )
            return True
        else:
            logger.error(f"Game {game_id} not found")
            return False

    except Exception as e:
        logger.error(f"Error manually updating game {game_id}: {e}")
        db.rollback()
        return False
    finally:
        db.close()
