"""
The apparatus as RatInABox environments: the triple T with its perimeter returns and corridor walls, and the circular arena, built from the constants in scripts/build_blocks/maze.py.
"""

import numpy as np
from ratinabox.Environment import Environment

from scripts.build_blocks import maze

ARENA_VERTICES = 32
ROUND = 6
# A rotated maze is turned about the room centre. The registration records no pivot, so this is a drawing assumption.
PIVOT = (maze.ROOM[0] / 2.0, maze.ROOM[1] / 2.0)
WALL_COLOR = "0.45"


def rnd_point(p):
    """
    The point rounded to ROUND decimals, as a tuple, so junction nodes compare equal.
    """
    return (round(float(p[0]), ROUND), round(float(p[1]), ROUND))


def unit(p0, p1):
    """
    The unit vector from p0 to p1, rounded.
    """
    d = np.subtract(p1, p0, dtype=float)
    d = d / np.hypot(*d)
    return (round(float(d[0]), ROUND), round(float(d[1]), ROUND))


def triple_t_centerline():
    """
    The outbound centreline of maze.py plus the goal connectors, the top, the sides and the bottom return corridors, as (p0, p1) pairs. The return topology is inferred from the paper's figure, as in axis-of-travel-rnn.
    """
    h = maze.CORRIDOR_WIDTH / 2.0
    ex, ey = maze.ENVELOPE
    x0, y0 = (maze.ROOM[0] - ex) / 2.0, (maze.ROOM[1] - ey) / 2.0
    yb, yt = y0 + h, y0 + ey - h
    xl, xr = x0 + h, x0 + ex - h
    segments = [(seg["p0"], seg["p1"]) for seg in maze.CENTERLINE]
    goals = [maze.REWARD_SITES[name] for name in maze.GOAL_NAMES]
    segments += [(p, (p[0], yt)) for p in goals]
    top_x = sorted([xl] + [p[0] for p in goals] + [xr])
    segments += [((top_x[i], yt), (top_x[i + 1], yt)) for i in range(len(top_x) - 1)]
    foot = maze.REWARD_SITES["start"]
    segments += [((xl, yb), (xl, yt)), ((xr, yb), (xr, yt)), ((xl, yb), foot), (foot, (xr, yb))]
    return segments


def corridor_walls(centerline, width):
    """
    The two walls of every corridor and a cap at every dead end, junctions left open.
    """
    # For a wall on side n of a segment whose unit vector away from a node is u, the away vectors incident at that node
    # decide where the wall ends: n incident, pull back by h (a branch opens on this side); -n incident and -u not,
    # extend by h (the outer wall of an L corner); otherwise flush. Naive offsets seal every junction.
    h = width / 2.0
    incident = {}
    for p0, p1 in centerline:
        d = unit(p0, p1)
        incident.setdefault(rnd_point(p0), set()).add(d)
        incident.setdefault(rnd_point(p1), set()).add((-d[0], -d[1]))

    def endpoint(node, u, n):
        here = incident[rnd_point(node)]
        if n in here:
            return (node[0] + h * u[0] + h * n[0], node[1] + h * u[1] + h * n[1])
        if (-n[0], -n[1]) in here and (-u[0], -u[1]) not in here:
            return (node[0] - h * u[0] + h * n[0], node[1] - h * u[1] + h * n[1])
        return (node[0] + h * n[0], node[1] + h * n[1])

    walls = []
    for p0, p1 in centerline:
        d = unit(p0, p1)
        for n in ((-d[1], d[0]), (d[1], -d[0])):
            walls.append([rnd_point(endpoint(p0, d, n)), rnd_point(endpoint(p1, (-d[0], -d[1]), n))])
    for node, here in incident.items():
        if len(here) == 1:
            (u,) = here
            n = (-u[1], u[0])
            walls.append([rnd_point((node[0] + h * n[0], node[1] + h * n[1])),
                          rnd_point((node[0] - h * n[0], node[1] - h * n[1]))])
    return walls


def turned(points, degrees):
    """
    The points, any array ending in (x, y), turned about PIVOT by degrees counterclockwise.
    """
    a = np.deg2rad(degrees)
    rotation = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    return (np.asarray(points, dtype=float) - PIVOT) @ rotation.T + PIVOT


def triple_t(rotation_deg=0.0):
    """
    The triple T as a RatInABox Environment: the envelope as its boundary, the corridor walls, the reward sites as objects, all turned by rotation_deg about the room centre. The sites are also kept by name on reward_sites.
    """
    ex, ey = maze.ENVELOPE
    x0, y0 = (maze.ROOM[0] - ex) / 2.0, (maze.ROOM[1] - ey) / 2.0
    boundary = turned([(x0, y0), (x0 + ex, y0), (x0 + ex, y0 + ey), (x0, y0 + ey)], rotation_deg)
    walls = turned(corridor_walls(triple_t_centerline(), maze.CORRIDOR_WIDTH), rotation_deg)
    names = list(maze.REWARD_SITES)
    sites = turned([maze.REWARD_SITES[name] for name in names], rotation_deg)
    env = Environment(params={"boundary": boundary.tolist(), "walls": walls.tolist(), "objects": sites.tolist()})
    env.reward_sites = {name: (float(p[0]), float(p[1])) for name, p in zip(names, sites)}
    return env


def arena(centre=PIVOT):
    """
    The circular arena of maze.ARENA_DIAMETER as a RatInABox Environment, an ARENA_VERTICES sided boundary about centre.
    """
    angles = np.linspace(0.0, 2.0 * np.pi, ARENA_VERTICES, endpoint=False)
    radius = maze.ARENA_DIAMETER / 2.0
    boundary = [[centre[0] + radius * np.cos(a), centre[1] + radius * np.sin(a)] for a in angles]
    env = Environment(params={"boundary": boundary})
    env.reward_sites = {}
    return env


def draw(ax, env):
    """
    Draw the environment's walls (the boundary among them) and its named reward sites on ax, returning the artists.
    """
    artists = []
    for p0, p1 in np.asarray(env.walls):
        artists += ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=WALL_COLOR, lw=1.2, zorder=0)
    for name, (sx, sy) in env.reward_sites.items():
        artists += ax.plot(sx, sy, "o", color="0.3", ms=4, zorder=1)
        artists.append(ax.annotate(name, (sx, sy), textcoords="offset points", xytext=(4, 4), fontsize=7, color="0.3"))
    return artists
