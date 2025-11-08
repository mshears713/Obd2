# OBD-II JSON CLI Loop

Simple standalone script that outputs one JSON reading per second from your car's OBD-II adapter.

---

## 📦 Installation

### 1. Install Python Dependencies

On Raspberry Pi:

```bash
pip3 install obd pyserial --break-system-packages
```

### 2. Bind Your Bluetooth ELM327 Adapter

First, find your adapter's MAC address (one-time setup):

```bash
hcitool scan
```

You should see something like:
```
Scanning ...
    00:1D:A5:09:2E:B3    OBDII
```

Then bind it to `/dev/rfcomm0` (channel 1):

```bash
sudo rfcomm bind 0 00:1D:A5:09:2E:B3 1
```

**Note:** Replace `00:1D:A5:09:2E:B3` with your adapter's actual MAC address.

The binding persists until reboot. To make it permanent, add to `/etc/rc.local` or create a systemd service.

---

## 🚗 Usage

### Run the JSON logger:

```bash
python3 cli_obd_loop.py
```

Or make it executable:

```bash
chmod +x cli_obd_loop.py
./cli_obd_loop.py
```

### Stop the logger:

Press `Ctrl-C`

---

## 📊 Example Output

### Successful Connection

**STDERR (info/warnings):**
```
[info] Starting OBD-II JSON logger...
[info] Connecting to OBD-II adapter at /dev/rfcomm0...
[info] Connected! Protocol: SAE J1850 VPW
[info] 52 PIDs available
[info] Outputting one JSON line per second (Ctrl-C to stop)
```

**STDOUT (JSON data):**
```json
{"timestamp": "2025-11-06T23:24:07+00:00", "rpm": 0, "speed_mph": 0.0, "coolant_temp_f": 53.6, "throttle_pct": 0.0, "load_pct": 0.8, "maf_gps": 2.45}
{"timestamp": "2025-11-06T23:24:08+00:00", "rpm": 0, "speed_mph": 0.0, "coolant_temp_f": 53.6, "throttle_pct": 0.0, "load_pct": 0.8, "maf_gps": 2.45}
{"timestamp": "2025-11-06T23:24:09+00:00", "rpm": 950, "speed_mph": 0.0, "coolant_temp_f": 185.2, "throttle_pct": 12.5, "load_pct": 15.3, "maf_gps": 5.23}
```

---

## 🔧 Simulation Mode

If the OBD adapter is not detected, the script **automatically falls back to simulation mode**.

### When Does Simulation Mode Trigger?

- `/dev/rfcomm0` does not exist (adapter not bound)
- `python-obd` module is not installed
- Connection to adapter fails

### How to Identify Simulation Mode

You'll see this warning at startup:

```
[warning] OBD adapter not detected — using simulation mode
[info] To connect real adapter: sudo rfcomm bind 0 00:1D:A5:09:2E:B3 1
[info] Running in SIMULATION MODE
```

### Simulation Data

Simulation generates realistic sensor values using time-based sine waves:
- **RPM**: 750-1100 (idle fluctuation)
- **Speed**: 0-45 mph (slow oscillation)
- **Coolant Temp**: 180-190°F (warm engine)
- **Throttle**: 0-25% (gentle variation)
- **Load**: 5-25%
- **MAF**: 2-8 grams/second

---

## 📋 JSON Fields

Each JSON line contains the following fields:

| Field             | Type    | Unit                    | Description                           |
|-------------------|---------|-------------------------|---------------------------------------|
| `timestamp`       | string  | ISO8601 UTC             | When the reading was taken            |
| `rpm`             | int     | revolutions per minute  | Engine speed (null if engine off)     |
| `speed_mph`       | float   | miles per hour          | Vehicle speed                         |
| `coolant_temp_f`  | float   | degrees Fahrenheit      | Engine coolant temperature            |
| `throttle_pct`    | float   | percent (0-100)         | Throttle position                     |
| `load_pct`        | float   | percent (0-100)         | Calculated engine load                |
| `maf_gps`         | float   | grams per second        | Mass air flow                         |

**Note:** Any field can be `null` if the sensor is unavailable or the PID query fails.

---

## 🔄 Piping to Other Programs

Since the script outputs clean JSON to `stdout` and logs to `stderr`, you can easily pipe the data:

### Save JSON to a file:
```bash
python3 cli_obd_loop.py > obd_data.jsonl 2>/dev/null
```

### Process with jq:
```bash
python3 cli_obd_loop.py 2>/dev/null | jq '.rpm'
```

### Send to a web API:
```bash
python3 cli_obd_loop.py 2>/dev/null | while read line; do
    curl -X POST -H "Content-Type: application/json" \
         -d "$line" http://localhost:8000/api/readings
done
```

---

## 🛠️ Troubleshooting

### "OBD adapter not detected"

1. Check if device exists: `ls -la /dev/rfcomm0`
2. If not, bind it: `sudo rfcomm bind 0 00:1D:A5:09:2E:B3 1`
3. Check Bluetooth: `hcitool scan` and `hcitool dev`

### "Adapter found, but car ignition is OFF"

- Turn your car's ignition to the ON position
- Engine doesn't need to be running for most sensors
- RPM will show 0 until engine starts

### Connection hangs or times out

- Release and rebind rfcomm:
  ```bash
  sudo rfcomm release 0
  sudo rfcomm bind 0 00:1D:A5:09:2E:B3 1
  ```
- Check if another program is using `/dev/rfcomm0`
- Try unplugging and replugging the ELM327 adapter

### All sensor values are `null`

- Engine might be off (RPM will be 0 or null)
- Some PIDs may not be supported by your vehicle
- Check adapter compatibility with your car's OBD protocol

---

## 🚀 Next Steps

This CLI loop is designed to be a **simple foundation** for building an API or dashboard:

1. **FastAPI Integration**: Wrap this in a web server to expose HTTP endpoints
2. **Database Logging**: Store readings in SQLite/PostgreSQL for historical analysis
3. **WebSocket Streaming**: Push real-time JSON to web dashboards
4. **Alerts & Monitoring**: Trigger notifications based on sensor thresholds

---

## 📝 Notes

- The script uses `fast=True` for quicker connections (assumes protocol is already known)
- Connection failures automatically trigger reconnection after 5 consecutive errors
- All output is unbuffered for real-time piping
- Handles `Ctrl-C` gracefully and closes the OBD connection cleanly

---

**Happy logging! 🚗📊**
