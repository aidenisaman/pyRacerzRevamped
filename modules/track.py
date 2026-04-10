# Copyright (C) 2005  Jujucece <jujucece@gmail.com>
#
# This file is part of pyRacerz.
#
# pyRacerz is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# pyRacerz is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyRacerz; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import pygame
from pygame.locals import *

import os
import configparser
import zlib
import math
import heapq

from . import misc

def getImageFromTrackName(name):

  # If it's a bonus (locked) track, act differently
  if name.startswith("bonus"):
    return pygame.image.fromstring(zlib.decompress(open(os.path.join("tracks", name + ".png"), "rb").read()), (1024, 768), "RGBA").convert()

  return pygame.image.load(os.path.join("tracks", name + ".png")).convert()

def getImageFFromTrackName(name):

  # If it's a bonus (locked) track, act differently
  if name.startswith("bonus"):
    return pygame.image.fromstring(zlib.decompress(open(os.path.join("tracks", name + "F.png"), "rb").read()), (1024, 768), "RGBA").convert()

  return pygame.image.load(os.path.join("tracks", name + "F.png")).convert()

class Track:
  '''Class representing a track (with the 2 track pictures)'''
  _ai_cache = {}

  def __init__(self, name, reverse=0):
    self.track = pygame.transform.scale(getImageFromTrackName(name), (int(1024*misc.zoom), int(768*misc.zoom)))
    self.trackF = pygame.transform.scale(getImageFFromTrackName(name), (int(1024*misc.zoom), int(768*misc.zoom)))
    # Optional nav-only AI surface. Keep trackF unchanged for game physics.
    self.trackF_bot_nav = None
    self.ai_nav_surface = self.trackF

    # Desert-specific nav map to prevent false underpass routing.
    if name == "desert":
      desert_nav_path = os.path.join("tracks", "desertFNewWithoutBridge.png")
      if os.path.exists(desert_nav_path):
        self.trackF_bot_nav = pygame.transform.scale(
          pygame.image.load(desert_nav_path).convert(),
          (int(1024*misc.zoom), int(768*misc.zoom))
        )
        self.ai_nav_surface = self.trackF_bot_nav

    # Generic optional nav map (e.g. cityF2.png) for other tracks.
    if self.trackF_bot_nav is None:
      bot_nav_path = os.path.join("tracks", name + "F2.png")
      if os.path.exists(bot_nav_path):
        self.trackF_bot_nav = pygame.transform.scale(
          pygame.image.load(bot_nav_path).convert(),
          (int(1024*misc.zoom), int(768*misc.zoom))
        )
        self.ai_nav_surface = self.trackF_bot_nav
    confFile = configparser.ConfigParser()
    confFile.read_file(open(os.path.join("tracks", name + ".conf"), "r"))

    self.name = name
    self.author = confFile.get("track", "author")
    self.nbCheckpoint = int(confFile.get("track", "nbCheckpoint"))

    # Flag use to race in the opposite way
    self.reverse = reverse

    if self.reverse == 0:
      section = "normal"
    else:
      section = "reverse"

    self.startX1 = int(confFile.get(section, "startX1"))*misc.zoom
    self.startY1 = int(confFile.get(section, "startY1"))*misc.zoom
    self.startX2 = int(confFile.get(section, "startX2"))*misc.zoom
    self.startY2 = int(confFile.get(section, "startY2"))*misc.zoom
    self.startX3 = int(confFile.get(section, "startX3"))*misc.zoom
    self.startY3 = int(confFile.get(section, "startY3"))*misc.zoom

    self.startAngle = float(confFile.get(section, "startAngle"))

    if name == "desert" and self.trackF_bot_nav is not None:
      nav_source = "desertFNewWithoutBridge"
    elif self.trackF_bot_nav is not None:
      nav_source = name + "F2"
    else:
      nav_source = "defaultF"

    cache_key = (name, reverse, int(misc.zoom * 1000), nav_source)
    cached_ai = Track._ai_cache.get(cache_key)
    if cached_ai is None:
      self._build_ai_pathway()
      Track._ai_cache[cache_key] = {
        "checkpoints": self.checkpoints,
        "cp_centroids": self.cp_centroids,
        "ai_paths": self.ai_paths,
      }
    else:
      self.checkpoints = cached_ai["checkpoints"]
      self.cp_centroids = cached_ai["cp_centroids"]
      self.ai_paths = cached_ai["ai_paths"]

  def _build_ai_pathway(self):
    print("Building Checkpoint A* Path...")
    grid_size = 16
    width, height = self.ai_nav_surface.get_size()

    def is_fast_road(x, y):
      if not (0 <= x < width and 0 <= y < height):
        return False
      if is_black_solid(x, y):
        return False
      return self.ai_nav_surface.get_at((x, y))[1] > 200

    def is_black_solid(x, y):
      if not (0 <= x < width and 0 <= y < height):
        return True

      nav_pix = self.ai_nav_surface.get_at((x, y))
      # Absolute black on navigation mask is always solid.
      if nav_pix[0] <= 5 and nav_pix[1] <= 5 and nav_pix[2] <= 5:
        return True

      # Also respect absolute black on the visual map.
      track_pix = self.track.get_at((x, y))
      if track_pix[0] <= 5 and track_pix[1] <= 5 and track_pix[2] <= 5:
        return True

      return False

    def get_blue(x, y):
      if not (0 <= x < width and 0 <= y < height):
        return 0
      return self.ai_nav_surface.get_at((x, y))[2]

    # ------------------------------------------------------------------
    # CHECKPOINT DETECTION  (FIX 1 + FIX 6)
    # ------------------------------------------------------------------
    # FIX 1: detect checkpoints at pixel resolution (not grid stride).
    #   To keep startup responsive we do a fast pass at step=2 first, then
    #   only rescan missing checkpoints at step=1.
    #
    # FIX 6: only collect pixels where g > 200 (fast road) when building
    #   the centroid.  Checkpoint stripes cross both fast road AND slow
    #   zones.  Including slow-zone pixels drags the centroid off the road
    #   and can place it inside a wall (critical on the mountain track where
    #   the CP line crosses the mountain obstacle).
    self.checkpoints = {r: 0 for r in range(16, self.nbCheckpoint * 16 + 1, 16)}
    cp_stats = {r: [0, 0, 0] for r in range(16, self.nbCheckpoint * 16 + 1, 16)}

    def scan_checkpoint_pixels(step, missing_only=None):
      for x in range(0, width, step):
        for y in range(0, height, step):
          pix = self.ai_nav_surface.get_at((x, y))
          r, g = pix[0], pix[1]
          if r > 0 and r % 16 == 0 and r <= self.nbCheckpoint * 16 and g > 200:
            if missing_only is not None and r not in missing_only:
              continue
            cp_stats[r][0] += x
            cp_stats[r][1] += y
            cp_stats[r][2] += 1

    # Fast pass first; fallback pass only for checkpoints still unseen.
    scan_checkpoint_pixels(step=2)
    missing = {cp for cp, stats in cp_stats.items() if stats[2] == 0}
    if missing:
      scan_checkpoint_pixels(step=1, missing_only=missing)

    for cp, stats in cp_stats.items():
      self.checkpoints[cp] = stats[2]


    def snap_to_grid(cx, cy, exclude=None):
      """Return nearest walkable grid node within 10 cells of (cx, cy),
      skipping any node in `exclude`."""
      if exclude is None:
        exclude = set()
      gx = (cx // grid_size) * grid_size
      gy = (cy // grid_size) * grid_size
      best = None
      best_d = float('inf')
      for dx in range(-10, 11):
        for dy in range(-10, 11):
          nx, ny = gx + dx * grid_size, gy + dy * grid_size
          if (nx, ny) in exclude:
            continue
          if 0 <= nx < width and 0 <= ny < height and is_fast_road(nx, ny):
            d = math.hypot(nx - cx, ny - cy)
            if d < best_d:
              best_d = d
              best = (nx, ny)
      return best

    self.cp_centroids = {}
    used_snaps = set()

    for cp in sorted(cp_stats.keys()):
      sx, sy, count = cp_stats[cp]
      if count == 0:
        continue
      cx = sx // count
      cy = sy // count

      snap = snap_to_grid(cx, cy)
      if snap is None:
        continue

      # Collision: another CP already owns this node — find the next best
      if snap in used_snaps:
        snap = snap_to_grid(cx, cy, exclude=used_snaps)
        if snap is None:
          continue

      self.cp_centroids[cp] = snap
      used_snaps.add(snap)

    def astar(start, goal):
      if start == goal:
        # Trivially adjacent CPs share a grid node; no waypoints needed.
        return []

      frontier = []
      heapq.heappush(frontier, (0, start))
      came_from  = {start: None}
      cost_so_far = {start: 0}
      final_goal = start

      while frontier:
        _, current = heapq.heappop(frontier)
        if math.hypot(current[0] - goal[0], current[1] - goal[1]) <= grid_size * 2:
          final_goal = current
          break

        for dx, dy in [(0, -grid_size), (0, grid_size), (-grid_size, 0), (grid_size, 0),
                       (-grid_size, -grid_size), (grid_size, grid_size),
                       (-grid_size,  grid_size), (grid_size, -grid_size)]:
          nx, ny = current[0] + dx, current[1] + dy
          if not is_fast_road(nx, ny):
            continue

          # Soft bridge / layer-transition penalty
          layer_cost = 5.0 if abs(int(get_blue(nx, ny)) - int(get_blue(*current))) > 50 else 0.0

          # Wall-avoidance: penalise nodes whose cardinal neighbours are off-road
          wall_penalty = 0.0
          for ox, oy in [(-grid_size, 0), (grid_size, 0), (0, -grid_size), (0, grid_size)]:
            cx2, cy2 = nx + ox, ny + oy
            if not (0 <= cx2 < width and 0 <= cy2 < height):
              wall_penalty += 10.0
              continue

            if is_black_solid(cx2, cy2):
              wall_penalty += 30.0
            elif not is_fast_road(cx2, cy2):
              wall_penalty += 10.0

          # Mountain-specific extra spacing from black obstacles to reduce
          # getting wedged while cornering around rock walls.
          if self.name == "mountain":
            for ox, oy in [(-grid_size, -grid_size), (grid_size, -grid_size),
                           (-grid_size,  grid_size), (grid_size,  grid_size)]:
              cx2, cy2 = nx + ox, ny + oy
              if 0 <= cx2 < width and 0 <= cy2 < height and is_black_solid(cx2, cy2):
                wall_penalty += 12.0

          move_cost = 1.414 if (dx != 0 and dy != 0) else 1.0
          new_cost  = cost_so_far[current] + move_cost + wall_penalty + layer_cost

          if (nx, ny) not in cost_so_far or new_cost < cost_so_far[(nx, ny)]:
            cost_so_far[(nx, ny)] = new_cost
            priority = new_cost + math.hypot(goal[0] - nx, goal[1] - ny)
            heapq.heappush(frontier, (priority, (nx, ny)))
            came_from[(nx, ny)] = current

      # Reconstruct path
      path    = []
      curr    = final_goal
      visited = set()
      while curr != start and curr is not None and curr not in visited:
        visited.add(curr)
        path.append(curr)
        curr = came_from.get(curr)
      path.reverse()
      return path

    # Build forward and reverse paths between every consecutive CP pair
    self.ai_paths = {}
    sorted_cps = sorted(self.cp_centroids.keys())
    for i in range(len(sorted_cps)):
      start_cp = sorted_cps[i]
      end_cp   = sorted_cps[(i + 1) % len(sorted_cps)]
      forward  = astar(self.cp_centroids[start_cp], self.cp_centroids[end_cp])
      self.ai_paths[(start_cp, end_cp)] = forward
      self.ai_paths[(end_cp, start_cp)] = forward[::-1]

    print("AI Checkpoint Paths Cached!")


def getAvailableTrackNames():
  # Find tracks with browsing and finding the 3 files
  listAvailableTrackNames = []

  listFiles = os.listdir("tracks")
  for fileTrack in listFiles:
    if fileTrack.endswith(".conf"):
      trackName = fileTrack.replace(".conf", "")
      track = 1

      # Test if the user has unlocked the Bonus Level
      try:
        if trackName.startswith("bonus") and misc.getUnlockLevel() < int(trackName.replace("bonus", "")):
          continue
      except Exception as e:
        continue

      for fileTrack2 in listFiles:
        if fileTrack2 == trackName + ".png":
           track = track + 1
        if fileTrack2 == trackName + "F.png":
           track = track + 1
      if track == 3:
        listAvailableTrackNames.append(trackName)
  return listAvailableTrackNames