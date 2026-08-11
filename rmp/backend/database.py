from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Use DATABASE_URL from environment (Secrets Manager) if available, otherwise fallback to individual variables for local dev
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    required = ("MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_HOST", "MYSQL_DB")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Set DATABASE_URL or all required MYSQL_* connection variables"
        )
    MYSQL_USER = os.environ["MYSQL_USER"]
    MYSQL_PASSWORD = os.environ["MYSQL_PASSWORD"]
    MYSQL_HOST = os.environ["MYSQL_HOST"]
    MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
    MYSQL_DB = os.environ["MYSQL_DB"]
    DATABASE_URL = f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
