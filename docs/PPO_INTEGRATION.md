# PPO Policy Integration with ASVSim

This document describes how to integrate trained PPO policies from the AMS-DRL-Pursuit-Evasion project with ASVSim for visualization in Unreal Engine.

## Overview

The integration allows you to:
- Load a trained PPO policy (runner_s1_v2)
- Run pursuit-evasion scenarios in ASVSim's Unreal Engine environment
- Visualize the runner drone evading two chaser drones while reaching a target

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         ASVSim (Unreal Engine)                  │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐        │
│  │ Drone1  │   │ Drone2  │   │ Drone3  │   │ Target  │        │
│  │ (Runner)│   │(Chaser0)│   │(Chaser1)│   │  Pos    │        │
│  └────┬────┘   └────┬────┘   └────┬────┘   └─────────┘        │
│       │             │             │                            │
└───────┼─────────────┼─────────────┼────────────────────────────┘
        │             │             │
        ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│              PursuitEvasionController (Python)                  │
│                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │ Observation      │    │ Action           │                  │
│  │ Computation      │    │ Application      │                  │
│  │ (15D)            │    │ (Velocity Cmds)  │                  │
│  └────────┬─────────┘    └────────▲─────────┘                  │
│           │                       │                            │
│           ▼                       │                            │
│  ┌────────────────────────────────┴─────────┐                  │
│  │           PPO Policy (SB3)               │                  │
│  │         (runner_s1_v2/model.zip)         │                  │
│  └──────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
```

## Observation Space (15D)

The runner's observation is a 15-dimensional vector:

| Index | Name | Description |
|-------|------|-------------|
| 0-2 | `target_relative` | Relative position to target (x, y, z) |
| 3-5 | `chaser_0_relative` | Relative position to chaser 0 (x, y, z) |
| 6-8 | `chaser_1_relative` | Relative position to chaser 1 (x, y, z) |
| 9-14 | `walls` | Distance to walls (+x, -x, +y, -y, +z, -z) |

### Observation Computation

```python
def compute_observation(self) -> np.ndarray:
    # Get positions
    runner_pos = self.get_drone_position("Drone1")
    chaser0_pos = self.get_drone_position("Drone2")
    chaser1_pos = self.get_drone_position("Drone3")
    target_pos = self.config.target_pos

    # Relative positions (from runner's perspective)
    target_rel = target_pos - runner_pos
    chaser0_rel = chaser0_pos - runner_pos
    chaser1_rel = chaser1_pos - runner_pos

    # Wall distances
    walls = np.array([
        arena_max[0] - runner_pos[0],  # +x (right wall)
        runner_pos[0] - arena_min[0],  # -x (left wall)
        arena_max[1] - runner_pos[1],  # +y (front wall)
        runner_pos[1] - arena_min[1],  # -y (back wall)
        runner_pos[2] - arena_max[2],  # +z (ceiling, NED)
        arena_min[2] - runner_pos[2],  # -z (floor)
    ])

    return np.concatenate([target_rel, chaser0_rel, chaser1_rel, walls])
```

## Action Space (4D)

The policy outputs a 4-dimensional action vector:

| Index | Name | Range | Description |
|-------|------|-------|-------------|
| 0 | `vx` | [-1, 1] | X velocity command |
| 1 | `vy` | [-1, 1] | Y velocity command |
| 2 | `vz` | [-1, 1] | Z velocity command |
| 3 | `wz` | [-1, 1] | Yaw rate (typically unused) |

Actions are scaled by `max_speed` (5.0 m/s) before being applied.

## Roles

### Runner (Drone1)
- Controlled by the trained PPO policy
- Objective: Reach the target position while avoiding chasers
- Speed: 100% of max_speed (5.0 m/s)

### Chasers (Drone2, Drone3)
- Controlled by heuristic pursuit
- Objective: Catch the runner
- Speed: 70% of runner speed (3.5 m/s)
- Strategy: Direct pursuit toward runner position

## Episode Termination

An episode ends when:
1. **Runner Success**: Runner reaches within 2.0m of target
2. **Chaser Success**: Any chaser gets within 1.5m of runner
3. **Wall Collision**: Runner goes out of arena bounds
4. **Timeout**: 500 steps reached

## Usage

### 1. Configure ASVSim

Copy the pursuit-evasion config to your AirSim settings:

```bash
cp configs/pursuit_evasion.json ~/Documents/AirSim/settings.json
```

Or on Windows: `C:\Users\<username>\Documents\AirSim\settings.json`

### 2. Start Unreal Engine

Launch the Blocks environment and press Play.

### 3. Run the Script

```bash
# Activate conda environment
conda activate asvsim

# Run pursuit-evasion
cd scripts
python pursuit_evasion_ppo.py --ip wsl --episodes 5
```

### Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--ip` | localhost | AirSim server IP. Use 'wsl' for auto-detect |
| `--episodes` | 5 | Number of episodes to run |
| `--policy` | auto-detect | Path to PPO model.zip |
| `--no-prompts` | False | Non-interactive mode |

## Training Background

The PPO policy was trained using the AMS-DRL (Asynchronous Multi-Stage Deep Reinforcement Learning) approach:

### Training Stages

1. **S0**: Runner learns target-seeking (no chasers)
   - 300,000 timesteps
   - Converged to 98% success rate

2. **S1**: Runner vs heuristic chasers at 70% speed
   - 820,000 timesteps
   - Converged to 90% success rate
   - This is the `runner_s1_v2` policy

### Hyperparameters

| Parameter | Value |
|-----------|-------|
| Algorithm | PPO |
| Learning Rate | 3e-4 (linear decay) |
| Batch Size | 64 |
| N Steps | 2048 |
| N Epochs | 10 |
| Entropy Coefficient | 0.02 |
| PPO Clip | 0.2 |
| GAE λ | 0.95 |
| Discount γ | 0.99 |

## Coordinate System Notes

### ASVSim (NED)
- X: North (forward)
- Y: East (right)
- Z: Down (negative = up)

### Arena Configuration
- Size: 30m × 30m × 10m height
- Min bounds: (0, 0, -15)
- Max bounds: (30, 30, -5)
- Target position: (25, 25, -10)

## Files

| File | Description |
|------|-------------|
| `scripts/pursuit_evasion_ppo.py` | Main integration script |
| `configs/pursuit_evasion.json` | ASVSim settings with 3 drones |
| `docs/PPO_INTEGRATION.md` | This documentation |

## Dependencies

```bash
pip install stable-baselines3 torch numpy
```

## References

- [AMS-DRL Paper](https://www.alphaxiv.org/abs/2304.03443): "Learning Multi-Pursuit Evasion for Safe Targeted Navigation of Drones"
- [stable-baselines3](https://stable-baselines3.readthedocs.io/): PPO implementation
- [ASVSim](https://github.com/Cosys-Lab/Cosys-AirSim): Simulator framework
