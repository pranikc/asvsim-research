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

Copy a config from `configs/` to your AirSim settings location:
- Windows: `C:\Users\<username>\Documents\AirSim\settings.json`

### 3. Run experiments

```bash
# Activate environment
conda activate asvsim

# Run multi-agent flight pattern demo
cd scripts
python multi_agent_flight_pattern.py --pattern circle --ip wsl
```

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

## Documentation

- [Key Findings](docs/FINDINGS.md) - Important discoveries and learnings
- [Caveats & Workarounds](docs/CAVEATS.md) - Known issues and solutions
- [Setup Guide](docs/SETUP.md) - Detailed environment setup

## Related Resources

- [ASVSIM Documentation](https://cosys-lab.github.io/intro/)
- [Original Cosys-AirSim](https://github.com/Cosys-Lab/Cosys-AirSim)
- [Microsoft AirSim (archived)](https://github.com/microsoft/AirSim)
