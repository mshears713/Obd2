#!/usr/bin/env python3
"""
OBD Pi API Server
=================

This is a simple FastAPI server that will eventually receive and serve
car telemetry data from the OBD-II adapter on your Raspberry Pi.

HOW TO RUN:
-----------
    python3 api_server.py

The server will start on port 8000.

HOW TO ACCESS FROM YOUR IPHONE:
--------------------------------
1. Connect your iPhone to the same network as your Raspberry Pi
2. Find your Pi's IP address with: hostname -I
3. Open Safari on your iPhone and go to:
   http://YOUR_PI_IP_ADDRESS:8000/docs

   Example: http://192.168.1.100:8000/docs

This will open the interactive API documentation where you can
test all endpoints directly from your phone.

WHAT THIS FILE DOES (FOR NOW):
-------------------------------
- Provides a /health endpoint to verify the server is running
- Establishes the foundation for future endpoints

WHAT THIS FILE NOW DOES:
------------------------
- Uses SQLite database for permanent storage of OBD-II readings
- POST /readings endpoint accepts and stores new readings
- GET /latest endpoint fetches the most recent reading
- GET /readings endpoint queries historical data with optional limit
- All data persists across server restarts
"""

from fastapi import FastAPI, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from schemas import ReadingIn, ReadingOut
from database import SessionLocal, engine
from models import Base, ReadingModel
from datetime import datetime, timezone, timedelta

# Create the FastAPI application
app = FastAPI(
    title="OBD Pi API",
    description="Local API for car telemetry on Raspberry Pi"
)

# Initialize template engine for HTML pages
# Templates are stored in the "templates" directory
templates = Jinja2Templates(directory="templates")

# Create database tables if they don't exist
# This runs once when the app starts and creates the "readings" table
Base.metadata.create_all(bind=engine)


# -------------------------------------------------
# DATABASE SESSION HELPER
# -------------------------------------------------
def get_db():
    """
    Creates a new database session for each request.
    The session is automatically closed when the request finishes.

    This is a generator function that FastAPI will use with dependency injection.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------
# IN-MEMORY STORAGE (NO LONGER USED)
# -------------------------------------------------
# The in-memory list has been replaced with SQLite database storage.
# All endpoints now read and write to the database for permanent storage.
# readings_memory = []  # ← No longer needed!


# -------------------------------------------------
# TRIP TRACKING STATE
# -------------------------------------------------
# Simple module-level variables for trip recording.
# These are reset when the server restarts.
# For persistent trip history, consider adding a trips table to the database.
trip_active = False       # Is a trip currently being recorded?
trip_start_time = None    # When did the trip start? (datetime object)
trip_end_time = None      # When did the trip end? (datetime object)


# -------------------------------------------------
# BASIC ENDPOINTS
# -------------------------------------------------

@app.get("/health")
def health_check():
    """
    Simple health check endpoint to verify the API is running.
    Returns a status message.
    """
    return {"status": "ok"}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    """
    Serve the live dashboard HTML page.

    This provides a simple web UI that auto-updates every second
    with the latest OBD reading from your car.

    Access it at: http://YOUR_PI_IP:8000/dashboard
    """
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.post("/readings", response_model=ReadingOut)
def create_reading(payload: ReadingIn, db: Session = Depends(get_db)):
    """
    Accept a new OBD-II reading and store it permanently in the SQLite database.

    Steps:
    1. Pydantic validates the incoming JSON against ReadingIn
    2. We convert it to a ReadingModel ORM object
    3. SQLAlchemy adds it to the database session
    4. We commit to save it permanently
    5. We refresh to get the auto-generated ID from the database
    6. Return the saved reading as ReadingOut

    Why refresh()?
    -------------
    After commit(), the database auto-generates the ID field.
    refresh() fetches the new ID back into our Python object.
    """
    # Create an ORM object from the validated Pydantic model
    # **payload.model_dump() unpacks the dict into keyword arguments
    db_reading = ReadingModel(**payload.model_dump())

    # Add the new reading to the database session (staged, not saved yet)
    db.add(db_reading)

    # Commit the transaction to permanently save to the database file
    db.commit()

    # Refresh the object to get the auto-generated ID and any defaults
    db.refresh(db_reading)

    # Return the ORM object (FastAPI auto-converts to ReadingOut)
    return db_reading


@app.get("/latest", response_model=ReadingOut)
def get_latest(db: Session = Depends(get_db)):
    """
    Get the most recent OBD-II reading from the database.

    Why order by ID instead of timestamp?
    --------------------------------------
    IDs auto-increment with each insert, so the highest ID is always
    the most recent row. This is simpler and faster than parsing timestamps.

    Returns:
    --------
    - The latest ReadingModel ORM object (converted to ReadingOut by FastAPI)
    - Or an error dict if no readings exist yet
    """
    # Query the database, order by ID descending, get the first result
    # .desc() means descending (highest first)
    # .first() returns one row or None
    latest = db.query(ReadingModel).order_by(ReadingModel.id.desc()).first()

    # Check if the database is empty
    if not latest:
        return {"error": "No readings available yet"}

    # Return the ORM object (FastAPI converts it to JSON using ReadingOut)
    return latest


@app.get("/readings", response_model=list[ReadingOut])
def get_readings(limit: int = 20, db: Session = Depends(get_db)):
    """
    Get recent OBD-II readings from the database with optional limit.

    Query parameters:
    -----------------
    - limit: How many readings to return (default: 20, maximum: no limit)

    Examples:
    ---------
    - /readings          → Last 20 readings
    - /readings?limit=5  → Last 5 readings
    - /readings?limit=100 → Last 100 readings

    Returns:
    --------
    A list of ReadingOut objects, sorted from newest to oldest.

    Why this replaces in-memory storage:
    ------------------------------------
    The old readings_memory list was lost on server restart.
    Now all data is permanently saved in readings.db and queried on demand.
    """
    # Query the database for the N most recent readings
    # .order_by(ReadingModel.id.desc()) → newest first (highest ID)
    # .limit(limit) → only return this many rows
    # .all() → return as a list (not a single row)
    readings = db.query(ReadingModel).order_by(ReadingModel.id.desc()).limit(limit).all()

    # Return the list of ORM objects (FastAPI converts to list[ReadingOut])
    return readings


# -------------------------------------------------
# DASHBOARD-FRIENDLY ENDPOINTS
# -------------------------------------------------

@app.get("/stats")
def get_stats(limit: int = 60, db: Session = Depends(get_db)):
    """
    Get summary statistics computed from recent readings.

    Query parameters:
    -----------------
    - limit: Number of recent readings to analyze (default: 60)

    Returns:
    --------
    A dictionary with computed statistics:
    - average_rpm: Average engine RPM
    - average_speed_mph: Average speed
    - max_coolant_temp_f: Maximum coolant temperature
    - min_coolant_temp_f: Minimum coolant temperature
    - average_throttle_pct: Average throttle position

    Why these stats?
    ----------------
    These provide a quick overview for a dashboard UI without needing
    to download all individual readings. Perfect for mobile displays.
    """
    # Get the most recent N readings
    readings = db.query(ReadingModel).order_by(ReadingModel.id.desc()).limit(limit).all()

    # Check if we have any data
    if not readings:
        return {"error": "No readings available yet"}

    # Compute averages and min/max
    # Filter out None values when computing stats

    # RPM: average of non-null values
    rpm_values = [r.rpm for r in readings if r.rpm is not None]
    average_rpm = round(sum(rpm_values) / len(rpm_values), 1) if rpm_values else None

    # Speed: average of non-null values
    speed_values = [r.speed_mph for r in readings if r.speed_mph is not None]
    average_speed_mph = round(sum(speed_values) / len(speed_values), 1) if speed_values else None

    # Coolant temp: min and max
    coolant_values = [r.coolant_temp_f for r in readings if r.coolant_temp_f is not None]
    max_coolant_temp_f = round(max(coolant_values), 1) if coolant_values else None
    min_coolant_temp_f = round(min(coolant_values), 1) if coolant_values else None

    # Throttle: average of non-null values
    throttle_values = [r.throttle_pct for r in readings if r.throttle_pct is not None]
    average_throttle_pct = round(sum(throttle_values) / len(throttle_values), 1) if throttle_values else None

    return {
        "readings_analyzed": len(readings),
        "average_rpm": average_rpm,
        "average_speed_mph": average_speed_mph,
        "max_coolant_temp_f": max_coolant_temp_f,
        "min_coolant_temp_f": min_coolant_temp_f,
        "average_throttle_pct": average_throttle_pct
    }


@app.get("/recent", response_model=list[ReadingOut])
def get_recent(seconds: int = 30, db: Session = Depends(get_db)):
    """
    Get all readings from the past N seconds.

    Query parameters:
    -----------------
    - seconds: How far back to look (default: 30)

    Returns:
    --------
    List of readings that occurred within the past N seconds,
    sorted from newest to oldest.

    How it works:
    -------------
    1. Calculate the cutoff time (now - N seconds)
    2. Query all readings and filter by timestamp
    3. Return matching readings

    Note: Timestamps are stored as ISO8601 strings, so we parse them
    to compare with the current time.
    """
    # Calculate the cutoff time (current time minus N seconds)
    cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=seconds)

    # Get all readings (we'll filter in Python since timestamps are strings)
    # For better performance with large datasets, consider storing timestamps as datetime
    all_readings = db.query(ReadingModel).order_by(ReadingModel.id.desc()).all()

    # Filter readings based on timestamp
    recent_readings = []
    for reading in all_readings:
        try:
            # Parse the ISO8601 timestamp string
            reading_time = datetime.fromisoformat(reading.timestamp.replace('Z', '+00:00'))

            # Check if it's within our time window
            if reading_time >= cutoff_time:
                recent_readings.append(reading)
        except (ValueError, AttributeError):
            # Skip readings with invalid timestamps
            continue

    return recent_readings


@app.get("/vehicle-state")
def get_vehicle_state(db: Session = Depends(get_db)):
    """
    Get a simple snapshot of current vehicle conditions.

    Returns:
    --------
    A dictionary with interpreted states:
    - is_moving: True if speed > 1 mph
    - engine_temp_status: "cool" | "normal" | "hot"
    - throttle_activity: "idle" | "light" | "high"

    How it works:
    -------------
    Uses the most recent reading and simple threshold logic to
    interpret the raw sensor values into human-friendly states.

    Temperature thresholds:
    - cool: < 140°F
    - normal: 140-220°F
    - hot: > 220°F

    Throttle thresholds:
    - idle: < 5%
    - light: 5-30%
    - high: > 30%
    """
    # Get the most recent reading
    latest = db.query(ReadingModel).order_by(ReadingModel.id.desc()).first()

    # Check if we have any data
    if not latest:
        return {"error": "No readings available yet"}

    # Determine if vehicle is moving
    # Consider moving if speed > 1 mph (accounts for sensor noise at 0)
    is_moving = False
    if latest.speed_mph is not None:
        is_moving = latest.speed_mph > 1.0

    # Determine engine temperature status
    engine_temp_status = "unknown"
    if latest.coolant_temp_f is not None:
        if latest.coolant_temp_f < 140:
            engine_temp_status = "cool"
        elif latest.coolant_temp_f <= 220:
            engine_temp_status = "normal"
        else:
            engine_temp_status = "hot"

    # Determine throttle activity level
    throttle_activity = "unknown"
    if latest.throttle_pct is not None:
        if latest.throttle_pct < 5:
            throttle_activity = "idle"
        elif latest.throttle_pct <= 30:
            throttle_activity = "light"
        else:
            throttle_activity = "high"

    return {
        "is_moving": is_moving,
        "engine_temp_status": engine_temp_status,
        "throttle_activity": throttle_activity,
        "latest_reading": {
            "timestamp": latest.timestamp,
            "rpm": latest.rpm,
            "speed_mph": latest.speed_mph,
            "coolant_temp_f": latest.coolant_temp_f,
            "throttle_pct": latest.throttle_pct
        }
    }


# -------------------------------------------------
# TRIP RECORDING ENDPOINTS
# -------------------------------------------------

@app.post("/trip/start")
def trip_start():
    """
    Start recording a trip.

    This endpoint should be called at the beginning of a drive (e.g., via iPhone Shortcut).
    It marks the current time as the trip start and activates trip tracking.

    Returns:
    --------
    Confirmation message with the trip start time.
    """
    global trip_active, trip_start_time, trip_end_time

    # Mark the trip as active
    trip_active = True

    # Record the current time as the trip start
    trip_start_time = datetime.now(timezone.utc)

    # Reset end time (in case there was a previous trip)
    trip_end_time = None

    return {
        "message": "Trip started",
        "trip_active": trip_active,
        "start_time": trip_start_time.isoformat()
    }


@app.post("/trip/end")
def trip_end():
    """
    End the current trip recording.

    This endpoint should be called at the end of a drive (e.g., via iPhone Shortcut).
    It marks the current time as the trip end and deactivates trip tracking.

    Returns:
    --------
    Confirmation message with the trip end time.
    Warns if no trip was active.
    """
    global trip_active, trip_end_time

    # Check if a trip was actually active
    if not trip_active:
        return {
            "warning": "No trip was active",
            "trip_active": False
        }

    # Mark the trip as inactive
    trip_active = False

    # Record the current time as the trip end
    trip_end_time = datetime.now(timezone.utc)

    return {
        "message": "Trip ended",
        "trip_active": trip_active,
        "end_time": trip_end_time.isoformat()
    }


@app.get("/trip/summary")
def trip_summary(db: Session = Depends(get_db)):
    """
    Get a complete summary of the most recent trip.

    This endpoint computes:
    - Duration
    - Distance traveled (approximate)
    - Fuel consumption (estimated from MAF)
    - MPG estimate
    - Speed and RPM statistics

    How fuel consumption is calculated:
    -----------------------------------
    MAF (Mass Air Flow) measures grams of air per second entering the engine.
    We use the stoichiometric air-fuel ratio (AFR = 14.7:1 for gasoline) to
    estimate fuel consumption:

    1. Total air mass = sum of (maf_gps * 1 second) for all samples
    2. Fuel mass = air mass / 14.7
    3. Fuel volume = fuel mass / gasoline density (0.74 g/mL)
    4. Convert mL to gallons (divide by 3785.41)

    This is an ESTIMATE and may not match your car's actual fuel gauge.

    Returns:
    --------
    Dictionary with trip statistics including distance, fuel, and MPG.
    """
    global trip_start_time, trip_end_time

    # Check if a trip has been recorded
    if trip_start_time is None:
        return {"error": "No trip has been recorded yet. Use POST /trip/start to begin."}

    if trip_end_time is None:
        return {"error": "Trip is still active. Use POST /trip/end to finish the trip."}

    # Query all readings between start and end times
    # Timestamps are stored as ISO8601 strings, so we need to parse them
    all_readings = db.query(ReadingModel).all()

    # Filter readings that fall within the trip time window
    trip_readings = []
    for reading in all_readings:
        try:
            # Parse the timestamp string to a datetime object
            # Handle both formats: with 'Z' and with '+00:00'
            reading_time = datetime.fromisoformat(reading.timestamp.replace('Z', '+00:00'))

            # Check if this reading occurred during the trip
            if trip_start_time <= reading_time <= trip_end_time:
                trip_readings.append(reading)
        except (ValueError, AttributeError):
            # Skip readings with invalid timestamps
            continue

    # Check if we have any trip data
    if not trip_readings:
        return {
            "error": "No readings found during trip",
            "trip_start": trip_start_time.isoformat(),
            "trip_end": trip_end_time.isoformat()
        }

    # ============================================================
    # COMPUTE TRIP STATISTICS
    # ============================================================

    # Duration: difference between start and end times
    duration_seconds = (trip_end_time - trip_start_time).total_seconds()

    # Total number of samples
    total_samples = len(trip_readings)

    # Speed statistics (filter out None values)
    speed_values = [r.speed_mph for r in trip_readings if r.speed_mph is not None]
    average_speed_mph = round(sum(speed_values) / len(speed_values), 1) if speed_values else None
    max_speed_mph = round(max(speed_values), 1) if speed_values else None

    # RPM statistics
    rpm_values = [r.rpm for r in trip_readings if r.rpm is not None]
    max_rpm = max(rpm_values) if rpm_values else None

    # Coolant temperature
    coolant_values = [r.coolant_temp_f for r in trip_readings if r.coolant_temp_f is not None]
    max_coolant_temp_f = round(max(coolant_values), 1) if coolant_values else None

    # Throttle statistics
    throttle_values = [r.throttle_pct for r in trip_readings if r.throttle_pct is not None]
    average_throttle_pct = round(sum(throttle_values) / len(throttle_values), 1) if throttle_values else None

    # ============================================================
    # DISTANCE CALCULATION
    # ============================================================
    # Approximate distance by summing speed over time.
    # Since we sample once per second: distance = speed * (1/3600) hour
    total_distance_miles = 0.0
    for reading in trip_readings:
        if reading.speed_mph is not None:
            # Distance = speed (mph) * time (hours)
            # 1 second = 1/3600 hour
            total_distance_miles += reading.speed_mph * (1 / 3600)

    total_distance_miles = round(total_distance_miles, 2)

    # ============================================================
    # FUEL CONSUMPTION CALCULATION (MAF-BASED)
    # ============================================================
    # MAF (Mass Air Flow) tells us how much air enters the engine (g/s).
    # Using stoichiometric AFR for gasoline (14.7:1), we can estimate fuel.
    #
    # Steps:
    # 1. Calculate total air mass consumed during trip
    # 2. Divide by AFR to get fuel mass
    # 3. Convert to volume using gasoline density
    # 4. Convert mL to gallons

    maf_values = [r.maf_gps for r in trip_readings if r.maf_gps is not None]

    fuel_used_gallons = None
    mpg_estimate = None
    fuel_note = None

    if maf_values:
        # Total air mass = sum of (MAF * 1 second) for all samples
        total_air_mass_g = sum(maf_values)  # grams of air

        # Stoichiometric air-fuel ratio for gasoline
        AFR = 14.7

        # Calculate fuel mass consumed
        fuel_mass_g = total_air_mass_g / AFR

        # Convert fuel mass to volume
        # Gasoline density ≈ 0.74 g/mL
        gasoline_density = 0.74  # g/mL
        fuel_volume_ml = fuel_mass_g / gasoline_density

        # Convert mL to gallons (1 gallon = 3785.41 mL)
        fuel_used_gallons = round(fuel_volume_ml / 3785.41, 3)

        # Calculate MPG if we have both distance and fuel
        if fuel_used_gallons > 0 and total_distance_miles > 0:
            mpg_estimate = round(total_distance_miles / fuel_used_gallons, 1)
    else:
        fuel_note = "MAF data not available - fuel consumption could not be estimated"

    # ============================================================
    # RETURN TRIP SUMMARY
    # ============================================================

    return {
        "trip_start": trip_start_time.isoformat(),
        "trip_end": trip_end_time.isoformat(),
        "duration_seconds": round(duration_seconds, 1),
        "total_samples": total_samples,
        "total_distance_miles": total_distance_miles,
        "average_speed_mph": average_speed_mph,
        "max_speed_mph": max_speed_mph,
        "max_rpm": max_rpm,
        "max_coolant_temp_f": max_coolant_temp_f,
        "average_throttle_pct": average_throttle_pct,
        "fuel_used_gallons": fuel_used_gallons,
        "mpg_estimate": mpg_estimate,
        "note": fuel_note
    }


# Run the server when this file is executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",  # Listen on all network interfaces
        port=8000,
        reload=False
    )
