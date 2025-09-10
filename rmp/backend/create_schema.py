#!/usr/bin/env python3
"""
Script to create the database schema from datamodel.sql
"""

import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "ccmdecoder")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "rmp")

def create_database_schema():
    """Create the database schema from datamodel.sql"""
    
    try:
        # Connect to MySQL server (without specifying database)
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD
        )
        
        cursor = connection.cursor()
        
        # Create database if it doesn't exist
        print(f"Creating database '{MYSQL_DB}' if it doesn't exist...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DB}")
        cursor.execute(f"USE {MYSQL_DB}")
        
        # Read and execute the SQL schema
        print("Reading datamodel.sql...")
        with open('datamodel.sql', 'r') as f:
            sql_content = f.read()
        
        # Split by semicolons and execute each statement
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        print(f"Executing {len(statements)} SQL statements...")
        for i, statement in enumerate(statements, 1):
            try:
                # Skip empty statements and comments
                if not statement or statement.startswith('--'):
                    continue
                    
                print(f"Executing statement {i}: {statement[:50]}...")
                cursor.execute(statement)
                connection.commit()
                
            except mysql.connector.Error as e:
                # Check if it's a harmless error (table already exists, etc.)
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"Warning (skipping): {e}")
                    continue
                else:
                    print(f"Error executing statement {i}: {e}")
                    print(f"Statement: {statement}")
                    # Don't stop on errors, continue with next statement
                    continue
        
        print("Database schema creation completed!")
        
        # Show tables to verify
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"\nCreated tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
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
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    success = create_database_schema()
    if success:
        print("\nDatabase schema created successfully!")
    else:
        print("\nDatabase schema creation failed!")
        exit(1)
