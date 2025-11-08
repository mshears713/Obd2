#!/usr/bin/env python3
"""
SQLAlchemy Database Configuration
==================================

This file sets up the SQLite database connection and session management
for storing OBD-II readings permanently.

WHY SQLITE?
-----------
SQLite is perfect for this project because:
- No separate database server needed (it's just a file)
- Zero configuration required
- Fast enough for our car telemetry use case
- The entire database is a single file: readings.db

WHY check_same_thread=False?
-----------------------------
FastAPI can handle multiple requests at the same time. By default, SQLite
doesn't allow connections to be used across different threads (for safety).
Since FastAPI might use different threads for different requests, we need
to disable this check. This is safe because SQLAlchemy handles the thread
safety for us.

WHAT HAPPENS HERE:
------------------
1. Create an "engine" that connects to readings.db
2. Create a "SessionLocal" factory for making database sessions
3. Create a "Base" class that all our database models will inherit from
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database file will be created in the same directory as this script
DATABASE_URL = "sqlite:///./readings.db"

# Create the database engine
# connect_args is only needed for SQLite to work with FastAPI's threading
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# SessionLocal is a factory for creating database sessions
# Each session represents a "conversation" with the database
SessionLocal = sessionmaker(
    autocommit=False,  # We'll manually commit when we want to save changes
    autoflush=False,   # We'll manually flush when needed
    bind=engine        # Connect sessions to our database engine
)

# Base class that all our database models will inherit from
# This lets SQLAlchemy know which classes are database tables
Base = declarative_base()
