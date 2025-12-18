# Setup Guide

Detailed instructions for setting up the ASVSIM research environment.

## Prerequisites

### Required Software

1. **ASVSIM** - Built from source or pre-built binaries
   - Repository: https://github.com/Cosys-Lab/Cosys-AirSim
   - Includes Unreal Engine environments

2. **Python 3.11+** with Miniconda/Anaconda

3. **WSL2** (recommended for Linux-based development on Windows)

---

## Installation

### Step 1: Install Miniconda (WSL)

```bash
# Download and install
curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o /tmp/miniconda.sh
bash /tmp/miniconda.sh -b -p $HOME/miniconda3

# Initialize
$HOME/miniconda3/bin/conda init bash

# Accept terms of service
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

# Restart shell or source bashrc
source ~/.bashrc
```

### Step 2: Create Conda Environment

```bash
# Create environment
conda create -n asvsim python=3.11 -y

# Activate
conda activate asvsim

# Install dependencies
pip install msgpack-rpc-python numpy opencv-python pillow gymnasium
```

### Step 3: Install cosysairsim

```bash
# Install from your ASVSIM installation (editable mode)
pip install -e /mnt/c/Users/<username>/Desktop/ASVSim/PythonClient
```

### Step 4: Configure ASVSIM Settings

Create/edit `C:\Users\<username>\Documents\AirSim\settings.json`:

```json
{
    "SeeDocsAt": "https://cosys-lab.github.io/settings/",
    "SettingsVersion": 1.2,
    "SimMode": "Multirotor",
    "LocalHostIp": "0.0.0.0",
    "Vehicles": {
        "Drone1": {"VehicleType": "SimpleFlight", "X": 0, "Y": 0, "Z": -2},
        "Drone2": {"VehicleType": "SimpleFlight", "X": 3, "Y": 3, "Z": -2},
        "Drone3": {"VehicleType": "SimpleFlight", "X": 3, "Y": -3, "Z": -2},
        "Drone4": {"VehicleType": "SimpleFlight", "X": 6, "Y": 6, "Z": -2},
        "Drone5": {"VehicleType": "SimpleFlight", "X": 6, "Y": -6, "Z": -2}
    }
}
```

**Important Settings:**
- `LocalHostIp: "0.0.0.0"` - Required for WSL connectivity
- `SimMode: "Multirotor"` - For drone simulation
- `Vehicles` - Define all drones you want to control

---

## Running Experiments

### 1. Start the Simulator

- Open Unreal Engine with the Blocks project
- Press **Play** to start the simulation
- You should see the configured drones spawn

### 2. Run Python Scripts

From WSL:
```bash
# Activate environment
conda activate asvsim

# Navigate to scripts
cd /mnt/c/Users/<username>/Desktop/asvsim-research/scripts

# Run with WSL networking
python multi_agent_flight_pattern.py --pattern circle --ip wsl
```

### 3. Available Flight Patterns

```bash
# All patterns
python multi_agent_flight_pattern.py --ip wsl

# Specific patterns
python multi_agent_flight_pattern.py --pattern v --ip wsl
python multi_agent_flight_pattern.py --pattern line --ip wsl
python multi_agent_flight_pattern.py --pattern circle --ip wsl
python multi_agent_flight_pattern.py --pattern waypoints --ip wsl
python multi_agent_flight_pattern.py --pattern spiral --ip wsl

# Fewer drones
python multi_agent_flight_pattern.py --pattern circle --drones 3 --ip wsl
```

---

## Troubleshooting

### Connection Refused

```
msgpackrpc.error.TransportError: Retry connection over the limit
```

**Solutions:**
1. Ensure simulator is running (press Play in Unreal)
2. Check `LocalHostIp` is set to `"0.0.0.0"` in settings.json
3. Restart the simulator after changing settings
4. Use `--ip wsl` flag when running from WSL

### Module Not Found: msgpackrpc

```
ModuleNotFoundError: No module named 'msgpackrpc'
```

**Solution:**
```bash
pip install msgpack-rpc-python
```

### Drones Not Appearing

**Solutions:**
1. Check `settings.json` is in correct location
2. Verify JSON syntax is valid
3. Ensure `SimMode` is set to `"Multirotor"`
4. Restart the simulator after changes

---

## Directory Reference

| Path | Description |
|------|-------------|
| `~/Documents/AirSim/settings.json` | Windows settings location |
| `/mnt/c/Users/.../Documents/AirSim/` | Same location from WSL |
| `ASVSim/PythonClient/cosysairsim/` | Python API source |
| `ASVSim/Unreal/Environments/Blocks/` | Blocks environment |
