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

  def play(self, track, rank):
    self.keyAccelPressed = 0
    self.keyBrakePressed = 0
    self.keyLeftPressed = 0
    self.keyRightPressed = 0

    Player.play(self, track, rank)

  def compute(self):
    '''Result a modification on keyXXXPressed'''

    # 1. Find for the 7 lines, the min point where g != 255
    coordN = (self.car.x - math.cos(self.car.angle)*self.car.height*1.2/2, self.car.y - math.sin(self.car.angle)*self.car.height*1.2/2)
    coordS = (self.car.x + math.cos(self.car.angle)*self.car.height*1.2/2, self.car.y + math.sin(self.car.angle)*self.car.height*1.2/2)
    coord0 = (int(coordN[0] - math.sin(self.car.angle)*self.car.width*1.2/2), int(coordN[1] + math.cos(self.car.angle)*self.car.width*1.2/2))
    coord1 = (int(coordN[0] + math.sin(self.car.angle)*self.car.width*1.2/2), int(coordN[1] - math.cos(self.car.angle)*self.car.width*1.2/2))
    #coord2 = (int(coordS[0] - math.sin(self.car.angle)*self.car.width*1.2/2), int(coordS[1] + math.cos(self.car.angle)*self.car.width*1.2/2))
    #coord3 = (int(coordS[0] + math.sin(self.car.angle)*self.car.width*1.2/2), int(coordS[1] - math.cos(self.car.angle)*self.car.width*1.2/2))
    
    minLine = []
    minLine.append(self.findMinObstacle(coord0[0], coord0[1], self.car.angle - math.pi/4.0))
    minLine.append(self.findMinObstacle(coord0[0], coord0[1], self.car.angle - 2.0*math.pi/5.0))
    minLine.append(self.findMinObstacle(coord0[0], coord0[1], self.car.angle - math.pi/5.0))

    # Take the worst possibility between the 2 axes
    minLine.append(min(self.findMinObstacle(coord0[0], coord0[1], self.car.angle), self.findMinObstacle(coord1[0], coord1[1], self.car.angle)))
    #minLine.append(self.findMinObstacle(self.car.x, self.car.y, self.car.angle))
    minLine.append(self.findMinObstacle(coord1[0], coord1[1], self.car.angle + math.pi/5.0))
    minLine.append(self.findMinObstacle(coord1[0], coord1[1], self.car.angle + 2.0*math.pi/5.0))
    minLine.append(self.findMinObstacle(coord1[0], coord1[1], self.car.angle + math.pi/4.0))

    # 2. Find the max of the minLines
    maxDist = -9999
    maxDistIndex = -1
    i = 0
    for line in minLine:
      if maxDist < line:
        maxDist = line
        maxDistIndex = i
      i = i + 1

    # Privileges the straight line
    if maxDist == minLine[3]:
      maxDistIndex = 3

    wallLimit1 = 300
    wallLimit2 = 400
    wallLimit3 = 400
    if self.level == 2:
      wallLimit1 = 450
      wallLimit2 = 600
      wallLimit3 = 600
    if self.level == 3:
      wallLimit1 = 600
      wallLimit2 = 800
      wallLimit3 = 800

    # If the car is surrounded by "No road" find the closer road
    if maxDist == 0:
      minLine = []
      minLine.append(self.findMinRoad(coord0[0], coord0[1], self.car.angle - math.pi/4.0))
      minLine.append(self.findMinRoad(coord0[0], coord0[1], self.car.angle - 2.0*math.pi/5.0))
      minLine.append(self.findMinRoad(coord0[0], coord0[1], self.car.angle - math.pi/5.0))

      # Take the worst possibility between the 2 axes
      minLine.append(self.findMinRoad(self.car.x, self.car.y, self.car.angle))
      minLine.append(self.findMinRoad(coord1[0], coord1[1], self.car.angle + math.pi/5.0))
      minLine.append(self.findMinRoad(coord1[0], coord1[1], self.car.angle + 2.0*math.pi/5.0))
      minLine.append(self.findMinRoad(coord1[0], coord1[1], self.car.angle + math.pi/4.0))
    
      # 2. Find the max of the minLines
      minDist = 9999
      minDistIndex = -1
      i = 0
      for line in minLine:
        if minDist > line:
          minDist = line
          minDistIndex = i
        i = i + 1

      # Privileges the straight line
      if minDist == minLine[3]:
        minDistIndex = 3
      
      self.keyAccelPressed = 1
      self.keyBrakePressed = 0
      if minDistIndex == [0] or minDistIndex == [1] or minDistIndex == [2]:
        self.keyLeftPressed = 1
      else:
        self.keyLeftPressed = 0
      if minDistIndex == [4] or minDistIndex == [5] or minDistIndex == [6]:
        self.keyRightPressed = 1
      else:
        self.keyRightPressed = 0      
    
    # The pseudo Wall depends on the speed Rate
    elif (self.car.speed > 0 and
          ((maxDist < wallLimit1*(self.car.speed/self.car.maxSpeed) and maxDistIndex == 3 and maxDist < 800) or
           (maxDist < wallLimit2*(self.car.speed/self.car.maxSpeed) and (maxDistIndex == 2 or maxDistIndex == 4) and maxDist < 800) or
           (maxDist < wallLimit3*(self.car.speed/self.car.maxSpeed) and (maxDistIndex == 1 or maxDistIndex == 5) and maxDist < 800) or
           (maxDistIndex == 0 or maxDistIndex == 6)
          )
         ):
      #print "FREIN " + str(maxDist) + " " + str(self.car.speed)
      if maxDistIndex == 3:
        self.keyAccelPressed = 0
        self.keyBrakePressed = 1
        self.keyLeftPressed = 0
        self.keyRightPressed = 0
      elif maxDistIndex == 2 or maxDistIndex == 1 or maxDistIndex == 0:
        self.keyAccelPressed = 0
        self.keyBrakePressed = 1
        self.keyLeftPressed = 1
        self.keyRightPressed = 0
      elif maxDistIndex == 4 or maxDistIndex == 5 or maxDistIndex == 6:
        self.keyAccelPressed = 0
        self.keyBrakePressed = 1
        self.keyLeftPressed = 0
        self.keyRightPressed = 1
    else:
      #print "ACCEL"
      if maxDistIndex == 3:
        self.keyAccelPressed = 1
        self.keyBrakePressed = 0
        # Try to center the car on the road
        if max(minLine[0], minLine[6]) - min(minLine[0], minLine[6]) > 100:
          #print "CORRECTION"
          if minLine[0] > minLine[6]:
            self.keyLeftPressed = 1
            self.keyRightPressed = 0
          else:
            self.keyLeftPressed = 0
            self.keyRightPressed = 1       
        else: 
          self.keyLeftPressed = 0
          self.keyRightPressed = 0
      elif maxDistIndex == 2:
        self.keyAccelPressed = 1
        self.keyBrakePressed = 0
        self.keyLeftPressed = 1
        self.keyRightPressed = 0
      elif maxDistIndex == 4:
        self.keyAccelPressed = 1
        self.keyBrakePressed = 0
        self.keyLeftPressed = 0
        self.keyRightPressed = 1
      elif maxDistIndex == 1:
        self.keyAccelPressed = 0
        self.keyBrakePressed = 0
        self.keyLeftPressed = 1
        self.keyRightPressed = 0
      elif maxDistIndex == 5:
        self.keyAccelPressed = 0
        self.keyBrakePressed = 0
        self.keyLeftPressed = 0
        self.keyRightPressed = 1

    if self.car.speed < 0.5:
      self.keyBrakePressed = 0

  def findMinObstacle(self, x, y, angle):
    dist = 0
    pix = None
    if x > 10 and x < 1014*misc.zoom and y > 10 and y < 758*misc.zoom:
      pix = self.car.track.trackF.get_at((int(x), int(y)))
    else:
      return dist
    while x > 10 and x < 1014*misc.zoom and y > 10 and y < 758*misc.zoom and dist < 600*misc.zoom and pix[1] == 255:
      # Be careful of the increasing of the dist on some tracks !!!
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

      # Checkpoints help us to find the right way
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
    if x > 10 and x < 1014*misc.zoom and y > 10 and y < 758*misc.zoom:
      pix = self.car.track.trackF.get_at((int(x), int(y)))
    else:
      return dist
    while x > 10 and x < 1014*misc.zoom and y > 10 and y < 758*misc.zoom and dist < 600*misc.zoom and pix[1] != 255:
      # Be careful of the increasing of the dist on some tracks !!!
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

      # Checkpoints help us to find the right way
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
