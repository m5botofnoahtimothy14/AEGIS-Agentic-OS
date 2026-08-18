import json
import os
import time
import math
import logging

logger = logging.getLogger("SATURDAY.HomeBot.Mapping")

MAP_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "homebot_map.json")


class GridMap:
    def __init__(self, width=100, height=100, resolution=0.1):
        self.width = width
        self.height = height
        self.resolution = resolution
        self.grid = [[0 for _ in range(width)] for _ in range(height)]
        self.origin_x = width // 2
        self.origin_y = height // 2
        self.occupancy_threshold = 60

    def world_to_grid(self, x, y):
        gx = int(self.origin_x + x / self.resolution)
        gy = int(self.origin_y + y / self.resolution)
        gx = max(0, min(gx, self.width - 1))
        gy = max(0, min(gy, self.height - 1))
        return gx, gy

    def grid_to_world(self, gx, gy):
        x = (gx - self.origin_x) * self.resolution
        y = (gy - self.origin_y) * self.resolution
        return x, y

    def mark_occupied(self, x, y, confidence=80):
        gx, gy = self.world_to_grid(x, y)
        self.grid[gy][gx] = min(100, self.grid[gy][gx] + confidence)

    def mark_free(self, x, y, confidence=30):
        gx, gy = self.world_to_grid(x, y)
        self.grid[gy][gx] = max(0, self.grid[gy][gx] - confidence)

    def is_occupied(self, x, y):
        gx, gy = self.world_to_grid(x, y)
        return self.grid[gy][gx] >= self.occupancy_threshold

    def get_frontiers(self, robot_x, robot_y, max_range=30):
        frontiers = []
        rgx, rgy = self.world_to_grid(robot_x, robot_y)
        for dy in range(-max_range, max_range + 1):
            for dx in range(-max_range, max_range + 1):
                gx, gy = rgx + dx, rgy + dy
                if 0 <= gx < self.width and 0 <= gy < self.height:
                    if self.grid[gy][gx] == 0:
                        for ndx, ndy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            ngx, ngy = gx + ndx, gy + ndy
                            if 0 <= ngx < self.width and 0 <= ngy < self.height:
                                if self.grid[ngy][ngx] >= self.occupancy_threshold:
                                    frontiers.append((gx, gy))
                                    break
        return frontiers[:50]


class HomeBotMap:
    def __init__(self):
        self.grid = GridMap()
        self.robot_position = {"x": 0.0, "y": 0.0, "theta": 0.0}
        self.waypoints = []
        self.path_history = []
        self.obstacles = []
        self.landmarks = {}
        self.scan_history = []
        self._load_map()

    def _load_map(self):
        try:
            if os.path.exists(MAP_FILE):
                with open(MAP_FILE, "r") as f:
                    data = json.load(f)
                    self.robot_position = data.get("robot_position", self.robot_position)
                    self.waypoints = data.get("waypoints", [])
                    self.obstacles = data.get("obstacles", [])
                    self.landmarks = data.get("landmarks", {})
                    saved_grid = data.get("grid")
                    if saved_grid and len(saved_grid) == self.grid.height:
                        self.grid.grid = saved_grid
        except Exception:
            pass

    def _save_map(self):
        try:
            os.makedirs(os.path.dirname(MAP_FILE), exist_ok=True)
            with open(MAP_FILE, "w") as f:
                json.dump({
                    "robot_position": self.robot_position,
                    "waypoints": self.waypoints,
                    "obstacles": self.obstacles,
                    "landmarks": self.landmarks,
                    "grid": self.grid.grid,
                    "last_updated": time.time(),
                }, f, indent=2)
        except Exception:
            pass

    def update_position(self, x, y, theta):
        self.robot_position = {"x": x, "y": y, "theta": theta}
        self.path_history.append({"x": x, "y": y, "time": time.time()})
        if len(self.path_history) > 1000:
            self.path_history = self.path_history[-1000:]
        self.grid.mark_free(x, y)
        self._save_map()

    def process_lidar_scan(self, scan_data):
        if not isinstance(scan_data, dict):
            return
        angles = scan_data.get("angles", [])
        distances = scan_data.get("distances", [])
        if not angles or not distances:
            return

        rx, ry = self.robot_position["x"], self.robot_position["y"]
        theta = self.robot_position["theta"]

        scan_points = []
        for angle, dist in zip(angles, distances):
            if dist is None or dist <= 0 or dist > 10:
                continue
            world_angle = theta + angle
            wx = rx + dist * math.cos(world_angle)
            wy = ry + dist * math.sin(world_angle)
            self.grid.mark_occupied(wx, wy)
            scan_points.append({"x": wx, "y": wy, "distance": dist})

            for step in range(1, int(dist / self.grid.resolution)):
                free_dist = step * self.grid.resolution
                fx = rx + free_dist * math.cos(world_angle)
                fy = ry + free_dist * math.sin(world_angle)
                self.grid.mark_free(fx, fy)

        self.scan_history.append({
            "timestamp": time.time(),
            "robot_pos": self.robot_position.copy(),
            "points": len(scan_points),
        })
        self._save_map()

    def process_nav_scan(self, data):
        if not isinstance(data, dict):
            return
        sensor_data = data.get("sensors", data)
        if isinstance(sensor_data, dict):
            for direction, distance in sensor_data.items():
                if distance is None:
                    continue
                try:
                    dist = float(distance)
                except (ValueError, TypeError):
                    continue
                rx, ry = self.robot_position["x"], self.robot_position["y"]
                theta = self.robot_position["theta"]
                direction_map = {
                    "front": theta, "forward": theta,
                    "back": theta + math.pi, "rear": theta + math.pi,
                    "left": theta - math.pi / 2,
                    "right": theta + math.pi / 2,
                    "front_left": theta - math.pi / 4,
                    "front_right": theta + math.pi / 4,
                    "back_left": theta - 3 * math.pi / 4,
                    "back_right": theta + 3 * math.pi / 4,
                }
                angle = direction_map.get(direction.lower(), theta)
                wx = rx + dist * math.cos(angle)
                wy = ry + dist * math.sin(angle)
                if dist < 2.0:
                    self.grid.mark_occupied(wx, wy)
                else:
                    self.grid.mark_free(wx, wy)
                    obstacle_x = rx + (dist - 0.1) * math.cos(angle)
                    obstacle_y = ry + (dist - 0.1) * math.sin(angle)
                    self.obstacles.append({"x": round(obstacle_x, 2), "y": round(obstacle_y, 2), "time": time.time()})
        self._save_map()

    def add_waypoint(self, x, y, label=""):
        wp = {"x": x, "y": y, "label": label or f"WP-{len(self.waypoints)+1}", "created": time.time()}
        self.waypoints.append(wp)
        self._save_map()
        return wp

    def remove_waypoint(self, index):
        if 0 <= index < len(self.waypoints):
            removed = self.waypoints.pop(index)
            self._save_map()
            return removed
        return None

    def add_landmark(self, name, x, y, description=""):
        self.landmarks[name] = {"x": x, "y": y, "description": description, "added": time.time()}
        self._save_map()

    def find_path(self, target_x, target_y):
        rx, ry = self.robot_position["x"], self.robot_position["y"]
        dx = target_x - rx
        dy = target_y - ry
        distance = math.sqrt(dx*dx + dy*dy)
        angle = math.atan2(dy, dx)

        waypoints = []
        steps = max(1, int(distance / 0.5))
        for i in range(1, steps + 1):
            frac = i / steps
            wx = rx + dx * frac
            wy = ry + dy * frac
            if self.grid.is_occupied(wx, wy):
                return {"success": False, "error": "Path blocked by obstacle", "blocked_at": {"x": wx, "y": wy}}
            waypoints.append({"x": round(wx, 2), "y": round(wy, 2)})

        return {
            "success": True,
            "distance": round(distance, 2),
            "angle": round(math.degrees(angle), 1),
            "waypoints": waypoints,
            "estimated_time": round(distance / 0.3, 1),
        }

    def get_map_status(self):
        occupied = sum(1 for row in self.grid.grid for cell in row if cell >= self.grid.occupancy_threshold)
        free = sum(1 for row in self.grid.grid for cell in row if 0 < cell < self.grid.occupancy_threshold)
        unknown = sum(1 for row in self.grid.grid for cell in row if cell == 0)
        total = self.grid.width * self.grid.height

        return {
            "robot_position": self.robot_position,
            "grid_size": f"{self.grid.width}x{self.grid.height}",
            "resolution": self.grid.resolution,
            "occupied_cells": occupied,
            "free_cells": free,
            "unknown_cells": unknown,
            "occupancy_pct": round(occupied / total * 100, 1),
            "waypoints": len(self.waypoints),
            "landmarks": len(self.landmarks),
            "obstacles": len(self.obstacles),
            "scans": len(self.scan_history),
            "path_points": len(self.path_history),
        }

    def get_map_data(self):
        return {
            "status": self.get_map_status(),
            "waypoints": self.waypoints,
            "landmarks": self.landmarks,
            "robot_position": self.robot_position,
            "path_history": self.path_history[-100:],
        }
