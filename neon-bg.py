#!/usr/bin/env python3
from ctypes import CDLL
CDLL("libgtk4-layer-shell.so")

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")

from gi.repository import Gtk, Gdk, GLib
from gi.repository import Gtk4LayerShell as LayerShell

import cairo
import math
import random
import time


APP_ID = "dev.quendoris.neon.flow.desktop"

FRAME_INTERVAL_MS = 4
SMOOTH_DT_INITIAL = 1.0 / 240.0
SMOOTH_DT_BLEND = 0.12
SMOOTH_DT_MIN = 1.0 / 360.0
SMOOTH_DT_MAX = 1.0 / 120.0
SMOOTH_DT_HARD_RESET = 0.080

FLOW_SPEED_PX_PER_SEC = 30.0

OVERSCAN_MIN = 220.0
OVERSCAN_MAX = 360.0
FADE_ZONE = 190.0

ANIMATED_BACKLIGHT_UPDATE_MS = 140
ANIMATED_BACKLIGHT_SPEED = 0.115
ANIMATED_BACKLIGHT_ALPHA = 0.060

MIN_DIST_DIVISOR = 16.7
MIN_DIST_MIN = 80.0
MIN_DIST_MAX = 122.0

EDGE_LINK_RADIUS_MULTIPLIER = 2.18
EDGE_WIDTH = 1.12
EDGE_ALPHA = 0.39
EDGE_SHORT_ALPHA_BOOST = 1.42
EDGE_LONG_ALPHA_FLOOR = 0.055
EDGE_FADE_START_MULTIPLIER = 0.86
EDGE_FADE_END_MULTIPLIER = 1.18
EDGE_MAX_DEGREE = 6
EDGE_TARGET_DEGREE = 5
EDGE_CANDIDATES_PER_POINT = 9
EDGE_REBUILD_ACTIVE_MS = 104
EDGE_REBUILD_IDLE_MS = 360
EDGE_REBUILD_MIN_MS = 82
MOUSE_ACTIVE_SECONDS = 1.15
MOTION_ACTIVE_SPEED = 7.0

POINT_MIN_SIZE = 2.55
POINT_MAX_SIZE = 4.25
POINT_CORE_ALPHA = 0.98
POINT_INNER_GLOW_ALPHA = 0.36
POINT_OUTER_GLOW_ALPHA = 0.15
POINT_INNER_GLOW_MULTIPLIER = 3.4
POINT_OUTER_GLOW_MULTIPLIER = 8.7

KICK_RADIUS = 720.0
KICK_INNER_RADIUS = 145.0
KICK_STRENGTH = 30.0
KICK_INNER_STRENGTH = 36.0
KICK_TRAIL_RADIUS = 840.0
KICK_TRAIL_INNER_RADIUS = 165.0
KICK_TRAIL_STRENGTH = 23.0
KICK_TRAIL_INNER_STRENGTH = 29.0
MOUSE_DIRECTION_PUSH = 0.24
KICK_INSTANT_NUDGE = 0.020
KICK_INSTANT_NUDGE_MAX = 2.15

VELOCITY_DAMPING = 2.65
GRAVITY_ACCEL = 24.0
UPWARD_EXTRA_DAMPING = 4.2
UPWARD_IMPULSE_SCALE = 0.58
DOWNWARD_IMPULSE_SCALE = 1.06
MAX_VELOCITY = 220.0
BOUNDARY_STIFFNESS = 3.6

NEON_PALETTE = [
    (1.00, 0.22, 0.88),
    (0.82, 0.22, 1.00),
    (0.48, 0.34, 1.00),
    (0.20, 0.70, 1.00),
    (0.18, 1.00, 0.88),
    (1.00, 0.42, 0.70),
]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def clamp01(v):
    return clamp(v, 0.0, 1.0)


def lerp(a, b, t):
    return a + (b - a) * t


def smootherstep(x):
    x = clamp01(x)
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def color_mix(c1, c2, t):
    return (lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t))


def limit_vector(x, y, max_len):
    length = math.sqrt(x * x + y * y)
    if length <= max_len or length <= 0.000001:
        return x, y
    scale = max_len / length
    return x * scale, y * scale


def distance_to_segment(px, py, ax, ay, bx, by):
    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay
    ab_len2 = abx * abx + aby * aby
    if ab_len2 <= 0.000001:
        dx = px - ax
        dy = py - ay
        return math.sqrt(dx * dx + dy * dy), ax, ay
    t = clamp01((apx * abx + apy * aby) / ab_len2)
    cx = ax + abx * t
    cy = ay + aby * t
    dx = px - cx
    dy = py - cy
    return math.sqrt(dx * dx + dy * dy), cx, cy


def ccw(ax, ay, bx, by, cx, cy):
    return (cy - ay) * (bx - ax) > (by - ay) * (cx - ax)


def segments_intersect(a, b, c, d):
    ax, ay = a
    bx, by = b
    cx, cy = c
    dx, dy = d
    if max(ax, bx) < min(cx, dx) or max(cx, dx) < min(ax, bx):
        return False
    if max(ay, by) < min(cy, dy) or max(cy, dy) < min(ay, by):
        return False
    return ccw(ax, ay, cx, cy, dx, dy) != ccw(bx, by, cx, cy, dx, dy) and ccw(ax, ay, bx, by, cx, cy) != ccw(ax, ay, bx, by, dx, dy)


def create_star_sprite(color, size):
    outer_radius = int(math.ceil(size * POINT_OUTER_GLOW_MULTIPLIER + 3.0))
    surface_size = outer_radius * 2 + 2
    center = surface_size / 2.0
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, surface_size, surface_size)
    cr = cairo.Context(surface)
    c = color

    outer = cairo.RadialGradient(center, center, 0.0, center, center, size * POINT_OUTER_GLOW_MULTIPLIER)
    outer.add_color_stop_rgba(0.00, c[0], c[1], c[2], POINT_OUTER_GLOW_ALPHA)
    outer.add_color_stop_rgba(0.38, c[0], c[1], c[2], POINT_OUTER_GLOW_ALPHA * 0.36)
    outer.add_color_stop_rgba(1.00, c[0], c[1], c[2], 0.00)
    cr.arc(center, center, size * POINT_OUTER_GLOW_MULTIPLIER, 0, math.tau)
    cr.set_source(outer)
    cr.fill()

    inner = cairo.RadialGradient(center, center, 0.0, center, center, size * POINT_INNER_GLOW_MULTIPLIER)
    inner.add_color_stop_rgba(0.00, 1.00, 0.86, 1.00, POINT_INNER_GLOW_ALPHA)
    inner.add_color_stop_rgba(0.28, c[0], c[1], c[2], POINT_INNER_GLOW_ALPHA * 0.78)
    inner.add_color_stop_rgba(1.00, c[0], c[1], c[2], 0.00)
    cr.arc(center, center, size * POINT_INNER_GLOW_MULTIPLIER, 0, math.tau)
    cr.set_source(inner)
    cr.fill()

    core = cairo.RadialGradient(center, center, 0.0, center, center, size * 1.35)
    core.add_color_stop_rgba(0.00, 1.00, 0.90, 1.00, POINT_CORE_ALPHA)
    core.add_color_stop_rgba(0.42, c[0], c[1], c[2], POINT_CORE_ALPHA * 0.88)
    core.add_color_stop_rgba(1.00, c[0], c[1], c[2], 0.00)
    cr.arc(center, center, size * 1.35, 0, math.tau)
    cr.set_source(core)
    cr.fill()

    return surface, center


class NeonCanvas(Gtk.DrawingArea):
    def __init__(self, monitor_name, initial_width, initial_height):
        super().__init__()
        self.monitor_name = monitor_name
        self.seed = 1337 + sum(ord(ch) for ch in monitor_name)
        self.rng = random.Random(self.seed + 7001)
        self.spawn_counter = 0

        self.points = []
        self.edges = []
        self.layout_key = None
        self.current_width = initial_width
        self.current_height = initial_height
        self.overscan = 240.0
        self.min_dist = 110.0
        self.edge_link_radius = self.min_dist * EDGE_LINK_RADIUS_MULTIPLIER

        self.mouse_x = self.mouse_y = 0.0
        self.prev_mouse_x = self.prev_mouse_y = 0.0
        self.mouse_inside = False
        self.has_mouse_history = False
        self.last_mouse_time = 0.0
        self.last_tick_time = time.monotonic()
        self.smoothed_dt = SMOOTH_DT_INITIAL
        self.last_edge_rebuild_time = 0.0
        self.edge_dirty = True

        self.background_surface = None
        self.background_key = None
        self.animated_backlight_surface = None
        self.animated_backlight_key = None
        self.sprite_cache = {}

        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_content_width(initial_width)
        self.set_content_height(initial_height)
        self.set_draw_func(self.draw)

        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self.on_motion)
        motion.connect("leave", self.on_leave)
        self.add_controller(motion)

    def on_motion(self, _controller, x, y):
        x = float(x)
        y = float(y)
        if not self.has_mouse_history:
            self.prev_mouse_x = x
            self.prev_mouse_y = y
            self.has_mouse_history = True
        else:
            self.prev_mouse_x = self.mouse_x
            self.prev_mouse_y = self.mouse_y
        self.mouse_x = x
        self.mouse_y = y
        self.mouse_inside = True
        self.last_mouse_time = time.monotonic()
        self.apply_mouse_kick()
        self.edge_dirty = True
        self.queue_draw()

    def on_leave(self, _controller):
        self.mouse_inside = False
        self.has_mouse_history = False

    def choose_point_color(self, rng, x, y, width, height):
        nx = x / max(1.0, width)
        ny = y / max(1.0, height)
        base = (nx * 2.6 + ny * 1.8 + rng.random() * 1.25) % len(NEON_PALETTE)
        i = int(base)
        j = (i + 1) % len(NEON_PALETTE)
        c = color_mix(NEON_PALETTE[i], NEON_PALETTE[j], base - i)
        return min(1.0, c[0] * 1.05), min(1.0, c[1] * 1.05), min(1.0, c[2] * 1.05)

    def get_star_sprite(self, color, size):
        key = (int(color[0] * 255), int(color[1] * 255), int(color[2] * 255), int(size * 10))
        sprite = self.sprite_cache.get(key)
        if sprite is None:
            sprite = create_star_sprite(color, size)
            self.sprite_cache[key] = sprite
        return sprite

    def make_point(self, rng, x, y, width, height):
        size = rng.uniform(POINT_MIN_SIZE, POINT_MAX_SIZE)
        color = self.choose_point_color(rng, x, y, width, height)
        sprite, center = self.get_star_sprite(color, size)
        return {"x": x, "y": y, "vx": 0.0, "vy": 0.0, "size": size, "color": color, "sprite": sprite, "sprite_center": center}

    def generate_poisson_points(self, width, height, min_dist, overscan):
        rng = random.Random(self.seed + width * 17 + height * 31)
        min_x, max_x = -overscan, width + overscan
        min_y, max_y = -overscan, height + overscan
        r = float(min_dist)
        cell = r / math.sqrt(2.0)
        grid_w = max(1, int(math.ceil((max_x - min_x) / cell)))
        grid_h = max(1, int(math.ceil((max_y - min_y) / cell)))
        grid = [-1] * (grid_w * grid_h)
        points, active = [], []

        def grid_coords(x, y): return int((x - min_x) / cell), int((y - min_y) / cell)
        def grid_index(gx, gy): return gy * grid_w + gx
        def in_bounds(x, y): return min_x <= x <= max_x and min_y <= y <= max_y
        def fits(x, y):
            if not in_bounds(x, y):
                return False
            gx, gy = grid_coords(x, y)
            rr = r * r
            for yy in range(max(0, gy - 2), min(grid_h, gy + 3)):
                for xx in range(max(0, gx - 2), min(grid_w, gx + 3)):
                    idx = grid[yy * grid_w + xx]
                    if idx == -1:
                        continue
                    dx = points[idx]["x"] - x
                    dy = points[idx]["y"] - y
                    if dx * dx + dy * dy < rr:
                        return False
            return True

        start_x, start_y = rng.uniform(min_x, max_x), rng.uniform(min_y, max_y)
        points.append(self.make_point(rng, start_x, start_y, width, height))
        active.append(0)
        gx, gy = grid_coords(start_x, start_y)
        grid[grid_index(gx, gy)] = 0

        while active:
            active_i = rng.randrange(len(active))
            base = points[active[active_i]]
            found = False
            for _ in range(26):
                angle = rng.random() * math.tau
                dist = rng.uniform(r, r * 1.95)
                x = base["x"] + math.cos(angle) * dist
                y = base["y"] + math.sin(angle) * dist
                if not fits(x, y):
                    continue
                idx = len(points)
                points.append(self.make_point(rng, x, y, width, height))
                active.append(idx)
                gx, gy = grid_coords(x, y)
                grid[grid_index(gx, gy)] = idx
                found = True
                break
            if not found:
                active[active_i] = active[-1]
                active.pop()
        return points

    def kick_falloff(self, distance, radius):
        if distance >= radius:
            return 0.0
        return smootherstep(1.0 - distance / radius)

    def add_impulse(self, point, center_x, center_y, distance, outer_radius, inner_radius, outer_strength, inner_strength, dt_scale):
        if distance <= 0.001 or distance >= outer_radius:
            return
        dx = point["x"] - center_x
        dy = point["y"] - center_y
        length = math.sqrt(dx * dx + dy * dy)
        if length <= 0.001:
            return
        ux, uy = dx / length, dy / length
        impulse = (self.kick_falloff(distance, outer_radius) * outer_strength + self.kick_falloff(distance, inner_radius) * inner_strength) * dt_scale
        mdx = self.mouse_x - self.prev_mouse_x
        mdy = self.mouse_y - self.prev_mouse_y
        mlen = math.sqrt(mdx * mdx + mdy * mdy)
        if mlen > 0.001:
            ux = ux * (1.0 - MOUSE_DIRECTION_PUSH) + (mdx / mlen) * MOUSE_DIRECTION_PUSH
            uy = uy * (1.0 - MOUSE_DIRECTION_PUSH) + (mdy / mlen) * MOUSE_DIRECTION_PUSH
            ulen = math.sqrt(ux * ux + uy * uy)
            if ulen > 0.001:
                ux, uy = ux / ulen, uy / ulen
        impulse *= UPWARD_IMPULSE_SCALE if uy < 0.0 else DOWNWARD_IMPULSE_SCALE
        instant = min(KICK_INSTANT_NUDGE_MAX, impulse * KICK_INSTANT_NUDGE)
        point["x"] += ux * instant
        point["y"] += uy * instant
        point["vx"] += ux * impulse
        point["vy"] += uy * impulse
        point["vx"], point["vy"] = limit_vector(point["vx"], point["vy"], MAX_VELOCITY)

    def apply_mouse_kick(self):
        if not self.points or not self.mouse_inside:
            return
        mdx = self.mouse_x - self.prev_mouse_x
        mdy = self.mouse_y - self.prev_mouse_y
        mouse_dist = math.sqrt(mdx * mdx + mdy * mdy)
        dt_scale = clamp(0.58 + mouse_dist / 340.0, 0.58, 1.55)
        for point in self.points:
            dx, dy = point["x"] - self.mouse_x, point["y"] - self.mouse_y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < KICK_RADIUS:
                self.add_impulse(point, self.mouse_x, self.mouse_y, dist, KICK_RADIUS, KICK_INNER_RADIUS, KICK_STRENGTH, KICK_INNER_STRENGTH, dt_scale)
            if self.has_mouse_history:
                trail_dist, cx, cy = distance_to_segment(point["x"], point["y"], self.prev_mouse_x, self.prev_mouse_y, self.mouse_x, self.mouse_y)
                if trail_dist < KICK_TRAIL_RADIUS:
                    self.add_impulse(point, cx, cy, trail_dist, KICK_TRAIL_RADIUS, KICK_TRAIL_INNER_RADIUS, KICK_TRAIL_STRENGTH, KICK_TRAIL_INNER_STRENGTH, dt_scale)

    def point_may_be_relevant(self, p, width, height, pad):
        return -pad <= p["x"] <= width + pad and -pad <= p["y"] <= height + pad

    def segment_visible(self, x1, y1, x2, y2, width, height, pad):
        return not (max(x1, x2) < -pad or min(x1, x2) > width + pad or max(y1, y2) < -pad or min(y1, y2) > height + pad)

    def would_cross_existing(self, i, j, p1, p2, accepted):
        for a, b, q1, q2 in accepted:
            if i == a or i == b or j == a or j == b:
                continue
            if segments_intersect(p1, p2, q1, q2):
                return True
        return False

    def rebuild_dynamic_edges(self, width, height):
        if len(self.points) < 3:
            self.edges = []
            return
        radius = self.edge_link_radius
        radius2 = radius * radius
        pad = self.overscan * 0.72
        cell = radius
        spatial, relevant_indices = {}, []
        for i, p in enumerate(self.points):
            if not self.point_may_be_relevant(p, width, height, pad):
                continue
            relevant_indices.append(i)
            gx, gy = int(p["x"] // cell), int(p["y"] // cell)
            spatial.setdefault((gx, gy), []).append(i)

        degrees = [0] * len(self.points)
        accepted, edges, kept = [], [], set()
        for edge in self.edges:
            if len(edge) != 2:
                continue
            i, j = edge
            if i < 0 or j < 0 or i >= len(self.points) or j >= len(self.points):
                continue
            p, q = self.points[i], self.points[j]
            if not self.segment_visible(p["x"], p["y"], q["x"], q["y"], width, height, FADE_ZONE + self.overscan):
                continue
            a, b = (i, j) if i < j else (j, i)
            p1, p2 = (p["x"], p["y"]), (q["x"], q["y"])
            if self.would_cross_existing(a, b, p1, p2, accepted):
                continue
            accepted.append((a, b, p1, p2))
            edges.append((a, b))
            kept.add((a, b))
            degrees[a] += 1
            degrees[b] += 1

        candidates, seen = [], set(kept)
        for i in relevant_indices:
            p = self.points[i]
            gx, gy = int(p["x"] // cell), int(p["y"] // cell)
            local = []
            for ny in range(gy - 1, gy + 2):
                for nx in range(gx - 1, gx + 2):
                    for j in spatial.get((nx, ny), []):
                        if j == i:
                            continue
                        q = self.points[j]
                        dx, dy = q["x"] - p["x"], q["y"] - p["y"]
                        d2 = dx * dx + dy * dy
                        if d2 <= radius2:
                            local.append((d2, j))
            local.sort(key=lambda item: item[0])
            for d2, j in local[:EDGE_CANDIDATES_PER_POINT]:
                a, b = (i, j) if i < j else (j, i)
                if (a, b) in seen:
                    continue
                seen.add((a, b))
                candidates.append((d2, a, b))
        candidates.sort(key=lambda item: item[0])
        for d2, i, j in candidates:
            if degrees[i] >= EDGE_MAX_DEGREE or degrees[j] >= EDGE_MAX_DEGREE:
                continue
            if (degrees[i] >= EDGE_TARGET_DEGREE or degrees[j] >= EDGE_TARGET_DEGREE) and d2 > radius2 * 0.38:
                continue
            p, q = self.points[i], self.points[j]
            p1, p2 = (p["x"], p["y"]), (q["x"], q["y"])
            if self.would_cross_existing(i, j, p1, p2, accepted):
                continue
            accepted.append((i, j, p1, p2))
            edges.append((i, j))
            degrees[i] += 1
            degrees[j] += 1
        self.edges = edges
        self.edge_dirty = False
        self.last_edge_rebuild_time = time.monotonic()

    def ensure_layout(self, width, height):
        layout_key = (width, height)
        if self.layout_key == layout_key:
            return
        self.layout_key = layout_key
        self.current_width = width
        self.current_height = height
        self.sprite_cache.clear()
        self.overscan = max(OVERSCAN_MIN, min(OVERSCAN_MAX, min(width, height) * 0.30))
        self.min_dist = max(MIN_DIST_MIN, min(MIN_DIST_MAX, math.sqrt(width * height) / MIN_DIST_DIVISOR))
        self.edge_link_radius = self.min_dist * EDGE_LINK_RADIUS_MULTIPLIER
        self.points = self.generate_poisson_points(width, height, self.min_dist, self.overscan)
        self.background_surface = None
        self.background_key = None
        self.animated_backlight_surface = None
        self.animated_backlight_key = None
        self.rebuild_dynamic_edges(width, height)
        inside_count = sum(1 for p in self.points if 0 <= p["x"] <= width and 0 <= p["y"] <= height)
        print(f"neon-bg-flow[{self.monitor_name}]: {inside_count}/{len(self.points)} visible points, {len(self.edges)} edges, min_dist={self.min_dist:.1f}, link_radius={self.edge_link_radius:.1f}, overscan={self.overscan:.1f}", flush=True)

    def choose_recycle_position(self, point, width, height):
        self.spawn_counter += 1
        spawn_y_min = -self.overscan - 150.0
        spawn_y_max = -self.overscan + 40.0
        x_min = -self.overscan * 0.92
        x_max = width + self.overscan * 0.92
        best_x = self.rng.uniform(x_min, x_max)
        best_y = self.rng.uniform(spawn_y_min, spawn_y_max)
        best_score = -1.0
        desired2 = (self.min_dist * 0.92) ** 2
        relevant = [q for q in self.points if q is not point and q["y"] <= height * 0.34]
        golden = 0.6180339887498949
        base = (self.spawn_counter * golden) % 1.0
        for attempt in range(42):
            lane = (base + attempt * golden) % 1.0
            x = x_min + lane * (x_max - x_min) + self.rng.uniform(-self.min_dist * 0.42, self.min_dist * 0.42)
            x = max(x_min, min(x_max, x))
            y = self.rng.uniform(spawn_y_min, spawn_y_max)
            score = 10_000_000.0
            for q in relevant:
                dx, dy = q["x"] - x, q["y"] - y
                score = min(score, dx * dx + dy * dy)
                if score < desired2 * 0.42:
                    break
            if score > best_score:
                best_score, best_x, best_y = score, x, y
            if score >= desired2:
                break
        return best_x, best_y

    def recycle_point_if_needed(self, p, width, height):
        if p["y"] <= height + self.overscan + 80.0:
            return False
        x, y = self.choose_recycle_position(p, width, height)
        fresh = self.make_point(self.rng, x, y, width, height)
        p.clear()
        p.update(fresh)
        p["vx"] = self.rng.uniform(-1.0, 1.0)
        p["vy"] = self.rng.uniform(-0.6, 0.8)
        self.edge_dirty = True
        self.last_edge_rebuild_time = 0.0
        return True

    def update_physics(self, dt, width, height):
        dt = clamp(dt, 0.001, 0.040)
        damping = math.exp(-VELOCITY_DAMPING * dt)
        max_speed = 0.0
        recycled = False
        recycled_indices = []
        left_bound = -self.overscan
        right_bound = width + self.overscan
        for idx, p in enumerate(self.points):
            if p["x"] < left_bound:
                p["vx"] += (left_bound - p["x"]) * BOUNDARY_STIFFNESS * dt
            elif p["x"] > right_bound:
                p["vx"] += (right_bound - p["x"]) * BOUNDARY_STIFFNESS * dt
            p["vx"] *= damping
            p["vy"] *= damping
            if p["vy"] < 0.0:
                p["vy"] *= math.exp(-UPWARD_EXTRA_DAMPING * dt)
            p["vy"] += GRAVITY_ACCEL * dt
            p["vx"], p["vy"] = limit_vector(p["vx"], p["vy"], MAX_VELOCITY)
            p["x"] += p["vx"] * dt
            p["y"] += (FLOW_SPEED_PX_PER_SEC + p["vy"]) * dt
            max_speed = max(max_speed, math.sqrt(p["vx"] * p["vx"] + p["vy"] * p["vy"]))
            if self.recycle_point_if_needed(p, width, height):
                recycled = True
                recycled_indices.append(idx)
        if recycled:
            dead = set(recycled_indices)
            self.edges = [(a, b) for a, b in self.edges if a not in dead and b not in dead]
            self.edge_dirty = True
            self.last_edge_rebuild_time = 0.0
        return max_speed

    def maybe_rebuild_edges(self, now, max_speed, width, height):
        since_last = (now - self.last_edge_rebuild_time) * 1000.0
        since_mouse = now - self.last_mouse_time
        active = since_mouse < MOUSE_ACTIVE_SECONDS or max_speed > MOTION_ACTIVE_SPEED
        interval = EDGE_REBUILD_ACTIVE_MS if active else EDGE_REBUILD_IDLE_MS
        if (self.edge_dirty and since_last >= EDGE_REBUILD_MIN_MS) or since_last >= interval:
            self.rebuild_dynamic_edges(width, height)

    def ensure_background_surface(self, width, height):
        bg_key = (width, height)
        if self.background_key == bg_key and self.background_surface is not None:
            return
        self.background_key = bg_key
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        cr = cairo.Context(surface)
        bg = cairo.LinearGradient(0, 0, width, height)
        bg.add_color_stop_rgba(0.00, 0.018, 0.010, 0.038, 1.00)
        bg.add_color_stop_rgba(0.22, 0.040, 0.013, 0.072, 1.00)
        bg.add_color_stop_rgba(0.52, 0.055, 0.016, 0.092, 1.00)
        bg.add_color_stop_rgba(0.78, 0.028, 0.018, 0.068, 1.00)
        bg.add_color_stop_rgba(1.00, 0.007, 0.009, 0.025, 1.00)
        cr.rectangle(0, 0, width, height)
        cr.set_source(bg)
        cr.fill()
        vignette = cairo.RadialGradient(width / 2, height / 2, height * 0.10, width / 2, height / 2, height * 0.84)
        vignette.add_color_stop_rgba(0.00, 0, 0, 0, 0.00)
        vignette.add_color_stop_rgba(0.62, 0, 0, 0, 0.060)
        vignette.add_color_stop_rgba(1.00, 0, 0, 0, 0.34)
        cr.rectangle(0, 0, width, height)
        cr.set_source(vignette)
        cr.fill()
        self.background_surface = surface

    def ensure_animated_backlight_surface(self, width, height, now):
        frame = int((now * 1000.0) // ANIMATED_BACKLIGHT_UPDATE_MS)
        key = (width, height, frame)
        if self.animated_backlight_key == key and self.animated_backlight_surface is not None:
            return
        self.animated_backlight_key = key
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        cr = cairo.Context(surface)
        t = now * ANIMATED_BACKLIGHT_SPEED
        alpha = ANIMATED_BACKLIGHT_ALPHA
        x1 = width * (0.74 + 0.085 * math.sin(t * 0.73))
        y1 = height * (0.18 + 0.060 * math.cos(t * 0.61))
        r1 = height * (0.88 + 0.055 * math.sin(t * 0.47))
        g1 = cairo.RadialGradient(x1, y1, 0.0, x1, y1, r1)
        g1.add_color_stop_rgba(0.00, 0.95, 0.08, 0.76, alpha)
        g1.add_color_stop_rgba(0.42, 0.38, 0.04, 0.50, alpha * 0.38)
        g1.add_color_stop_rgba(1.00, 0, 0, 0, 0)
        cr.rectangle(0, 0, width, height)
        cr.set_source(g1)
        cr.fill()
        x2 = width * (0.13 + 0.070 * math.cos(t * 0.59))
        y2 = height * (0.86 + 0.045 * math.sin(t * 0.67))
        r2 = height * (0.76 + 0.060 * math.cos(t * 0.41))
        g2 = cairo.RadialGradient(x2, y2, 0.0, x2, y2, r2)
        g2.add_color_stop_rgba(0.00, 0.12, 0.12, 0.84, alpha * 0.82)
        g2.add_color_stop_rgba(0.46, 0.06, 0.04, 0.38, alpha * 0.32)
        g2.add_color_stop_rgba(1.00, 0, 0, 0, 0)
        cr.rectangle(0, 0, width, height)
        cr.set_source(g2)
        cr.fill()
        self.animated_backlight_surface = surface

    def visibility_fade(self, x, y, width, height):
        fx_left = smootherstep((x + FADE_ZONE) / FADE_ZONE)
        fx_right = smootherstep((width + FADE_ZONE - x) / FADE_ZONE)
        fy_top = smootherstep((y + FADE_ZONE) / FADE_ZONE)
        fy_bottom = smootherstep((height + FADE_ZONE - y) / FADE_ZONE)
        return clamp01(fx_left * fx_right * fy_top * fy_bottom)

    def edge_length_alpha(self, distance):
        fade_start = self.edge_link_radius * EDGE_FADE_START_MULTIPLIER
        fade_end = self.edge_link_radius * EDGE_FADE_END_MULTIPLIER
        if distance <= fade_start:
            shortness = 1.0 - distance / max(1.0, fade_start)
            return EDGE_ALPHA * (1.0 + shortness * (EDGE_SHORT_ALPHA_BOOST - 1.0))
        if distance >= fade_end:
            return EDGE_LONG_ALPHA_FLOOR
        t = (distance - fade_start) / max(1.0, fade_end - fade_start)
        fade = 1.0 - smootherstep(t)
        return EDGE_LONG_ALPHA_FLOOR + (EDGE_ALPHA - EDGE_LONG_ALPHA_FLOOR) * fade

    def set_edge_gradient(self, cr, p, q, x1, y1, x2, y2, alpha):
        c1, c2 = p["color"], q["color"]
        mid = color_mix(c1, c2, 0.5)
        gradient = cairo.LinearGradient(x1, y1, x2, y2)
        gradient.add_color_stop_rgba(0.00, c1[0], c1[1], c1[2], alpha)
        gradient.add_color_stop_rgba(0.50, mid[0], mid[1], mid[2], alpha * 0.88)
        gradient.add_color_stop_rgba(1.00, c2[0], c2[1], c2[2], alpha)
        cr.set_source(gradient)

    def draw_edges(self, cr, width, height):
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_line_width(EDGE_WIDTH)
        pad = FADE_ZONE + 28.0
        for a, b in self.edges:
            p, q = self.points[a], self.points[b]
            x1, y1, x2, y2 = p["x"], p["y"], q["x"], q["y"]
            if not self.segment_visible(x1, y1, x2, y2, width, height, pad):
                continue
            dx, dy = x2 - x1, y2 - y1
            distance = math.sqrt(dx * dx + dy * dy)
            length_alpha = self.edge_length_alpha(distance)
            fade1 = self.visibility_fade(x1, y1, width, height)
            fade2 = self.visibility_fade(x2, y2, width, height)
            alpha = length_alpha * max(fade1, fade2, 0.22)
            if alpha <= 0.002:
                continue
            self.set_edge_gradient(cr, p, q, x1, y1, x2, y2, alpha)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.stroke()

    def draw_points(self, cr, width, height):
        cr.set_operator(cairo.OPERATOR_ADD)
        pad = FADE_ZONE + 80.0
        for p in self.points:
            x, y = p["x"], p["y"]
            if x < -pad or x > width + pad or y < -pad or y > height + pad:
                continue
            alpha = self.visibility_fade(x, y, width, height)
            if alpha <= 0.01:
                continue
            sprite, center = p["sprite"], p["sprite_center"]
            cr.set_source_surface(sprite, x - center, y - center)
            cr.paint_with_alpha(alpha)
        cr.set_operator(cairo.OPERATOR_OVER)

    def draw(self, _area, cr, width, height):
        self.ensure_layout(width, height)
        self.ensure_background_surface(width, height)
        cr.set_source_surface(self.background_surface, 0, 0)
        cr.paint()
        now = time.monotonic()
        self.ensure_animated_backlight_surface(width, height, now)
        if self.animated_backlight_surface is not None:
            cr.set_operator(cairo.OPERATOR_OVER)
            cr.set_source_surface(self.animated_backlight_surface, 0, 0)
            cr.paint()
        if self.points:
            self.draw_edges(cr, width, height)
            self.draw_points(cr, width, height)

    def tick(self):
        now = time.monotonic()
        raw_dt = now - self.last_tick_time
        self.last_tick_time = now
        if raw_dt <= 0.0 or raw_dt > SMOOTH_DT_HARD_RESET:
            raw_dt = self.smoothed_dt
        raw_dt = clamp(raw_dt, SMOOTH_DT_MIN, SMOOTH_DT_MAX)
        self.smoothed_dt = self.smoothed_dt * (1.0 - SMOOTH_DT_BLEND) + raw_dt * SMOOTH_DT_BLEND
        dt = clamp(self.smoothed_dt, SMOOTH_DT_MIN, SMOOTH_DT_MAX)
        if self.layout_key is not None and self.points:
            width, height = self.current_width, self.current_height
            max_speed = self.update_physics(dt, width, height)
            self.maybe_rebuild_edges(now, max_speed, width, height)
            self.queue_draw()
        return True


class NeonBackground(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.windows = []
        self.canvases = []

    def do_activate(self):
        if not LayerShell.is_supported():
            raise RuntimeError("wlr-layer-shell is not supported by this compositor")
        display = Gdk.Display.get_default()
        monitors = display.get_monitors()
        count = monitors.get_n_items()
        print(f"neon-bg-flow: monitors detected: {count}", flush=True)
        for index in range(count):
            self.create_monitor_window(monitors.get_item(index), index)
        GLib.timeout_add(FRAME_INTERVAL_MS, self.tick)

    def get_monitor_name(self, monitor, index):
        for getter in ("get_connector", "get_description"):
            try:
                value = getattr(monitor, getter)()
                if value:
                    return value
            except Exception:
                pass
        return f"monitor-{index}"

    def create_monitor_window(self, monitor, index):
        geometry = monitor.get_geometry()
        width, height = int(geometry.width), int(geometry.height)
        monitor_name = self.get_monitor_name(monitor, index)
        print(f"neon-bg-flow: creating window for {monitor_name}: x={geometry.x}, y={geometry.y}, w={width}, h={height}", flush=True)
        window = Gtk.ApplicationWindow(application=self)
        window.set_title(f"neon-background-flow-{monitor_name}")
        window.set_decorated(False)
        window.set_focusable(False)
        window.set_resizable(False)
        window.set_default_size(width, height)
        window.set_size_request(width, height)
        LayerShell.init_for_window(window)
        LayerShell.set_namespace(window, f"neon-background-{monitor_name}")
        LayerShell.set_monitor(window, monitor)
        LayerShell.set_layer(window, LayerShell.Layer.BACKGROUND)
        LayerShell.set_keyboard_mode(window, LayerShell.KeyboardMode.NONE)
        LayerShell.set_exclusive_zone(window, -1)
        for edge in (LayerShell.Edge.TOP, LayerShell.Edge.BOTTOM, LayerShell.Edge.LEFT, LayerShell.Edge.RIGHT):
            LayerShell.set_anchor(window, edge, True)
            LayerShell.set_margin(window, edge, 0)
        canvas = NeonCanvas(monitor_name, width, height)
        window.set_child(canvas)
        window.present()
        self.windows.append(window)
        self.canvases.append(canvas)
        print(f"neon-bg-flow: presented {monitor_name}", flush=True)

    def tick(self):
        for canvas in self.canvases:
            canvas.tick()
        return True


if __name__ == "__main__":
    app = NeonBackground()
    app.run(None)
