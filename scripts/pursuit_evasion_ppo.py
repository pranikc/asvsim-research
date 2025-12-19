"""
Pursuit-Evasion PPO Integration for ASVSim
==========================================

This script integrates the trained PPO policy from AMS-DRL-Pursuit-Evasion
with ASVSim to visualize multi-agent pursuit-evasion in Unreal Engine.

Roles:
- Runner (Drone1): Evader controlled by PPO policy, tries to reach target
- Chaser0 (Drone2): Pursuer using heuristic pursuit
- Chaser1 (Drone3): Pursuer using heuristic pursuit

Observation Space (15D):
- target_relative [0-2]: Relative position to target (x, y, z)
- chaser_0_relative [3-5]: Relative position to chaser 0
- chaser_1_relative [6-8]: Relative position to chaser 1
- walls [9-14]: Distance to arena walls (+x, -x, +y, -y, +z, -z)

Action Space (4D):
- vx, vy, vz, wz: Velocity commands in [-1, 1]

Usage:
    python pursuit_evasion_ppo.py --ip wsl --no-prompts
"""

import os
import sys
import time
import argparse
import numpy as np

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import setup_path
import cosysairsim as airsim


def get_wsl_host_ip():
    """Get the Windows host IP when running from WSL."""
    try:
        import subprocess
        result = subprocess.run(
            ["ip", "route", "show"],
            capture_output=True, text=True
        )
        for line in result.stdout.split('\n'):
            if 'default' in line:
                return line.split()[2]
    except:
        pass
    return ""


class PursuitEvasionConfig:
    """Configuration for the pursuit-evasion scenario."""

    # Arena dimensions (meters) - matching the training environment
    # ASVSim uses NED coordinates, so we'll work in a similar space
    arena_min = np.array([0.0, 0.0, -15.0])  # x, y, z (z negative = up in NED)
    arena_max = np.array([30.0, 30.0, -5.0])   # 30x30m arena, 10m height range

    # Target position (runner tries to reach this)
    target_pos = np.array([25.0, 25.0, -10.0])

    # Speed settings
    max_speed = 5.0  # m/s for runner
    chaser_speed_ratio = 0.7  # Chasers at 70% of runner speed

    # Thresholds
    target_radius = 2.0  # Success if runner within this distance
    collision_radius = 1.5  # Collision if drones within this distance

    # Episode settings
    max_steps = 500
    dt = 0.1  # Control timestep (seconds)


class PursuitEvasionController:
    """
    Controls the pursuit-evasion game in ASVSim using trained PPO policy.
    """

    def __init__(self, policy_path: str, ip: str = ""):
        """
        Initialize the controller.

        Args:
            policy_path: Path to the PPO model.zip file
            ip: IP address of AirSim server
        """
        self.config = PursuitEvasionConfig()

        # Load PPO model
        self._load_policy(policy_path)

        # Connect to ASVSim
        print(f"Connecting to ASVSim at {ip if ip else 'localhost'}...")
        self.client = airsim.MultirotorClient(ip=ip)
        self.client.confirmConnection()
        print("Connected!")

        # Drone names
        self.runner_name = "Drone1"
        self.chaser_names = ["Drone2", "Drone3"]
        self.all_drones = [self.runner_name] + self.chaser_names

        # Episode tracking
        self.step_count = 0
        self.episode_count = 0
        self.runner_wins = 0

    def _load_policy(self, policy_path: str):
        """Load the trained PPO policy."""
        try:
            from stable_baselines3 import PPO
            print(f"Loading PPO policy from {policy_path}...")
            self.model = PPO.load(policy_path)
            print("Policy loaded successfully!")
        except ImportError:
            print("ERROR: stable_baselines3 not installed.")
            print("Install with: pip install stable-baselines3")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR loading policy: {e}")
            sys.exit(1)

    def enable_control(self):
        """Enable API control for all drones."""
        for name in self.all_drones:
            self.client.enableApiControl(True, name)
            self.client.armDisarm(True, name)
        print("All drones armed and API control enabled")

    def disable_control(self):
        """Disable API control for all drones."""
        for name in self.all_drones:
            self.client.armDisarm(False, name)
            self.client.enableApiControl(False, name)

    def get_drone_position(self, drone_name: str) -> np.ndarray:
        """Get the current position of a drone."""
        state = self.client.getMultirotorState(vehicle_name=drone_name)
        pos = state.kinematics_estimated.position
        return np.array([pos.x_val, pos.y_val, pos.z_val])

    def compute_observation(self) -> np.ndarray:
        """
        Compute the 15D observation for the runner.

        Returns:
            15D observation: [target_rel(3), chaser0_rel(3), chaser1_rel(3), walls(6)]
        """
        # Get positions
        runner_pos = self.get_drone_position(self.runner_name)
        chaser0_pos = self.get_drone_position(self.chaser_names[0])
        chaser1_pos = self.get_drone_position(self.chaser_names[1])
        target_pos = self.config.target_pos

        # Relative positions (from runner's perspective)
        target_rel = target_pos - runner_pos
        chaser0_rel = chaser0_pos - runner_pos
        chaser1_rel = chaser1_pos - runner_pos

        # Wall distances (distance to arena boundaries)
        # [+x, -x, +y, -y, +z, -z]
        walls = np.array([
            self.config.arena_max[0] - runner_pos[0],  # +x (right wall)
            runner_pos[0] - self.config.arena_min[0],  # -x (left wall)
            self.config.arena_max[1] - runner_pos[1],  # +y (front wall)
            runner_pos[1] - self.config.arena_min[1],  # -y (back wall)
            runner_pos[2] - self.config.arena_max[2],  # +z (ceiling, remember NED)
            self.config.arena_min[2] - runner_pos[2],  # -z (floor)
        ])

        # Normalize walls to reasonable range (clip negative values)
        walls = np.clip(walls, 0, 50)

        # Concatenate observation
        obs = np.concatenate([target_rel, chaser0_rel, chaser1_rel, walls])
        return obs.astype(np.float32)

    def get_runner_action(self, obs: np.ndarray) -> np.ndarray:
        """
        Get action from PPO policy for the runner.

        Args:
            obs: 15D observation

        Returns:
            4D action [vx, vy, vz, wz] in [-1, 1]
        """
        action, _ = self.model.predict(obs, deterministic=True)
        return action

    def get_chaser_action(self, chaser_name: str) -> np.ndarray:
        """
        Get heuristic pursuit action for a chaser.
        Simple direct pursuit toward the runner.

        Args:
            chaser_name: Name of the chaser drone

        Returns:
            4D action [vx, vy, vz, wz] in [-1, 1]
        """
        chaser_pos = self.get_drone_position(chaser_name)
        runner_pos = self.get_drone_position(self.runner_name)

        # Direction to runner
        direction = runner_pos - chaser_pos
        dist = np.linalg.norm(direction)

        if dist > 0.1:
            direction = direction / dist
        else:
            direction = np.zeros(3)

        # Action at reduced speed
        speed_ratio = self.config.chaser_speed_ratio
        action = np.array([
            direction[0] * speed_ratio,
            direction[1] * speed_ratio,
            direction[2] * speed_ratio,
            0.0  # No yaw
        ], dtype=np.float32)

        return action

    def apply_action(self, drone_name: str, action: np.ndarray, is_runner: bool = False):
        """
        Apply velocity action to a drone.

        Args:
            drone_name: Name of the drone
            action: [vx, vy, vz, wz] in [-1, 1]
            is_runner: Whether this is the runner (uses full speed)
        """
        # Scale to actual velocity
        speed = self.config.max_speed if is_runner else (self.config.max_speed * self.config.chaser_speed_ratio)
        vx = action[0] * speed
        vy = action[1] * speed
        vz = action[2] * speed

        # Apply velocity command
        self.client.moveByVelocityAsync(
            vx, vy, vz,
            duration=self.config.dt,
            vehicle_name=drone_name
        )

    def check_termination(self) -> tuple:
        """
        Check if the episode should terminate.

        Returns:
            (terminated, outcome): outcome is "runner_success", "chaser_success", "timeout", or None
        """
        runner_pos = self.get_drone_position(self.runner_name)

        # Check runner reached target
        target_dist = np.linalg.norm(runner_pos - self.config.target_pos)
        if target_dist < self.config.target_radius:
            return True, "runner_success"

        # Check collision with chasers
        for chaser_name in self.chaser_names:
            chaser_pos = self.get_drone_position(chaser_name)
            dist = np.linalg.norm(runner_pos - chaser_pos)
            if dist < self.config.collision_radius:
                return True, "chaser_success"

        # Check runner out of bounds
        if (np.any(runner_pos[:2] < self.config.arena_min[:2]) or
            np.any(runner_pos[:2] > self.config.arena_max[:2]) or
            runner_pos[2] > self.config.arena_min[2] or  # Below floor (NED)
            runner_pos[2] < self.config.arena_max[2]):   # Above ceiling (NED)
            return True, "chaser_success"  # Out of bounds counts as chaser win

        # Check timeout
        if self.step_count >= self.config.max_steps:
            return True, "timeout"

        return False, None

    def reset_positions(self):
        """Reset drones to starting positions."""
        print("\nResetting positions...")

        # Define starting positions
        start_positions = {
            self.runner_name: airsim.Vector3r(5, 5, -10),
            self.chaser_names[0]: airsim.Vector3r(15, 5, -10),
            self.chaser_names[1]: airsim.Vector3r(5, 15, -10),
        }

        # Teleport each drone
        for name, pos in start_positions.items():
            pose = airsim.Pose(pos, airsim.Quaternionr(0, 0, 0, 1))
            self.client.simSetVehiclePose(pose, True, vehicle_name=name)

        time.sleep(0.5)  # Let physics settle
        self.step_count = 0

    def run_episode(self, verbose: bool = True) -> str:
        """
        Run a single episode of pursuit-evasion.

        Returns:
            Outcome: "runner_success", "chaser_success", or "timeout"
        """
        self.episode_count += 1
        self.reset_positions()

        if verbose:
            print(f"\n{'='*50}")
            print(f"Episode {self.episode_count}")
            print(f"{'='*50}")

        terminated = False
        outcome = None

        while not terminated:
            self.step_count += 1

            # Get observation
            obs = self.compute_observation()

            # Get actions
            runner_action = self.get_runner_action(obs)
            chaser0_action = self.get_chaser_action(self.chaser_names[0])
            chaser1_action = self.get_chaser_action(self.chaser_names[1])

            # Apply actions
            self.apply_action(self.runner_name, runner_action, is_runner=True)
            self.apply_action(self.chaser_names[0], chaser0_action)
            self.apply_action(self.chaser_names[1], chaser1_action)

            # Wait for timestep
            time.sleep(self.config.dt)

            # Check termination
            terminated, outcome = self.check_termination()

            # Progress update
            if verbose and self.step_count % 50 == 0:
                runner_pos = self.get_drone_position(self.runner_name)
                target_dist = np.linalg.norm(runner_pos - self.config.target_pos)
                print(f"Step {self.step_count}: Target dist = {target_dist:.1f}m")

        # Update stats
        if outcome == "runner_success":
            self.runner_wins += 1

        if verbose:
            win_rate = 100 * self.runner_wins / self.episode_count
            print(f"\nOutcome: {outcome} ({self.step_count} steps)")
            print(f"Runner wins: {self.runner_wins}/{self.episode_count} ({win_rate:.0f}%)")

        return outcome

    def run(self, num_episodes: int = 10, verbose: bool = True):
        """
        Run multiple episodes.

        Args:
            num_episodes: Number of episodes to run
            verbose: Print progress updates
        """
        print("\n" + "="*60)
        print("Pursuit-Evasion PPO Demo")
        print("Runner: PPO Policy | Chasers: Heuristic Pursuit")
        print("="*60)

        self.enable_control()

        # Takeoff all drones
        print("\nTaking off...")
        futures = []
        for name in self.all_drones:
            f = self.client.takeoffAsync(vehicle_name=name)
            futures.append(f)
        for f in futures:
            f.join()

        time.sleep(1)

        try:
            for ep in range(num_episodes):
                self.run_episode(verbose=verbose)
                time.sleep(1)  # Pause between episodes
        except KeyboardInterrupt:
            print("\nInterrupted by user")

        # Land all drones
        print("\nLanding...")
        futures = []
        for name in self.all_drones:
            f = self.client.landAsync(vehicle_name=name)
            futures.append(f)
        for f in futures:
            f.join()

        self.disable_control()

        # Final stats
        if self.episode_count > 0:
            win_rate = 100 * self.runner_wins / self.episode_count
            print(f"\n{'='*60}")
            print(f"Final Results: {self.runner_wins}/{self.episode_count} ({win_rate:.0f}% runner success)")
            print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Run Pursuit-Evasion with trained PPO policy in ASVSim"
    )
    parser.add_argument(
        "--ip",
        type=str,
        default="",
        help="IP address of AirSim server. Use 'wsl' to auto-detect Windows host from WSL."
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=5,
        help="Number of episodes to run (default: 5)"
    )
    parser.add_argument(
        "--policy",
        type=str,
        default="",
        help="Path to PPO policy model.zip (default: auto-detect)"
    )
    parser.add_argument(
        "--no-prompts",
        action="store_true",
        help="Run in non-interactive mode"
    )

    args = parser.parse_args()

    # Handle WSL IP detection
    ip = args.ip
    if ip.lower() == "wsl":
        ip = get_wsl_host_ip()
        print(f"Detected Windows host IP: {ip}")

    # Find policy path
    policy_path = args.policy
    if not policy_path:
        # Try common locations
        candidates = [
            "/mnt/c/Users/john/Desktop/AMS-DRL-Pursuit-Evasion/policies/runner_s1_v2/model.zip",
            "../AMS-DRL-Pursuit-Evasion/policies/runner_s1_v2/model.zip",
            "../../AMS-DRL-Pursuit-Evasion/policies/runner_s1_v2/model.zip",
        ]
        for path in candidates:
            if os.path.exists(path):
                policy_path = path
                break

        if not policy_path:
            print("ERROR: Could not find PPO policy. Specify path with --policy")
            sys.exit(1)

    print(f"Policy path: {policy_path}")

    # Create controller and run
    controller = PursuitEvasionController(policy_path=policy_path, ip=ip)
    controller.run(num_episodes=args.episodes, verbose=True)


if __name__ == "__main__":
    main()
