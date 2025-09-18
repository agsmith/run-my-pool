import json
import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import boto3
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
import requests
import mysql.connector

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_current_nfl_week() -> int:
    """Calculate current NFL week based on date"""
    now = datetime.now(timezone.utc)
    current_year = now.year
    
    # NFL Week 1 typically starts around September 7-14
    # For 2025, let's assume Week 1 starts September 7, 2025
    week1_start = datetime(current_year, 9, 7, tzinfo=timezone.utc)
    
    if now < week1_start:
        return 1
    
    days_since_week1_end = (now - week1_start).days
    week = (days_since_week1_end // 7) + 1
    
    # Cap at Week 18
    return min(week, 18)

def is_nfl_game_time() -> bool:
    """
    Check if current time is during typical NFL game hours
    Returns True if it's likely that NFL games are being played
    """
    now = datetime.now(timezone.utc)
    
    # Convert to ET for easier comparison
    # UTC is 4-5 hours ahead of ET depending on DST
    # For simplicity, assume 5 hours (EST) during NFL season
    et_hour = (now.hour - 5) % 24
    et_weekday = now.weekday()  # 0=Monday, 6=Sunday
    
    # Check if we're in NFL season (September through February)
    if now.month not in [9, 10, 11, 12, 1, 2]:
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
    
    # Saturday (weekday 5): 1:00 PM - 11:30 PM ET (late season games)
    # Only during weeks 15-18 and playoffs
    current_week = get_current_nfl_week()
    if et_weekday == 5 and 13 <= et_hour <= 23 and current_week >= 15:
        return True
    
    return False

def lambda_handler(event, context):
    """
    AWS Lambda function to check NFL game results and update database
    
    This function:
    1. Fetches current NFL game results from ESPN API
    2. Updates game results in the schedule table
    3. Updates picks with win/loss status
    4. Eliminates entries based on losing picks
    5. Logs all actions for audit trail
    """
    try:
        logger.info("Starting NFL game results update process")
        
        # # Check if it's actually game time
        # if not is_nfl_game_time():
        #     logger.info("Not during NFL game time, skipping update")
        #     return {
        #         'statusCode': 200,
        #         'body': json.dumps({
        #             'message': 'Skipped - not during NFL game time',
        #             'timestamp': datetime.now(timezone.utc).isoformat()
        #         })
        #     }
        
        # Get database connection
        engine = get_database_engine()
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            # Get current week
            current_week = get_current_nfl_week()
            logger.info(f"Processing games for week {current_week}")
            
            # Fetch game results from ESPN API
            game_results = fetch_nfl_game_results(current_week)
            logger.info(f"Fetched {len(game_results)} game results")
            
            # Update database with results
            updates_made = update_game_results(db, game_results)
            
            # Update picks based on game results
            picks_updated = update_picks_results(db, game_results)
            
            # Update entry status (eliminate losing entries)
            entries_eliminated = eliminate_losing_entries(db)
            
            # Commit all changes
            db.commit()
            
            response = {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Successfully updated NFL game results',
                    'week': current_week,
                    'games_updated': updates_made,
                    'picks_updated': picks_updated,
                    'entries_eliminated': entries_eliminated,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            }
            
            logger.info(f"Process completed successfully: {response['body']}")
            return response
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error processing NFL game results: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        }

def get_database_engine():
    """Create database engine from environment variables or Secrets Manager"""
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        return create_engine(database_url, pool_pre_ping=True)
    
    # Fallback to individual environment variables
    mysql_user = os.getenv("MYSQL_USER", "root")
    mysql_password = os.getenv("MYSQL_PASSWORD")
    mysql_host = os.getenv("MYSQL_HOST")
    mysql_port = os.getenv("MYSQL_PORT", "3306")
    mysql_db = os.getenv("MYSQL_DB", "rmp")
    
    if not all([mysql_password, mysql_host]):
        # Try to get from AWS Secrets Manager
        secrets_manager = boto3.client('secretsmanager', 
                                        config=boto3.session.Config(
                                            connect_timeout=10,
                                            read_timeout=10
                                        ))
        secret_name = os.getenv('DB_SECRET_NAME', 'arn:aws:secretsmanager:us-east-1:739444271939:secret:runmypool/database-url-nRqy5o')
        
        try:
            response = secrets_manager.get_secret_value(SecretId=secret_name)
            database_url = json.loads(response['SecretString'])
        except Exception as e:
            logger.error(f"Failed to retrieve database credentials from Secrets Manager: {e}")
            raise
    
    return create_engine(database_url, pool_pre_ping=True)

def get_current_nfl_week() -> int:
    """Calculate current NFL week based on date"""
    now = datetime.now(timezone.utc)
    current_year = now.year
    
    # NFL Week 1 typically starts around September 7-14
    # For 2025, let's assume Week 1 starts September 7, 2025
    week1_start = datetime(current_year, 9, 7, tzinfo=timezone.utc)
    
    if now < week1_start:
        return 1
    
    days_since_week1 = (now - week1_start).days
    week = (days_since_week1 // 7) + 1
    
    # Cap at Week 18
    return min(week, 18)

def fetch_nfl_game_results(week: int) -> List[Dict]:
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
            'week': week,
            'seasontype': 2,  # Regular season
            'year': datetime.now().year
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        game_results = []
        
        for event in data.get('events', []):
            # Only process completed games
            if event['status']['type']['name'] not in ['STATUS_FINAL', 'STATUS_IN_PROGRESS']:
                continue
                
            competition = event['competitions'][0]
            
            # Extract team information
            home_team = None
            away_team = None
            home_score = 0
            away_score = 0
            
            for competitor in competition['competitors']:
                team_abbrv = competitor['team']['abbreviation']
                score = int(competitor.get('score', 0))
                
                if competitor['homeAway'] == 'home':
                    home_team = team_abbrv
                    home_score = score
                else:
                    away_team = team_abbrv
                    away_score = score
            
            # Determine winner
            winning_team = home_team if home_score > away_score else away_team
            game_status = event['status']['type']['name']
            
            game_result = {
                'home_team_abbrv': home_team,
                'away_team_abbrv': away_team,
                'home_score': home_score,
                'away_score': away_score,
                'winning_team_abbrv': winning_team,
                'status': game_status,
                'week': week,
                'game_date': event.get('date')
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
    from models import Schedule, Team
    
    updates_made = 0
    
    for game in game_results:
        try:
            # Find the game in our schedule table
            home_team = db.query(Team).filter(Team.abbrv == game['home_team_abbrv']).first()
            away_team = db.query(Team).filter(Team.abbrv == game['away_team_abbrv']).first()
            
            if not home_team or not away_team:
                logger.warning(f"Team not found for game: {game['home_team_abbrv']} vs {game['away_team_abbrv']}")
                continue
            
            # Find the scheduled game
            scheduled_game = db.query(Schedule).filter(
                and_(
                    Schedule.home_team_id == home_team.id,
                    Schedule.away_team_id == away_team.id,
                    Schedule.week_num == game['week']
                )
            ).first()
            
            if not scheduled_game:
                logger.warning(f"Scheduled game not found: {game['home_team_abbrv']} vs {game['away_team_abbrv']}, Week {game['week']}")
                continue
            
            # Update winning team
            winning_team = db.query(Team).filter(Team.abbrv == game['winning_team_abbrv']).first()
            if winning_team:
                scheduled_game.winning_team_id = str(winning_team.id)
                updates_made += 1
                logger.info(f"Updated game result: {game['away_team_abbrv']} @ {game['home_team_abbrv']}, Winner: {game['winning_team_abbrv']}")
            
        except Exception as e:
            logger.error(f"Error updating game result for {game}: {e}")
            continue
    
    return updates_made

def update_picks_results(db, game_results: List[Dict]) -> int:
    """Update picks with win/loss results based on game outcomes"""
    from models import Pick, Team
    
    picks_updated = 0
    
    # Create a mapping of team abbreviations to winning status
    team_results = {}
    for game in game_results:
        if game['status'] == 'STATUS_FINAL':
            # Mark winner as 'win' and loser as 'loss'
            team_results[game['winning_team_abbrv']] = 'win'
            loser = game['home_team_abbrv'] if game['winning_team_abbrv'] != game['home_team_abbrv'] else game['away_team_abbrv']
            team_results[loser] = 'loss'
    
    # Update picks based on results
    for team_abbrv, result in team_results.items():
        try:
            # Find the team
            team = db.query(Team).filter(Team.abbrv == team_abbrv).first()
            if not team:
                continue
            
            # Find all picks for this team that don't have results yet
            picks = db.query(Pick).filter(
                and_(
                    Pick.team_id == team.id,
                    Pick.result.in_(['pending', None])
                )
            ).all()
            
            for pick in picks:
                pick.result = result
                picks_updated += 1
                logger.info(f"Updated pick result: Entry {pick.entry_id}, Week {pick.week}, Team {team_abbrv}, Result: {result}")
                
        except Exception as e:
            logger.error(f"Error updating picks for team {team_abbrv}: {e}")
            continue
    
    return picks_updated

def eliminate_losing_entries(db) -> int:
    """Mark entries as eliminated if they have any losing picks"""
    from models import Entry, Pick
    
    entries_eliminated = 0
    
    try:
        # Find all active entries that have losing picks
        losing_entries = db.query(Entry).join(Pick).filter(
            and_(
                Entry.alive == True,
                Pick.result == 'loss'
            )
        ).distinct().all()
        
        for entry in losing_entries:
            entry.alive = False
            entries_eliminated += 1
            
            # Log the elimination for audit trail
            losing_picks = db.query(Pick).filter(
                and_(
                    Pick.entry_id == entry.id,
                    Pick.result == 'loss'
                )
            ).all()
            
            losing_teams = [pick.team_obj.abbrv for pick in losing_picks if pick.team_obj]
            logger.info(f"Eliminated entry {entry.id} (User: {entry.user_id}) due to losing pick(s): {', '.join(losing_teams)}")
        
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
            created_at=datetime.now(timezone.utc)
        )
        db.add(audit_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")

# Additional helper functions for testing and manual operations

def test_api_connection():
    """Test function to verify API connectivity"""
    try:
        response = requests.get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard", timeout=10)
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
            logger.info(f"Manually updated game {game_id} winner to team {winning_team_id}")
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

# if __name__ == "__main__":
#     # For local testing
#     test_event = {}
#     test_context = {}
#     result = lambda_handler(test_event, test_context)
#     print(json.dumps(result, indent=2))