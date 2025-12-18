# Caveats & Workarounds

Known issues, limitations, and their workarounds when working with ASVSIM.

---

## Running from WSL

### Non-Interactive Mode Required

**Issue:** When running scripts from WSL, `airsim.wait_key()` fails with `termios.error: (25, 'Inappropriate ioctl for device')` because WSL terminals don't support the terminal control operations.

**Error:**
```
termios.error: (25, 'Inappropriate ioctl for device')
```

**Workaround:** Use `--no-prompts` flag to run in non-interactive mode:
```bash
python multi_agent_flight_pattern.py --pattern circle --ip wsl --no-prompts
```

---

## Environment Setup

### WSL2 Cannot Connect to Windows Simulator

**Issue:** Python scripts in WSL2 fail to connect to ASVSIM running on Windows.

**Error:**
```
WARNING:tornado.general:Connect error on fd 6: ECONNREFUSED
msgpackrpc.error.TransportError: Retry connection over the limit
```

**Workaround:**

1. Add `"LocalHostIp": "0.0.0.0"` to your `settings.json`
2. Connect using the Windows host IP instead of localhost
3. Use `--ip wsl` flag in scripts that support it

See [FINDINGS.md](FINDINGS.md#wsl2-to-windows-simulator-connection) for details.

---

### Conda Environment in WSL vs Windows

**Issue:** Conda installed in WSL is not accessible from Windows PowerShell and vice versa.

**Workaround:**

Option 1: Run everything from WSL:
```bash
wsl
conda activate asvsim
python script.py --ip wsl
```

Option 2: Install Miniconda separately on Windows for PowerShell usage.

---

## Dependencies

### tornado Version Conflict

**Issue:** `cosysairsim` may install `rpc-msgpack` which requires `tornado>=6.1`, but `msgpack-rpc-python` requires `tornado<5`.

**Error:**
```
ModuleNotFoundError: No module named 'msgpackrpc'
```

**Workaround:**
```bash
pip uninstall rpc-msgpack -y
pip install msgpack-rpc-python
```

The `msgpack-rpc-python` package provides the correct `msgpackrpc` module.

---

## Simulation

### Vehicles Must Be Pre-Configured

**Issue:** Vehicles cannot be dynamically created without being defined in `settings.json` first (with some exceptions using `simAddVehicle`).

**Workaround:** Pre-define all vehicles you plan to use in `settings.json`:
```json
{
    "Vehicles": {
        "Drone1": {"VehicleType": "SimpleFlight", "X": 0, "Y": 0, "Z": -2},
        "Drone2": {"VehicleType": "SimpleFlight", "X": 5, "Y": 0, "Z": -2}
    }
}
```

---

### Negative Z for Altitude

**Issue:** Forgetting that ASVSIM uses NED coordinates where negative Z is up.

**Symptom:** Drone flies into the ground or doesn't take off properly.

**Workaround:** Always use negative Z values for altitude:
```python
# WRONG - this goes underground
client.moveToPositionAsync(0, 0, 10, 5)

# CORRECT - 10 meters altitude
client.moveToPositionAsync(0, 0, -10, 5)
```

---

### Simulator Must Be Running First

**Issue:** Python scripts fail if the Unreal Engine simulator isn't running.

**Workaround:** Always start the simulator (press Play in Unreal Editor or run the packaged executable) before running Python scripts.

---

## API Behavior

### API Control Must Be Enabled

**Issue:** Commands are ignored if API control isn't enabled for the vehicle.

**Workaround:** Always enable API control before sending commands:
```python
client.enableApiControl(True, "Drone1")
client.armDisarm(True, "Drone1")
```

---

### Async Operations Need join()

**Issue:** Async operations may not complete if the script exits before they finish.

**Workaround:** Always call `.join()` on futures:
```python
future = client.takeoffAsync()
future.join()  # Wait for completion
```

---

### Hover After Position Commands

**Issue:** Drone may drift slightly after reaching a position.

**Workaround:** Call `hoverAsync()` after position commands if precise hovering is needed:
```python
client.moveToPositionAsync(x, y, z, velocity).join()
client.hoverAsync().join()
time.sleep(1)  # Let it stabilize
```

---

## Performance

### High CPU Usage in Loops

**Issue:** Tight control loops without delays cause high CPU usage.

**Workaround:** Add small delays in control loops:
```python
while running:
    # Control logic here
    time.sleep(0.1)  # 10 Hz update rate is usually sufficient
```

---

*Add new caveats as they are discovered...*
