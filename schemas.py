#!/usr/bin/env python3
"""
Pydantic Models for OBD-II API
===============================

This file defines the data structures (schemas) for our API using Pydantic.

WHAT ARE PYDANTIC MODELS?
--------------------------
Pydantic models are Python classes that define the shape and types of data.
They automatically:
- Validate incoming data (reject bad types, missing fields, etc.)
- Convert data to the correct types when possible
- Generate clear error messages when validation fails
- Provide automatic documentation in FastAPI's /docs page

WHY SEPARATE INPUT vs OUTPUT MODELS?
-------------------------------------
Even though ReadingIn and ReadingOut look identical now, separating them gives us
flexibility for the future. For example:
- ReadingOut might later include an "id" field from the database
- ReadingIn might require certain fields while ReadingOut makes them optional
- We can evolve each model independently without breaking the API

HOW THESE WILL BE USED:
------------------------
- ReadingIn: Validates data sent TO our API (POST /readings)
- ReadingOut: Defines the structure of data returned FROM our API
  (GET /latest, GET /readings, etc.)

These models match the exact JSON format produced by cli_obd_loop.py
"""

from pydantic import BaseModel


class ReadingIn(BaseModel):
    """
    Model for incoming OBD-II readings from the CLI loop.
    Used when POST-ing new sensor data to the API.

    All sensor fields can be None if the reading failed or
    the sensor is not supported by the vehicle.
    """
    timestamp: str
    rpm: int | None
    speed_mph: float | None
    coolant_temp_f: float | None
    throttle_pct: float | None
    load_pct: float | None
    maf_gps: float | None


class ReadingOut(BaseModel):
    """
    Model for OBD-II readings returned by the API.
    Used when the API sends sensor data back to clients.

    Structure is identical to ReadingIn for simplicity.
    In future steps, this might include additional fields like
    a database ID or computed values.
    """
    timestamp: str
    rpm: int | None
    speed_mph: float | None
    coolant_temp_f: float | None
    throttle_pct: float | None
    load_pct: float | None
    maf_gps: float | None
