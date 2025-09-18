#!/usr/bin/env python3
"""
Script to fix duplicate foreign key constraints in the Schedule table
"""

import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_connection():
    """Get database connection using environment variables"""
    # Use DATABASE_URL from environment (Secrets Manager) if available
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if DATABASE_URL:
        # Parse the DATABASE_URL
        # Format: mysql+mysqlconnector://user:password@host:port/database
        import re
        match = re.match(r'mysql\+mysqlconnector://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
        if match:
            user, password, host, port, database = match.groups()
            return mysql.connector.connect(
                host=host,
                port=int(port),
                user=user,
                password=password,
                database=database
            )
    
    # Fallback to individual environment variables
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "ccmdecoder")
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
    MYSQL_DB = os.getenv("MYSQL_DB", "rmp")
    
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )

def fix_duplicate_constraints():
    """Fix duplicate foreign key constraints in the Schedule table"""
    
    try:
        connection = get_database_connection()
        cursor = connection.cursor()
        
        print("Checking for duplicate constraints in schedule table...")
        
        # Check if schedule table exists
        cursor.execute("SHOW TABLES LIKE 'schedule'")
        if not cursor.fetchone():
            print("Schedule table does not exist. Nothing to fix.")
            return True
            
        # Check existing foreign key constraints
        cursor.execute("""
            SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE 
            WHERE TABLE_NAME = 'schedule' 
            AND CONSTRAINT_SCHEMA = DATABASE()
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """)
        
        constraints = cursor.fetchall()
        print(f"Found {len(constraints)} foreign key constraints:")
        for constraint in constraints:
            print(f"  - {constraint[0]}: {constraint[1]} -> {constraint[2]}.{constraint[3]}")
        
        # Check for duplicate Schedule_ibfk_1 constraints
        duplicate_constraints = [c for c in constraints if c[0].lower() in ['schedule_ibfk_1', 'Schedule_ibfk_1']]
        
        if len(duplicate_constraints) > 1:
            print(f"Found {len(duplicate_constraints)} duplicate constraints with name pattern 'Schedule_ibfk_1'")
            
            # Drop all constraints with this pattern first
            for constraint in duplicate_constraints:
                try:
                    print(f"Dropping constraint: {constraint[0]}")
                    cursor.execute(f"ALTER TABLE schedule DROP FOREIGN KEY {constraint[0]}")
                    connection.commit()
                except mysql.connector.Error as e:
                    print(f"Warning: Could not drop constraint {constraint[0]}: {e}")
                    continue
            
            # Re-add the constraints with unique names
            print("Re-adding foreign key constraints with proper names...")
            
            try:
                # Add home_team_id constraint
                cursor.execute("""
                    ALTER TABLE schedule 
                    ADD CONSTRAINT fk_schedule_home_team 
                    FOREIGN KEY (home_team_id) REFERENCES teams(id)
                """)
                print("Added constraint: fk_schedule_home_team")
                
                # Add away_team_id constraint  
                cursor.execute("""
                    ALTER TABLE schedule 
                    ADD CONSTRAINT fk_schedule_away_team 
                    FOREIGN KEY (away_team_id) REFERENCES teams(id)
                """)
                print("Added constraint: fk_schedule_away_team")
                
                connection.commit()
                print("Successfully fixed duplicate constraints!")
                
            except mysql.connector.Error as e:
                print(f"Error adding new constraints: {e}")
                return False
        else:
            print("No duplicate constraints found.")
        
        return True
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("Database connection closed.")

if __name__ == "__main__":
    success = fix_duplicate_constraints()
    if success:
        print("\nConstraint fix completed successfully!")
    else:
        print("\nConstraint fix failed!")
        exit(1)
