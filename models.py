#!/usr/bin/env python3
"""
SQLAlchemy ORM Models
=====================

This file defines the database table structure for storing OBD-II readings.

WHAT IS AN ORM MODEL?
---------------------
ORM = Object-Relational Mapping
It lets us work with database tables as if they were Python classes.
Instead of writing SQL, we can just work with Python objects.

THE ReadingModel CLASS:
-----------------------
This class mirrors our Pydantic models (ReadingIn/ReadingOut) but is used
for the DATABASE, not the API.

Each instance of ReadingModel = one row in the "readings" table
Each attribute (id, timestamp, rpm, etc.) = one column in the table

SQLAlchemy will automatically create the table the first time the app runs.

FIELD TYPES:
------------
- id: Auto-incrementing primary key (unique ID for each reading)
- timestamp: String (ISO8601 format from the OBD loop)
- rpm, speed_mph, coolant_temp_f, etc.: Match the Pydantic schema
- nullable=True: These fields can be None if the sensor fails
"""

from sqlalchemy import Column, Integer, Float, String
from database import Base


class ReadingModel(Base):
    """
    Database model for storing OBD-II sensor readings.

    Each row represents one reading from the car at a specific moment in time.
    """
    __tablename__ = "readings"

    # Primary key - auto-increments with each new reading
    id = Column(Integer, primary_key=True, index=True)

    # Timestamp of when the reading was taken (ISO8601 format)
    timestamp = Column(String, index=True)

    # Engine RPM (revolutions per minute)
    rpm = Column(Integer, nullable=True)

    # Vehicle speed in miles per hour
    speed_mph = Column(Float, nullable=True)

    # Engine coolant temperature in Fahrenheit
    coolant_temp_f = Column(Float, nullable=True)

    # Throttle position as a percentage (0-100)
    throttle_pct = Column(Float, nullable=True)

    # Calculated engine load as a percentage (0-100)
    load_pct = Column(Float, nullable=True)

    # Mass air flow in grams per second
    maf_gps = Column(Float, nullable=True)
