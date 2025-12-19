# ASVSIM Research

Internal research and experiments using the [ASVSIM](https://github.com/Cosys-Lab/Cosys-AirSim) (Autonomous Surface Vehicle Simulator) framework.

## Overview

This repository contains:
- Multi-agent drone/vehicle flight patterns and experiments
- Configuration templates for various simulation scenarios
- Documentation of findings, caveats, and best practices
- Reusable scripts and utilities for ASVSIM development

## Prerequisites

- **ASVSIM** installed with Unreal Engine (Blocks environment recommended for testing)
- **Python 3.11+** with conda environment
- **WSL2** (if running Python from Linux while simulator runs on Windows)

## Quick Start

### 1. Set up the conda environment

```bash
# From WSL
conda create -n asvsim python=3.11 -y
conda activate asvsim

# Install dependencies
pip install msgpack-rpc-python numpy opencv-python pillow gymnasium

# Install cosysairsim from your ASVSIM installation
pip install -e /path/to/ASVSim/PythonClient
```

### 2. Configure ASVSIM settings

Copy the config from `configs/multi_drone.json` to your AirSim settings location:
- Windows: `C:\Users\<username>\Documents\AirSim\settings.json`

**Important:** The config includes `"LocalHostIp": "0.0.0.0"` which is required for WSL connectivity.

### 3. Run experiments

```bash
# Activate environment
conda activate asvsim

# Run multi-agent flight pattern demo (non-interactive mode for WSL)
cd scripts
python multi_agent_flight_pattern.py --pattern circle --ip wsl --no-prompts
```

## Multi-Agent Flight Patterns

The `multi_agent_flight_pattern.py` script supports several coordinated flight patterns:

| Pattern | Description |
|---------|-------------|
| `v` | V-formation flight following waypoints |
| `line` | Line formation moving together |
| `circle` | Circular orbit around a center point |
| `waypoints` | Synchronized convergence on waypoints |
| `spiral` | Expanding spiral from center outward |
| `all` | Run all patterns sequentially |

### Usage

```bash
# Run specific pattern with 5 drones
python multi_agent_flight_pattern.py --pattern circle --ip wsl --no-prompts

# Run with fewer drones
python multi_agent_flight_pattern.py --pattern v --drones 3 --ip wsl --no-prompts

# Run all patterns
python multi_agent_flight_pattern.py --pattern all --ip wsl --no-prompts

# Interactive mode (waits for key presses between steps)
python multi_agent_flight_pattern.py --pattern circle --ip wsl
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `--pattern` | Flight pattern: `v`, `line`, `circle`, `waypoints`, `spiral`, `all` |
| `--drones` | Number of drones: 2-5 (default: 5) |
| `--ip` | Simulator IP. Use `wsl` to auto-detect Windows host from WSL |
| `--no-prompts` | Non-interactive mode, no key press waits |

## Repository Structure

```
asvsim-research/
├── README.md                 # This file
├── docs/
│   ├── FINDINGS.md          # Key findings and learnings
│   ├── CAVEATS.md           # Known issues and workarounds
│   └── SETUP.md             # Detailed setup instructions
├── configs/
│   └── multi_drone.json     # Multi-drone configuration template
├── scripts/
│   └── multi_agent_flight_pattern.py  # Multi-agent flight patterns
└── examples/
    └── ...                  # Example notebooks and scripts
```

## Key Findings

### WSL2 to Windows Connectivity

When running Python from WSL2 while the simulator runs on Windows:

1. **Set `LocalHostIp` to `0.0.0.0`** in settings.json (allows external connections)
2. **Use `--ip wsl`** flag to auto-detect Windows host IP
3. **Add firewall rule** if connection is blocked:
   ```powershell
   New-NetFirewallRule -DisplayName "AirSim" -Direction Inbound -Port 41451 -Protocol TCP -Action Allow
   ```

See [docs/FINDINGS.md](docs/FINDINGS.md) for more details.

## Pursuit-Evasion with PPO

Run trained PPO policies from [AMS-DRL-Pursuit-Evasion](https://github.com/SkyrunAI/AMS-DRL-Pursuit-Evasion) in ASVSim:

```bash
# Use the 3-drone config
cp configs/pursuit_evasion.json ~/Documents/AirSim/settings.json

# Run pursuit-evasion demo
python scripts/pursuit_evasion_ppo.py --ip wsl --episodes 5
```

**Scenario:**
- **Runner (Drone1)**: PPO-controlled evader, tries to reach target
- **Chasers (Drone2, Drone3)**: Heuristic pursuers at 70% speed

See [docs/PPO_INTEGRATION.md](docs/PPO_INTEGRATION.md) for details.

## Documentation

- [Key Findings](docs/FINDINGS.md) - Important discoveries and learnings
- [Caveats & Workarounds](docs/CAVEATS.md) - Known issues and solutions
- [Setup Guide](docs/SETUP.md) - Detailed environment setup
- [PPO Integration](docs/PPO_INTEGRATION.md) - Pursuit-evasion with trained policies

## Related Resources

- [ASVSIM Documentation](https://cosys-lab.github.io/intro/)
- [Original Cosys-AirSim](https://github.com/Cosys-Lab/Cosys-AirSim)
- [Microsoft AirSim (archived)](https://github.com/microsoft/AirSim)
