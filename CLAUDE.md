# CLAUDE.md - AI Assistant Guide for OBD2 Telemetry Project

## Project Overview

This is a **Raspberry Pi OBD-II Data Logger and Telemetry Dashboard** that collects real-time vehicle sensor data via an ELM327 Bluetooth adapter, stores it in a database, and visualizes it through a mobile-friendly web dashboard.

**Primary Use Case**: Run on a Raspberry Pi in a car to log, visualize, and analyze OBD-II sensor data in real-time, accessible from mobile devices on the same network.

**Tech Stack**:
- Python 3.10+
- FastAPI (REST API backend)
- Streamlit (interactive dashboard UI)
- SQLite (data persistence)
- python-OBD (hardware communication)
- Plotly (data visualization)

---

## Codebase Structure

```
Obd2/
├── README.md                      # Main project documentation
├── CLI_README.md                  # CLI loop documentation
├── AGENTS.md                      # AI agent behavioral guidelines
├── requirements.txt               # Python dependencies (plotly only - minimal)
│
├── main.py                        # Original data logger with fake/real modes
├── cli_obd_loop.py                # Standalone JSON output loop for OBD data
├── api_server.py                  # FastAPI backend server (770 lines)
├── database.py                    # SQLAlchemy database setup
├── models.py                      # SQLAlchemy ORM models
├── schemas.py                     # Pydantic request/response schemas
├── data_manager.py                # CSV data utilities (legacy Stage 1)
│
├── telemetry_dashboard/
│   └── app.py                     # Streamlit dashboard (794 lines)
│
├── templates/
│   └── dashboard.html             # HTML dashboard template
│
├── .streamlit/
│   └── config.toml                # Streamlit theme config (dark mode)
│
├── *.service                      # Systemd service files for Pi deployment
│   ├── obd-api.service            # FastAPI server service
│   ├── obd-reader.service         # OBD loop service
│   └── streamlit-dashboard.service # Streamlit dashboard service
│
├── readings.db                    # SQLite database (auto-created)
├── obd_readings.csv               # Legacy CSV output (gitignored)
│
└── .github/workflows/
    └── test.yml                   # CI/CD smoke tests
```

---

## Architecture Components

### 1. Data Collection Layer

**Files**: `cli_obd_loop.py`, `main.py`

- **cli_obd_loop.py**: Standalone script that reads OBD-II data every second and outputs JSON to stdout
  - Auto-detects `/dev/rfcomm0` (Bluetooth ELM327 adapter)
  - Falls back to simulation mode if hardware unavailable
  - Clean separation: JSON to stdout, logs to stderr
  - Designed for piping to other programs

- **main.py**: Original prototype with CSV logging
  - Supports `--fake` mode for development without hardware
  - Handles SIGINT for graceful shutdown
  - Used by GitHub Actions for smoke tests

**Key PIDs Collected**:
- RPM (engine speed)
- Speed (mph)
- Coolant temperature (°F)
- Throttle position (%)
- Engine load (%)
- Mass air flow (grams/second)

### 2. API Backend Layer

**Files**: `api_server.py`, `database.py`, `models.py`, `schemas.py`

- **api_server.py**: FastAPI server exposing REST endpoints
  - `POST /readings` - Store new sensor readings
  - `GET /latest` - Fetch most recent reading
  - `GET /readings?limit=N` - Query historical data
  - `GET /readings/range?start=X&end=Y` - Time-based queries
  - `POST /trip/start` & `/trip/end` - Trip session tracking
  - `GET /dashboard` - HTML dashboard view
  - `GET /health` - Health check endpoint
  - `GET /diagnostics` - System diagnostics (CPU, memory, disk, network)

- **database.py**: SQLAlchemy engine and session configuration
  - SQLite with `check_same_thread=False` for FastAPI threading
  - Database file: `readings.db`

- **models.py**: ORM model for `readings` table
  - Auto-incrementing ID
  - All sensor fields nullable (handles sensor failures)

- **schemas.py**: Pydantic models for request/response validation
  - `ReadingIn` - Incoming POST data
  - `ReadingOut` - API responses

### 3. Dashboard Layer

**Files**: `telemetry_dashboard/app.py`, `.streamlit/config.toml`

- **app.py**: Streamlit dashboard with real-time telemetry visualization
  - Auto-refreshes every 3 seconds (configurable)
  - **TV Mode** toggle for large-screen display (350px gauges vs 200px)
  - **Gauge visualizations**: RPM, Speed, Throttle
  - **Metrics**: Engine Load, Coolant Temp, MAF
  - **Trip Monitor**: Distance, duration, avg speed, fuel consumption estimates
  - **History Charts**: Time-series graphs for trends
  - **Insights Panel**: Rule-based alerts and recommendations
  - **System Diagnostics**: CPU, memory, disk, network stats
  - Mobile-optimized layout

- **config.toml**: Dark theme with green accent (`#2E8B57`)

### 4. Deployment

**Files**: `*.service` (systemd unit files)

Three services run on the Raspberry Pi:
1. `obd-reader.service` - Runs `cli_obd_loop.py` continuously
2. `obd-api.service` - Runs FastAPI server on port 8000
3. `streamlit-dashboard.service` - Runs Streamlit on port 8501

**Installation**:
```bash
sudo cp *.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable obd-reader obd-api streamlit-dashboard
sudo systemctl start obd-reader obd-api streamlit-dashboard
```

---

## Development Workflows

### Local Development

1. **Setup**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   pip install fastapi uvicorn sqlalchemy pydantic streamlit requests psutil
   ```

2. **Run in Fake Mode** (no hardware needed):
   ```bash
   # Test data collection
   python3 main.py --fake --print-sample

   # Run API server
   python3 api_server.py

   # Run dashboard (in separate terminal)
   cd telemetry_dashboard
   streamlit run app.py
   ```

3. **Access**:
   - API docs: http://localhost:8000/docs
   - Dashboard: http://localhost:8501

### Git Workflow

- **Main branch**: `main` (protected)
- **Feature branches**: Use `claude/` prefix followed by session ID
  - Example: `claude/claude-md-mi2jkgehuivfog2n-01W6s9jd7AWRXDV4GXZsuEpd`
- **Commit style**: Clear, concise messages focused on "why" not "what"
  - Examples from history: "Add TV mode toggle with responsive layout scaling", "Add system diagnostics to telemetry dashboard"
- **PR workflow**: Features developed in branches, merged via GitHub PRs

### Testing

**CI/CD**: GitHub Actions workflow (`.github/workflows/test.yml`)
- Runs on: push to main, PRs, manual dispatch
- Smoke tests:
  - `python main.py --fake --smoke-test`
  - `python main.py --fake-run 3`
  - CSV integrity validation
  - Graceful shutdown verification

**Local Testing**:
```bash
# Quick smoke test
python3 main.py --fake --smoke-test

# Run 5 fake readings
python3 main.py --fake-run 5

# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/latest
```

---

## Key Conventions for AI Assistants

### Code Style Guidelines (from AGENTS.md)

1. **Simplicity First**:
   - Keep code readable and beginner-friendly
   - Avoid unnecessary abstractions
   - Prefer explicit logic over cleverness
   - Target audience: beginner–intermediate programmers

2. **Comments**:
   - Add comments sparingly but clearly
   - Extensive docstrings on modules/classes explaining "what" and "why"
   - Inline comments only for non-obvious logic

3. **Naming**:
   - Clear, descriptive variable names
   - No abbreviations except common ones (rpm, mph, etc.)

4. **State Management**:
   - Avoid global state unless absolutely required
   - Use `st.session_state` for Streamlit UI state
   - Module-level variables for trip tracking in API (documented as non-persistent)

5. **Performance**:
   - Lightweight implementations for Raspberry Pi
   - Avoid heavy plotting libraries
   - Keep gauge rendering performant for real-time updates

### Forbidden Practices

**DO NOT**:
- Introduce containerization (Docker, etc.)
- Add CI/CD pipelines beyond current GitHub Actions
- Rewrite large portions of codebase without direction
- Use advanced frontend frameworks (React, Vue, plain JS)
- Modify backend logic unless specifically instructed
- Add unnecessary dependencies

### File Modification Rules

- **NEVER modify**:
  - Backend code unless explicitly directed
  - Service files without user confirmation
  - Database schema without migration plan

- **Prefer editing over creating**:
  - Always edit existing files rather than creating new ones
  - Maintain logical structure of project
  - Avoid major refactors unless requested

### Dashboard Development

- Main dashboard stays in `telemetry_dashboard/app.py` unless split is requested
- Keep utility functions in lightweight helper modules if needed
- Maintain mobile-first responsive design
- Test on both desktop and mobile viewports
- Consider TV Mode (large-screen) when adding visual elements

---

## Common Tasks for AI Assistants

### Adding a New Sensor/PID

1. Update `schemas.py` - Add field to `ReadingIn` and `ReadingOut`
2. Update `models.py` - Add column to `ReadingModel`
3. Update `cli_obd_loop.py` - Query the new PID
4. Update `telemetry_dashboard/app.py` - Add visualization
5. Test in fake mode first
6. Document in relevant README files

### Adding Dashboard Features

1. Check `telemetry_dashboard/app.py` structure
2. Add feature in appropriate section (gauges, metrics, history, etc.)
3. Respect TV mode toggle (`tv_mode` variable)
4. Use session state for UI persistence
5. Test auto-refresh behavior
6. Ensure mobile responsiveness

### Modifying API Endpoints

1. Update `api_server.py`
2. Use Pydantic models from `schemas.py` for validation
3. Follow existing patterns for database access
4. Update docstrings
5. Test with `/docs` interactive API
6. Update dashboard if endpoint is consumed there

### Database Changes

1. **Never** directly modify `readings.db`
2. Schema changes require updating:
   - `models.py` (ORM model)
   - `schemas.py` (Pydantic schemas)
   - Migration strategy (if breaking change)
3. Consider backward compatibility
4. Test with fresh database creation

---

## Configuration & Customization

### Streamlit Theme

Edit `.streamlit/config.toml`:
- `primaryColor` - Accent color (currently SeaGreen `#2E8B57`)
- `backgroundColor` - Main background (dark: `#0E1117`)
- `secondaryBackgroundColor` - Card backgrounds (`#262730`)
- `textColor` - Text (`#FAFAFA`)

### Refresh Rate

Dashboard auto-refresh configured in `telemetry_dashboard/app.py`:
```python
st.session_state.refresh_ttl = 3  # seconds
```

### Hardware Connection

Bluetooth ELM327 binding:
```bash
hcitool scan                          # Find MAC address
sudo rfcomm bind 0 00:1D:A5:09:2E:B3 1  # Bind to /dev/rfcomm0
```

---

## Data Flow

```
ELM327 Adapter (Bluetooth)
    ↓
/dev/rfcomm0
    ↓
cli_obd_loop.py (JSON stdout)
    ↓
POST to api_server.py /readings
    ↓
SQLite Database (readings.db)
    ↓
GET from telemetry_dashboard/app.py
    ↓
Streamlit UI (mobile/desktop browser)
```

---

## Troubleshooting

### Dashboard Shows No Data
- Check API server is running: `curl http://localhost:8000/health`
- Verify database exists and has data: `sqlite3 readings.db "SELECT COUNT(*) FROM readings;"`
- Check Streamlit API URL configuration in `app.py`

### Simulation Mode Not Working
- Verify `cli_obd_loop.py` has simulation fallback
- Check for import errors with `python-obd`
- Run `python3 cli_obd_loop.py` directly to see stderr logs

### Service Not Starting
- Check logs: `sudo journalctl -u obd-api.service -f`
- Verify working directory in service file matches actual path
- Check user permissions in service file

### CI/CD Failing
- Smoke tests require `main.py --fake` mode
- Check `obd_readings.csv` is gitignored but creation works
- Verify Python 3.11+ compatibility

---

## API Endpoint Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Server health check |
| GET | `/diagnostics` | System diagnostics (CPU, memory, disk, network) |
| POST | `/readings` | Store new OBD reading |
| GET | `/latest` | Fetch most recent reading |
| GET | `/readings?limit=N` | Get last N readings |
| GET | `/readings/range?start=X&end=Y` | Time-based query |
| POST | `/trip/start` | Begin trip recording |
| POST | `/trip/end` | End trip recording |
| GET | `/trip/status` | Current trip status |
| GET | `/dashboard` | HTML dashboard view |
| GET | `/docs` | Interactive API documentation |

---

## Environment & Runtime

- **Target Platform**: Raspberry Pi (any model with Bluetooth)
- **Python Version**: 3.10+ (tested on 3.11)
- **User Access**: Dashboard accessed from Android/iOS devices via LAN IP
- **Deployment Method**: systemd services (no containers)
- **Data Storage**: Local SQLite (no cloud dependencies)

---

## Agent Behavioral Notes

This project follows the **"Streamlit Conjurer" pattern** described in AGENTS.md:
- AI acts as implementation engine following high-level instructions
- Maintains beginner-friendly code
- Avoids over-engineering
- Preserves Pi hardware compatibility
- Focuses on incremental, understandable changes

**When working on this project**:
1. Read AGENTS.md for specific behavioral guidelines
2. Prioritize clarity over cleverness
3. Test in fake mode before hardware deployment
4. Keep mobile UX in mind for dashboard changes
5. Respect the Raspberry Pi's performance constraints
6. Follow existing patterns rather than introducing new paradigms

---

## Version History Highlights

Recent features (from git log):
- System diagnostics integration (CPU, memory, disk, network)
- Rule-based insights panel with real-time alerts
- TV mode toggle for large-screen display
- Trip monitoring with session tracking
- Historical data charts
- Efficiency metrics (MPG estimates, MAF)
- Mobile dashboard UI polish
- OBD connection status monitoring

---

## Future Considerations

Areas marked for future development (from TODOs in code):
- Persistent trip history (database table for trips)
- Auto-reconnect loop improvements
- Additional PID support (fuel level, intake temp, etc.)
- Alert thresholds customization
- Data export features (CSV, JSON downloads)
- Multi-vehicle support
- Advanced analytics (trend detection, anomaly detection)

---

## Quick Reference Commands

```bash
# Development
python3 main.py --fake --print-sample    # Test data generation
python3 api_server.py                    # Run API server
streamlit run telemetry_dashboard/app.py # Run dashboard

# Testing
python3 main.py --fake-run 5             # Generate 5 fake readings
curl http://localhost:8000/health        # Test API health
curl http://localhost:8000/latest        # Get latest reading

# Deployment
sudo systemctl status obd-api            # Check service status
sudo journalctl -u obd-api -f            # View live logs
sudo systemctl restart obd-api           # Restart service

# Hardware
hcitool scan                             # Find Bluetooth devices
sudo rfcomm bind 0 MAC_ADDRESS 1         # Bind ELM327 adapter
ls -la /dev/rfcomm0                      # Verify device binding

# Database
sqlite3 readings.db "SELECT COUNT(*) FROM readings;"  # Row count
sqlite3 readings.db ".schema readings"                # Schema info
```

---

**Last Updated**: 2025-11-17
**Project Maintainer**: mshears713
**Documentation Version**: 1.0
