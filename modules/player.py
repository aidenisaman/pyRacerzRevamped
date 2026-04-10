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

from . import car
from . import misc

import random
import math
import os


class Player:
  '''Virtual class for any pyRacerz player'''

  def __init__(self, name, carColor, level):
    '''Base constructor for any player'''
    self.car = car.Car(carColor, level)

    self.name = name
    self.level = level

    # Point and rank is used to compute tournament
    self.point = 0
    self.rank = 0

  # Input hooks to be overridden by subclasses
  def handle_keydown(self, key):
    return

  def handle_keyup(self, key):
    return

  def update_controls(self):
    return

  def play(self, track, rank):
    '''The player play on track with a rank'''

    self.bestChrono = 999999
    self.chrono = 0

    self.nbLap = 0

    self.raceFinish = 0

    if track.reverse == 0:
      self.lastCheckpoint = 16
    else:
      self.lastCheckpoint = track.nbCheckpoint * 16

    self.car.reInit(track, rank)

class ReplayPlayer(Player):
  '''Class for a Replay player'''

  def __init__(self, name, carColor, level):
    '''Constructor'''
    Player.__init__(self, name, carColor, level)

  def play(self, track):
    Player.play(self, track, 0)

class HumanPlayer(Player):
  '''Class for a human pyRacerz player'''

  def __init__(self, name, carColor, level, keyAccel, keyBrake, keyLeft, keyRight):
    '''Constructor'''
    Player.__init__(self, name, carColor, level)

    self.keyAccel = keyAccel
    self.keyBrake = keyBrake
    self.keyLeft = keyLeft
    self.keyRight = keyRight

    self.keyAccelPressed = 0
    self.keyBrakePressed = 0
    self.keyLeftPressed = 0
    self.keyRightPressed = 0

  def play(self, track, rank):
    self.keyAccelPressed = 0
    self.keyBrakePressed = 0
    self.keyLeftPressed = 0
    self.keyRightPressed = 0

    Player.play(self, track, rank)

  def handle_keydown(self, key):
    if key == self.keyAccel:
      self.keyAccelPressed = 1
    if key == self.keyBrake:
      self.keyBrakePressed = 1
    if key == self.keyLeft:
      self.keyLeftPressed = 1
    if key == self.keyRight:
      self.keyRightPressed = 1

  def handle_keyup(self, key):
    if key == self.keyAccel:
      self.keyAccelPressed = 0
    if key == self.keyBrake:
      self.keyBrakePressed = 0
    if key == self.keyLeft:
      self.keyLeftPressed = 0
    if key == self.keyRight:
      self.keyRightPressed = 0

  def update_controls(self):
    if self.keyAccelPressed == 1:
      self.car.doAccel()
    else:
      self.car.noAccel()
    if self.keyBrakePressed == 1:
      self.car.doBrake()
    else:
      self.car.noBrake()
    if self.keyLeftPressed == 1:
      self.car.doLeft()
    if self.keyRightPressed == 1:
      self.car.doRight()
    if self.keyLeftPressed == 0 and self.keyRightPressed == 0:
      self.car.noWheel()

class NetPlayer(Player):
  '''Class for a network pyRacerz player'''

  def __init__(self, name, carColor, level):
    '''Constructor'''
    Player.__init__(self, name, carColor, level)

class RobotPlayer(Player):
  '''Class for a robot pyRacerz player'''

  def __init__(self, carColor, level):
    '''Constructor'''
    Player.__init__(self, "BOT", carColor, level)

    self.keyAccelPressed = 0
    self.keyBrakePressed = 0
    self.keyLeftPressed = 0
    self.keyRightPressed = 0

    self.racePlayers = [self]

  def set_race_context(self, listPlayers):
    self.racePlayers = listPlayers

  def play(self, track, rank):
    self.keyAccelPressed = 0
    self.keyBrakePressed = 0
    self.keyLeftPressed = 0
    self.keyRightPressed = 0

    # Reset all AI state on new race
    self.current_path_key = None
    self.wp_idx = 0
    self.stuck_timer = 0
    self.stuck_attempts = 0
    self.is_reversing = False
    self.reverse_timer = 0
    self.forward_escape_timer = 0
    self.reverse_chain_count = 0
    self.escape_turn_bias = 1
    # FIX 3: Position-based stuck detection — track displacement over time,
    # not instantaneous speed, so braking mid-corner doesn't trigger a false
    # "stuck" event and cause unnecessary reversing manoeuvres.
    self._pos_history = []

    Player.play(self, track, rank)

  def compute(self):
    '''Calculate inputs based on precomputed A* path waypoints'''
    # 1. Determine target checkpoint
    target_cp = self.lastCheckpoint + 16 if self.car.track.reverse == 0 else self.lastCheckpoint - 16
    if target_cp > self.car.track.nbCheckpoint * 16:
      target_cp = 16
    if target_cp < 16:
      target_cp = self.car.track.nbCheckpoint * 16

    # 2. Get the precomputed route
    path_segment = getattr(self.car.track, 'ai_paths', {}).get((self.lastCheckpoint, target_cp), [])

    if not path_segment:
      # Fallback: no path cached — just accelerate and hope for the best
      self.keyAccelPressed = 1
      return

    # 3. Progressive waypoint tracking
    # Only allow the waypoint index to advance — never retreat.
    # This prevents U-turns caused by chasing a waypoint that was just passed.
    car_pos = (self.car.x, self.car.y)
    path_key = (self.lastCheckpoint, target_cp)
    if getattr(self, 'current_path_key', None) != path_key:
      self.current_path_key = path_key
      self.wp_idx = 0

    # Fast-forward wp_idx up to 20 steps to the closest upcoming waypoint
    search_end = min(len(path_segment), self.wp_idx + 20)
    min_dist = float('inf')
    best_idx = self.wp_idx
    for i in range(self.wp_idx, search_end):
      d = math.hypot(path_segment[i][0] - car_pos[0], path_segment[i][1] - car_pos[1])
      if d < min_dist:
        min_dist = d
        best_idx = i
    self.wp_idx = best_idx

    # Mountain uses a tighter 50px lookahead so the car doesn't steer diagonally
    # through the black mountain wall at the top-right corner.
    # All other tracks keep 100px for smoother high-speed steering.
    lookahead = 50 if self.car.track.name == "mountain" else 100

    # Find the next waypoint more than `lookahead` units ahead to use as the steering target
    target_wp = path_segment[-1]
    found = False
    for i in range(self.wp_idx, len(path_segment)):
      wp = path_segment[i]
      if math.hypot(wp[0] - car_pos[0], wp[1] - car_pos[1]) > lookahead:
        target_wp = wp
        found = True
        break

    # If we're right on top of this checkpoint, bleed into the next segment
    if not found:
      next_cp = target_cp + 16 if self.car.track.reverse == 0 else target_cp - 16
      if next_cp > self.car.track.nbCheckpoint * 16: next_cp = 16
      if next_cp < 16: next_cp = self.car.track.nbCheckpoint * 16
      next_segment = getattr(self.car.track, 'ai_paths', {}).get((target_cp, next_cp), [])
      for wp in next_segment:
        if math.hypot(wp[0] - car_pos[0], wp[1] - car_pos[1]) > lookahead:
          target_wp = wp
          break

    # 4. Steering
    # car.py moves: x -= cos(angle)*speed, so angle=0 → moving left.
    # Invert dx/dy to get the angle FROM the target TO the car.
    dx = self.car.x - target_wp[0]
    dy = self.car.y - target_wp[1]
    angle_to_wp = math.atan2(dy, dx)
    angle_diff  = (angle_to_wp - self.car.angle + math.pi) % (2 * math.pi) - math.pi

    self.keyAccelPressed = 1
    self.keyBrakePressed = 0

    if angle_diff > 0.15:
      self.keyRightPressed = 1
      self.keyLeftPressed  = 0
      if angle_diff > 0.8 and abs(self.car.speed) > 1.5:
        self.keyBrakePressed = 1   # Hard brake on sharp turns
      if angle_diff > 0.5:
        self.keyAccelPressed = 0   # Coast through medium turns
    elif angle_diff < -0.15:
      self.keyLeftPressed  = 1
      self.keyRightPressed = 0
      if angle_diff < -0.8 and abs(self.car.speed) > 1.5:
        self.keyBrakePressed = 1
      if angle_diff < -0.5:
        self.keyAccelPressed = 0
    else:
      self.keyLeftPressed  = 0
      self.keyRightPressed = 0

    # ------------------------------------------------------------------
    # 5. Unstuck logic  (FIX 3 + FIX 4)
    # ------------------------------------------------------------------
    # FIX 3: Position-history-based stuck detection.
    # The original trigger was abs(speed) < 0.5 which fires during any
    # normal hard brake or tight corner, causing the bot to reverse
    # unnecessarily mid-race.  Instead we measure total displacement over
    # the last 60 frames (~1 s at 60 fps).  Only if the car has barely moved
    # is it genuinely wedged against a wall.
    if not hasattr(self, '_pos_history'):
      self._pos_history = []
    if not hasattr(self, 'stuck_timer'):
      self.stuck_timer   = 0
      self.stuck_attempts = 0
      self.is_reversing  = False
      self.reverse_timer = 0
      self.forward_escape_timer = 0
      self.reverse_chain_count = 0
      self.escape_turn_bias = 1

    self._pos_history.append((self.car.x, self.car.y))
    if len(self._pos_history) > 90:
      self._pos_history.pop(0)

    # --- Execute active reversing manoeuvre ---
    if getattr(self, 'is_reversing', False):
      self.reverse_timer -= 1

      if self.stuck_attempts % 2 == 0:
        # Reverse + steer left
        self.keyAccelPressed = 0; self.keyBrakePressed = 1
        self.keyLeftPressed  = 1; self.keyRightPressed = 0
      else:
        # Reverse + steer right
        self.keyAccelPressed = 0; self.keyBrakePressed = 1
        self.keyLeftPressed  = 0; self.keyRightPressed = 1

      if self.reverse_timer <= 0:
        self.is_reversing = False
        self.stuck_attempts += 1
        self.reverse_chain_count += 1
        self.stuck_timer   = 0
        # Always force a forward burst after reverse so the bot cannot
        # get trapped in reverse-only recovery cycles.
        self.forward_escape_timer = 45
        # FIX 4: After a reversing manoeuvre the car faces a different
        # direction and the stale wp_idx now points at a waypoint that is
        # behind the car.  Clearing current_path_key forces a fresh
        # nearest-waypoint search on the very next frame.
        self.current_path_key = None
        self.wp_idx = 0
        self._pos_history.clear()
      return

    # --- Mandatory forward recovery phase after a reverse cycle ---
    if getattr(self, 'forward_escape_timer', 0) > 0:
      self.forward_escape_timer -= 1
      self.keyAccelPressed = 1
      self.keyBrakePressed = 0

      # During the first half of forced forward recovery, use a turn bias
      # to break out of trap pockets. Then resume normal route steering.
      if self.forward_escape_timer > 22:
        if self.escape_turn_bias > 0:
          self.keyRightPressed = 1
          self.keyLeftPressed = 0
        else:
          self.keyLeftPressed = 1
          self.keyRightPressed = 0
      else:
        if angle_diff > 0.15:
          self.keyRightPressed = 1
          self.keyLeftPressed  = 0
        elif angle_diff < -0.15:
          self.keyLeftPressed  = 1
          self.keyRightPressed = 0
        else:
          self.keyLeftPressed  = 0
          self.keyRightPressed = 0

      # If we are clearly moving again, stop forcing forward early.
      if len(self._pos_history) >= 20:
        oldest = self._pos_history[-20]
        recent_disp = math.hypot(self.car.x - oldest[0], self.car.y - oldest[1])
        if recent_disp > 25.0:
          self.forward_escape_timer = 0
          self.reverse_chain_count = 0
      return

    # --- Check for stuck condition ---
    if len(self._pos_history) >= 60:
      oldest = self._pos_history[0]
      displacement = math.hypot(self.car.x - oldest[0], self.car.y - oldest[1])
      if displacement < 20.0:
        self.stuck_timer += 1
      else:
        self.stuck_timer = 0
        if displacement > 120.0 and self.car.speed > 0.5:
          # Decay attempts slowly after strong forward progress so we still
          # preserve alternating recovery behavior in tough sections.
          self.stuck_attempts = max(0, self.stuck_attempts - 1)
          self.reverse_chain_count = 0

    if self.stuck_timer > 5:
      # Hard cap consecutive reverse cycles to avoid mountain finish-line
      # deadlocks where reverse never creates enough clearance.
      if self.reverse_chain_count >= 3:
        self.is_reversing = False
        self.forward_escape_timer = 70 if self.car.track.name == "mountain" else 55
        self.escape_turn_bias *= -1
        self.stuck_timer = 0
        self.current_path_key = None
        self.wp_idx = 0
        self._pos_history.clear()
        return

      self.is_reversing  = True
      self.reverse_timer = min(90, 30 + self.stuck_attempts * 20)
      self.stuck_timer   = 0

  def update_controls(self):
    self.compute()
    if self.keyAccelPressed == 1:
      self.car.doAccel()
    else:
      self.car.noAccel()
    if self.keyBrakePressed == 1:
      self.car.doBrake()
    else:
      self.car.noBrake()
    if self.keyLeftPressed == 1:
      self.car.doLeft()
    if self.keyRightPressed == 1:
      self.car.doRight()
    if self.keyLeftPressed == 0 and self.keyRightPressed == 0:
      self.car.noWheel()

  def findMinObstacle(self, x, y, angle):
    dist = 0
    pix = None
    prev_blue = 0
    if x > 10 and x < 1014*misc.zoom and y > 10 and y < 758*misc.zoom:
      pix = self.car.track.trackF.get_at((int(x), int(y)))
      prev_blue = pix[2]
    else:
      return dist
    while x > 10 and x < 1014*misc.zoom and y > 10 and y < 758*misc.zoom and dist < 600*misc.zoom and pix[1] == 255:
      if abs(pix[2] - prev_blue) > 50:
        break
      prev_blue = pix[2]
      if dist < 10*misc.zoom:
        step = 1.0
      elif dist < 40*misc.zoom:
        step = 5.0*misc.zoom
      elif dist < 100*misc.zoom:
        step = 10.0*misc.zoom
      elif dist < 200*misc.zoom:
        step = 30.0*misc.zoom
      elif dist < 600*misc.zoom:
        step = 60.0*misc.zoom
      x = x-math.cos(angle)*step
      y = y-math.sin(angle)*step
      dist = dist + step
      if self.car.track.reverse == 0 and pix[0] == self.lastCheckpoint + 16:
        dist = dist + 200*misc.zoom
      if self.car.track.reverse == 0 and pix[0] != 0 and pix[0] == self.lastCheckpoint - 16:
        dist = dist - 100*misc.zoom
      if self.car.track.reverse == 1 and pix[0] == self.lastCheckpoint - 16:
        dist = dist + 200*misc.zoom
      if self.car.track.reverse == 1 and pix[0] != 0 and pix[0] == self.lastCheckpoint + 16:
        dist = dist - 100*misc.zoom
      if x > 10 and x < 1014*misc.zoom and y > 10 and y < 758*misc.zoom:
        pix = self.car.track.trackF.get_at((int(x), int(y)))
      else:
        dist = dist - 100*misc.zoom
    return dist

  def findMinRoad(self, x, y, angle):
    dist = 0
    pix = None
    prev_blue = 0
    if x > 10 and x < 1014*misc.zoom and y > 10 and y < 758*misc.zoom:
      pix = self.car.track.trackF.get_at((int(x), int(y)))
      prev_blue = pix[2]
    else:
      return dist
    while x > 10 and x < 1014*misc.zoom and y > 10 and y < 758*misc.zoom and dist < 600*misc.zoom and pix[1] != 255:
      if abs(pix[2] - prev_blue) > 50:
        break
      prev_blue = pix[2]
      if dist < 10*misc.zoom:
        step = 1.0
      elif dist < 40*misc.zoom:
        step = 5.0*misc.zoom
      elif dist < 100*misc.zoom:
        step = 10.0*misc.zoom
      elif dist < 200*misc.zoom:
        step = 30.0*misc.zoom
      elif dist < 600*misc.zoom:
        step = 60.0*misc.zoom
      x = x-math.cos(angle)*step
      y = y-math.sin(angle)*step
      dist = dist + step
      if self.car.track.reverse == 0 and pix[0] == self.lastCheckpoint + 16:
        dist = dist - 400*misc.zoom
      if self.car.track.reverse == 0 and pix[0] != 0 and pix[0] == self.lastCheckpoint - 16:
        dist = dist + 100*misc.zoom
      if self.car.track.reverse == 1 and pix[0] == self.lastCheckpoint - 16:
        dist = dist - 400*misc.zoom
      if self.car.track.reverse == 1 and pix[0] != 0 and pix[0] == self.lastCheckpoint + 16:
        dist = dist + 100*misc.zoom
      if x > 10 and x < 1014*misc.zoom and y > 10 and y < 758*misc.zoom:
        pix = self.car.track.trackF.get_at((int(x), int(y)))
      else:
        dist = dist + 1000*misc.zoom
    return dist