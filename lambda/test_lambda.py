#!/usr/bin/env python3
"""
Test script for NFL Game Updater Lambda function
Run this locally to test the function logic before deployment
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging for testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

def test_api_connection():
    """Test ESPN API connectivity"""
    print("=" * 50)
    print("Testing ESPN API Connection")
    print("=" * 50)
    
    try:
        from nfl_game_updater import test_api_connection
        result = test_api_connection()
        if result:
            print("✅ ESPN API connection successful")
        else:
            print("❌ ESPN API connection failed")
        return result
    except Exception as e:
        print(f"❌ Error testing API connection: {e}")
        return False

def test_week_calculation():
    """Test current week calculation"""
    print("=" * 50)
    print("Testing Week Calculation")
    print("=" * 50)
    
    try:
        from nfl_game_updater import get_current_nfl_week
        current_week = get_current_nfl_week()
        print(f"✅ Current NFL Week: {current_week}")
        return current_week
    except Exception as e:
        print(f"❌ Error calculating current week: {e}")
        return None

def test_game_results_fetch():
    """Test fetching game results from ESPN API"""
    print("=" * 50)
    print("Testing Game Results Fetch")
    print("=" * 50)
    
    try:
        from nfl_game_updater import fetch_nfl_game_results, get_current_nfl_week
        
        current_week = get_current_nfl_week()
        print(f"Fetching games for week {current_week}...")
        
        game_results = fetch_nfl_game_results(current_week)
        print(f"✅ Fetched {len(game_results)} games")
        
        # Display first few games
        for i, game in enumerate(game_results[:3]):
            print(f"Game {i+1}: {game['away_team_abbrv']} @ {game['home_team_abbrv']}")
            print(f"  Score: {game['away_score']} - {game['home_score']}")
            print(f"  Winner: {game['winning_team_abbrv']}")
            print(f"  Status: {game['status']}")
            print()
        
        return game_results
    except Exception as e:
        print(f"❌ Error fetching game results: {e}")
        return []

def test_database_connection():
    """Test database connection (requires environment variables)"""
    print("=" * 50)
    print("Testing Database Connection")
    print("=" * 50)
    
    # Check for required environment variables
    required_vars = ['MYSQL_HOST', 'MYSQL_PASSWORD', 'MYSQL_USER']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("Set these variables to test database connection:")
        for var in required_vars:
            print(f"  export {var}=your_value")
        return False
    
    try:
        from nfl_game_updater import get_database_engine
        from sqlalchemy.orm import sessionmaker
        
        engine = get_database_engine()
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Test connection with a simple query
        result = db.execute("SELECT 1").fetchone()
        db.close()
        
        if result:
            print("✅ Database connection successful")
            return True
        else:
            print("❌ Database query failed")
            return False
            
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_models_import():
    """Test importing database models"""
    print("=" * 50)
    print("Testing Models Import")
    print("=" * 50)
    
    try:
        from models import Team, Schedule, Pick, Entry
        print("✅ Models imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing models: {e}")
        return False

def run_dry_run():
    """Run a dry run of the Lambda function without database updates"""
    print("=" * 50)
    print("Running Dry Run (No Database Updates)")
    print("=" * 50)
    
    # Set up mock environment
    os.environ['DRY_RUN'] = 'true'
    
    try:
        from nfl_game_updater import lambda_handler
        
        # Create mock event and context
        event = {}
        context = type('Context', (), {
            'function_name': 'test-function',
            'function_version': '$LATEST',
            'invoked_function_arn': 'arn:aws:lambda:us-east-1:123456789012:function:test',
            'memory_limit_in_mb': '256',
            'remaining_time_in_millis': lambda: 30000
        })()
        
        # Run the function
        result = lambda_handler(event, context)
        
        print("✅ Dry run completed")
        print("Response:")
        print(json.dumps(result, indent=2))
        
        return result
        
    except Exception as e:
        print(f"❌ Dry run failed: {e}")
        return None

def main():
    """Run all tests"""
    print("NFL Game Updater Lambda - Test Suite")
    print("=" * 50)
    print(f"Test started at: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    results = {}
    
    # Run tests
    results['models_import'] = test_models_import()
    results['api_connection'] = test_api_connection()
    results['week_calculation'] = test_week_calculation()
    results['game_results_fetch'] = test_game_results_fetch()
    results['database_connection'] = test_database_connection()
    
    # Summary
    print("=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
        if result:
            passed += 1
    
    print()
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Ready for deployment.")
        
        # Offer to run dry run
        try:
            response = input("\nRun dry run of Lambda function? (y/N): ")
            if response.lower() in ['y', 'yes']:
                run_dry_run()
        except KeyboardInterrupt:
            print("\nTest suite interrupted by user.")
    else:
        print("❌ Some tests failed. Please fix issues before deployment.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
