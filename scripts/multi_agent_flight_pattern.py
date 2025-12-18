"""
Multi-Agent Drone Flight Pattern Demo
=====================================
Demonstrates coordinated flight patterns with multiple drones in ASVSIM.

Patterns included:
- V-Formation flying
- Line formation
- Circular orbit formation
- Synchronized waypoint following

Use the settings.json configuration below with the Blocks environment (FlyingExampleMap):

{
    "SeeDocsAt": "https://cosys-lab.github.io/settings/",
    "SettingsVersion": 1.2,
    "SimMode": "Multirotor",
    "ClockSpeed": 1,

    "Vehicles": {
        "Drone1": {
            "VehicleType": "SimpleFlight",
            "X": 0, "Y": 0, "Z": -2
        },
        "Drone2": {
            "VehicleType": "SimpleFlight",
            "X": 3, "Y": 3, "Z": -2
        },
        "Drone3": {
            "VehicleType": "SimpleFlight",
            "X": 3, "Y": -3, "Z": -2
        },
        "Drone4": {
            "VehicleType": "SimpleFlight",
            "X": 6, "Y": 6, "Z": -2
        },
        "Drone5": {
            "VehicleType": "SimpleFlight",
            "X": 6, "Y": -6, "Z": -2
        }
    }
}
"""

import setup_path
import cosysairsim as airsim
import math
import time
import argparse
import sys


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


class MultiAgentFlightController:
    """Controls multiple drones in coordinated flight patterns."""

    def __init__(self, drone_names=None, ip=""):
        """
        Initialize the multi-agent flight controller.

        Args:
            drone_names: List of drone names to control. If None, uses default 5 drones.
            ip: IP address of the AirSim server. Empty string for localhost.
        """
        self.client = airsim.MultirotorClient(ip=ip)
        self.client.confirmConnection()

        if drone_names is None:
            self.drone_names = ["Drone1", "Drone2", "Drone3", "Drone4", "Drone5"]
        else:
            self.drone_names = drone_names

        self.num_drones = len(self.drone_names)
        print(f"Initialized controller for {self.num_drones} drones: {self.drone_names}")

    def enable_control_all(self):
        """Enable API control for all drones."""
        for name in self.drone_names:
            self.client.enableApiControl(True, name)
            self.client.armDisarm(True, name)
        print("All drones armed and API control enabled")

    def disable_control_all(self):
        """Disable API control for all drones."""
        for name in self.drone_names:
            self.client.armDisarm(False, name)
            self.client.enableApiControl(False, name)
        print("All drones disarmed and API control disabled")

    def takeoff_all(self, timeout=20):
        """Command all drones to take off simultaneously."""
        print("All drones taking off...")
        futures = []
        for name in self.drone_names:
            f = self.client.takeoffAsync(timeout, name)
            futures.append(f)

        for f in futures:
            f.join()
        print("All drones airborne")

    def land_all(self, timeout=60):
        """Command all drones to land simultaneously."""
        print("All drones landing...")
        futures = []
        for name in self.drone_names:
            f = self.client.landAsync(timeout, name)
            futures.append(f)

        for f in futures:
            f.join()
        print("All drones landed")

    def hover_all(self):
        """Command all drones to hover in place."""
        futures = []
        for name in self.drone_names:
            f = self.client.hoverAsync(name)
            futures.append(f)

        for f in futures:
            f.join()

    def move_to_positions(self, positions, velocity=5):
        """
        Move all drones to specified positions simultaneously.

        Args:
            positions: List of (x, y, z) tuples for each drone
            velocity: Movement velocity in m/s
        """
        futures = []
        for i, name in enumerate(self.drone_names):
            x, y, z = positions[i]
            f = self.client.moveToPositionAsync(x, y, z, velocity, vehicle_name=name)
            futures.append(f)

        for f in futures:
            f.join()

    def get_positions(self):
        """Get current positions of all drones."""
        positions = {}
        for name in self.drone_names:
            state = self.client.getMultirotorState(vehicle_name=name)
            pos = state.kinematics_estimated.position
            positions[name] = (pos.x_val, pos.y_val, pos.z_val)
        return positions

    # ========== FLIGHT PATTERNS ==========

    def fly_v_formation(self, leader_path, spacing=5, altitude=-10, velocity=5):
        """
        Fly drones in V-formation following a leader path.

        Args:
            leader_path: List of (x, y) waypoints for the leader drone
            spacing: Distance between drones in the formation
            altitude: Flight altitude (negative = up in NED)
            velocity: Movement velocity in m/s
        """
        print("Flying V-formation pattern...")

        # Calculate V-formation offsets relative to leader
        # Leader is at center, others fan out behind
        offsets = self._calculate_v_offsets(spacing)

        for waypoint in leader_path:
            leader_x, leader_y = waypoint
            positions = []

            for i in range(self.num_drones):
                offset_x, offset_y = offsets[i]
                positions.append((leader_x + offset_x, leader_y + offset_y, altitude))

            print(f"Moving formation to waypoint ({leader_x}, {leader_y})")
            self.move_to_positions(positions, velocity)
            time.sleep(0.5)

        print("V-formation flight complete")

    def _calculate_v_offsets(self, spacing):
        """Calculate position offsets for V-formation."""
        offsets = [(0, 0)]  # Leader at origin

        # Alternate sides: left-back, right-back, further left-back, etc.
        for i in range(1, self.num_drones):
            side = 1 if i % 2 == 1 else -1  # Alternate left/right
            row = (i + 1) // 2  # How many rows back
            offset_x = -row * spacing * 0.7  # Behind leader
            offset_y = side * row * spacing  # To the side
            offsets.append((offset_x, offset_y))

        return offsets

    def fly_line_formation(self, start_pos, end_pos, spacing=4, altitude=-10, velocity=5):
        """
        Fly drones in a line formation from start to end position.

        Args:
            start_pos: (x, y) starting position for leader
            end_pos: (x, y) ending position for leader
            spacing: Distance between drones in the line
            altitude: Flight altitude (negative = up in NED)
            velocity: Movement velocity in m/s
        """
        print("Flying line formation pattern...")

        # First, form the line at starting position
        line_positions = []
        for i in range(self.num_drones):
            x = start_pos[0]
            y = start_pos[1] + i * spacing
            line_positions.append((x, y, altitude))

        print("Forming line at start position...")
        self.move_to_positions(line_positions, velocity)
        time.sleep(1)

        # Now move the entire line to end position
        end_positions = []
        for i in range(self.num_drones):
            x = end_pos[0]
            y = end_pos[1] + i * spacing
            end_positions.append((x, y, altitude))

        print("Moving line formation to end position...")
        self.move_to_positions(end_positions, velocity)

        print("Line formation flight complete")

    def fly_circle_formation(self, center, radius=10, altitude=-10, velocity=3, orbits=1):
        """
        Fly drones in a circular orbit around a center point, maintaining formation.

        Args:
            center: (x, y) center point of the circle
            radius: Radius of the circle
            altitude: Flight altitude (negative = up in NED)
            velocity: Movement velocity in m/s
            orbits: Number of complete orbits to perform
        """
        print(f"Flying circle formation pattern: {orbits} orbit(s) around ({center[0]}, {center[1]})")

        # Calculate angular spacing between drones
        angle_spacing = 2 * math.pi / self.num_drones

        # Number of steps per orbit (more steps = smoother circle)
        steps_per_orbit = 36  # 10 degrees per step
        total_steps = steps_per_orbit * orbits
        angle_step = 2 * math.pi / steps_per_orbit

        # Initial formation: position drones evenly around the circle
        print("Forming circular formation...")
        initial_positions = []
        for i in range(self.num_drones):
            angle = i * angle_spacing
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            initial_positions.append((x, y, altitude))

        self.move_to_positions(initial_positions, velocity)
        time.sleep(1)

        # Orbit while maintaining formation
        print("Starting orbital flight...")
        for step in range(total_steps):
            positions = []
            base_angle = step * angle_step

            for i in range(self.num_drones):
                angle = base_angle + i * angle_spacing
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                positions.append((x, y, altitude))

            # Use velocity control for smoother motion
            futures = []
            for i, name in enumerate(self.drone_names):
                x, y, z = positions[i]
                # Calculate velocity towards next position
                state = self.client.getMultirotorState(vehicle_name=name)
                curr_pos = state.kinematics_estimated.position

                dx = x - curr_pos.x_val
                dy = y - curr_pos.y_val
                dz = z - curr_pos.z_val

                # Normalize and scale by velocity
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                if dist > 0.1:
                    vx = velocity * dx / dist
                    vy = velocity * dy / dist
                    vz = velocity * dz / dist
                else:
                    vx, vy, vz = 0, 0, 0

                f = self.client.moveByVelocityZAsync(vx, vy, altitude, 0.5, vehicle_name=name)
                futures.append(f)

            # Don't wait for all futures to complete - just a short delay
            time.sleep(0.3)

        # Return to hover
        self.hover_all()
        print("Circle formation flight complete")

    def fly_synchronized_waypoints(self, waypoints, altitude=-10, velocity=5):
        """
        All drones fly to the same waypoints in sequence, maintaining a staggered formation.

        Args:
            waypoints: List of (x, y) waypoints
            altitude: Flight altitude (negative = up in NED)
            velocity: Movement velocity in m/s
        """
        print("Flying synchronized waypoint pattern...")

        # Offset each drone slightly from the waypoint
        offset_radius = 3
        angle_spacing = 2 * math.pi / self.num_drones

        for wp in waypoints:
            wp_x, wp_y = wp
            print(f"All drones moving to waypoint ({wp_x}, {wp_y})")

            # Calculate positions around the waypoint
            positions = []
            for i in range(self.num_drones):
                angle = i * angle_spacing
                x = wp_x + offset_radius * math.cos(angle)
                y = wp_y + offset_radius * math.sin(angle)
                positions.append((x, y, altitude))

            self.move_to_positions(positions, velocity)
            time.sleep(1)

        print("Synchronized waypoint flight complete")

    def fly_expanding_spiral(self, center, start_radius=5, end_radius=20, altitude=-10, velocity=4):
        """
        Fly drones in an expanding spiral pattern from the center outward.

        Args:
            center: (x, y) center point
            start_radius: Starting radius
            end_radius: Ending radius
            altitude: Flight altitude (negative = up in NED)
            velocity: Movement velocity in m/s
        """
        print("Flying expanding spiral pattern...")

        angle_spacing = 2 * math.pi / self.num_drones
        num_steps = 72  # Complete 2 full rotations while expanding

        for step in range(num_steps):
            # Calculate current radius (linear interpolation)
            t = step / (num_steps - 1)
            radius = start_radius + t * (end_radius - start_radius)

            # Calculate base angle for this step
            base_angle = step * (4 * math.pi / num_steps)  # 2 full rotations

            positions = []
            for i in range(self.num_drones):
                angle = base_angle + i * angle_spacing
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                positions.append((x, y, altitude))

            # Move all drones
            futures = []
            for i, name in enumerate(self.drone_names):
                x, y, z = positions[i]
                f = self.client.moveToPositionAsync(x, y, z, velocity, vehicle_name=name)
                futures.append(f)

            # Brief pause to allow movement
            time.sleep(0.2)

        # Wait for final positions
        self.hover_all()
        print("Expanding spiral pattern complete")


def run_demo(pattern="all", num_drones=5, ip="", interactive=True):
    """
    Run the multi-agent flight pattern demo.

    Args:
        pattern: Which pattern to run ("v", "line", "circle", "waypoints", "spiral", or "all")
        num_drones: Number of drones to use (2-5)
        ip: IP address of the AirSim server. Use "wsl" to auto-detect Windows host from WSL.
        interactive: If True, wait for key presses between steps. Set False for non-interactive mode.
    """
    def wait_or_continue(msg):
        if interactive:
            airsim.wait_key(msg)
        else:
            print(msg.replace("Press any key to", "Starting:"))
            time.sleep(1)

    # Handle WSL auto-detection
    if ip.lower() == "wsl":
        ip = get_wsl_host_ip()
        print(f"Detected Windows host IP: {ip}")

    drone_names = [f"Drone{i+1}" for i in range(num_drones)]
    controller = MultiAgentFlightController(drone_names, ip=ip)

    print("\n" + "="*50)
    print("Multi-Agent Drone Flight Pattern Demo")
    print("="*50 + "\n")

    # Initialize
    controller.enable_control_all()
    wait_or_continue("Press any key to take off...")
    controller.takeoff_all()

    # Climb to altitude
    print("\nClimbing to formation altitude...")
    initial_positions = [(i * 3, 0, -10) for i in range(num_drones)]
    controller.move_to_positions(initial_positions, velocity=3)
    time.sleep(2)

    try:
        if pattern in ["v", "all"]:
            wait_or_continue("\nPress any key to start V-formation flight...")
            v_path = [
                (0, 0),
                (20, 0),
                (20, 20),
                (40, 20),
                (40, 0),
                (20, 0)
            ]
            controller.fly_v_formation(v_path, spacing=5, altitude=-10, velocity=5)

        if pattern in ["line", "all"]:
            wait_or_continue("\nPress any key to start line formation flight...")
            controller.fly_line_formation(
                start_pos=(0, -10),
                end_pos=(30, -10),
                spacing=4,
                altitude=-12,
                velocity=5
            )

        if pattern in ["circle", "all"]:
            wait_or_continue("\nPress any key to start circle formation flight...")
            controller.fly_circle_formation(
                center=(15, 0),
                radius=12,
                altitude=-15,
                velocity=4,
                orbits=2
            )

        if pattern in ["waypoints", "all"]:
            wait_or_continue("\nPress any key to start synchronized waypoint flight...")
            waypoints = [
                (0, 0),
                (10, 10),
                (20, 0),
                (10, -10),
                (0, 0)
            ]
            controller.fly_synchronized_waypoints(waypoints, altitude=-10, velocity=5)

        if pattern in ["spiral", "all"]:
            wait_or_continue("\nPress any key to start expanding spiral flight...")
            controller.fly_expanding_spiral(
                center=(15, 0),
                start_radius=5,
                end_radius=20,
                altitude=-12,
                velocity=4
            )

    except KeyboardInterrupt:
        print("\nInterrupted by user")

    # Land and cleanup
    wait_or_continue("\nPress any key to land all drones...")
    controller.land_all()
    controller.disable_control_all()

    print("\nDemo complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Multi-Agent Drone Flight Pattern Demo for ASVSIM"
    )
    parser.add_argument(
        "--pattern",
        type=str,
        choices=["v", "line", "circle", "waypoints", "spiral", "all"],
        default="all",
        help="Flight pattern to run (default: all)"
    )
    parser.add_argument(
        "--drones",
        type=int,
        choices=[2, 3, 4, 5],
        default=5,
        help="Number of drones to use (default: 5)"
    )
    parser.add_argument(
        "--ip",
        type=str,
        default="",
        help="IP address of AirSim server. Use 'wsl' to auto-detect Windows host from WSL."
    )
    parser.add_argument(
        "--no-prompts",
        action="store_true",
        help="Run in non-interactive mode without waiting for key presses."
    )

    args = parser.parse_args()
    run_demo(pattern=args.pattern, num_drones=args.drones, ip=args.ip, interactive=not args.no_prompts)
