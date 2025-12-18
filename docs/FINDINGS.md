# Key Findings

Documentation of important discoveries and learnings while working with ASVSIM.

---

## Networking

### WSL2 to Windows Simulator Connection

**Date:** 2024-12

**Problem:** When running Python scripts from WSL2 while the ASVSIM simulator runs on Windows, connection fails with `ECONNREFUSED` errors.

**Root Cause:**
- WSL2 runs in a lightweight VM with its own network stack
- `localhost` in WSL refers to WSL's loopback, not Windows
- By default, ASVSIM listens only on `127.0.0.1` (Windows localhost)

**Solution:**

1. **Configure ASVSIM to listen on all interfaces:**

   Add to `settings.json`:
   ```json
   {
       "LocalHostIp": "0.0.0.0"
   }
   ```

2. **Connect to Windows host IP from WSL:**

   The Windows host is reachable at the default gateway IP:
   ```bash
   ip route show | grep default | awk '{print $3}'
   # Typically returns something like 172.17.144.1
   ```

3. **Use the `--ip wsl` flag** in our scripts for auto-detection:
   ```bash
   python multi_agent_flight_pattern.py --ip wsl
   ```

**Key Insight:** WSL2 and Windows share a virtual network bridge. Windows services must bind to `0.0.0.0` to be accessible from WSL.

### Windows Firewall Configuration

**Date:** 2024-12

**Problem:** Even with `LocalHostIp: "0.0.0.0"`, connections from WSL may be blocked by Windows Firewall.

**Solution:** Add an inbound firewall rule (run PowerShell as Administrator):
```powershell
New-NetFirewallRule -DisplayName "AirSim" -Direction Inbound -Port 41451 -Protocol TCP -Action Allow
```

---

## Multi-Agent Control

### Parallel Drone Control Pattern

**Date:** 2024-12

**Finding:** ASVSIM supports true parallel control of multiple vehicles through async operations.

**Pattern:**
```python
# Launch operations in parallel
f1 = client.takeoffAsync(vehicle_name="Drone1")
f2 = client.takeoffAsync(vehicle_name="Drone2")
f3 = client.takeoffAsync(vehicle_name="Drone3")

# Wait for all to complete
f1.join()
f2.join()
f3.join()
```

**Key Points:**
- All API methods accept a `vehicle_name` parameter
- Async methods return futures that can be joined later
- Parallel execution provides significant performance gains for multi-agent scenarios

### Vehicle Configuration

**Finding:** Vehicles must be pre-configured in `settings.json` with unique names and spawn positions.

```json
{
    "Vehicles": {
        "Drone1": {"VehicleType": "SimpleFlight", "X": 0, "Y": 0, "Z": -2},
        "Drone2": {"VehicleType": "SimpleFlight", "X": 5, "Y": 0, "Z": -2}
    }
}
```

**Note:** The `Z` value is negative because ASVSIM uses NED (North-East-Down) coordinates where negative Z is up.

---

## Coordinate System

### NED Coordinates

**Finding:** ASVSIM uses NED (North-East-Down) coordinate system:
- **X**: North (forward)
- **Y**: East (right)
- **Z**: Down (negative values = up)

**Implication:** When specifying altitudes, use negative values:
```python
# Fly to 10 meters altitude
client.moveToPositionAsync(x=0, y=0, z=-10, velocity=5)
```

---

## API & RPC

### Connection Settings

**Finding:** Default RPC connection parameters:
- **Port:** 41451
- **Timeout:** 3600 seconds
- **IP:** 127.0.0.1 (configurable)

```python
client = airsim.MultirotorClient(ip="172.17.144.1", port=41451)
```

### msgpack-rpc Dependency

**Finding:** The `cosysairsim` package requires `msgpack-rpc-python` which depends on `tornado<5`. There can be dependency conflicts with newer tornado versions.

**Solution:** Install `msgpack-rpc-python` explicitly:
```bash
pip install msgpack-rpc-python
```

---

## Performance

### Smooth Circular Motion

**Finding:** For smooth circular/orbital motion, use velocity commands with small time steps rather than position commands.

```python
# Smoother approach - velocity control
client.moveByVelocityZAsync(vx, vy, altitude, duration=0.5)

# Less smooth - position jumps
client.moveToPositionAsync(x, y, z, velocity)
```

---

## Environment

### Blocks Environment

**Finding:** The Blocks environment is the recommended lightweight environment for testing:
- Fast loading times
- Simple geometry
- Good for algorithm development and debugging

**Location:** `ASVSim/Unreal/Environments/Blocks`

---

*Add new findings as they are discovered...*
