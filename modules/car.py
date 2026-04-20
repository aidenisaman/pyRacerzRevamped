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

from . import misc

import math
import os

class Car(pygame.sprite.Sprite):
  '''Class representing the car belonging to a player'''

  def __init__(self, color, level):
    pygame.sprite.Sprite.__init__(self)
    image = pygame.image.load(os.path.join("sprites", "cars", "car" + str(color) + ".png")).convert_alpha()
    imageLight = pygame.image.load(os.path.join("sprites", "cars", "car" + str(color) + "B.png")).convert_alpha()
    

    # Car size scaling
    self.scale = 1.5   # car size control 
    

    self.sprite = pygame.sprite.RenderPlain(self)

    self.miniCar = pygame.transform.rotozoom(image, 0, misc.zoom)

    self.color = color

    if level > 3:
      level = 3
    if level < 1:
      level = 1

    self.level = level # 1,2,3

    if level == 1:
      self.maxSpeed = 3.5
    if level == 2:
      self.maxSpeed = 4.5
    if level == 3:
      self.maxSpeed = 6

    self.maxSpeedB = -0.66*self.level
    self.power = 0.0133*self.level

    self.sizeRect = int(30*misc.zoom)

    # TODO do not put it hardcoded...
    self.width = int(15*misc.zoom)
    self.height = int(24*misc.zoom)

    self.cars = []
    self.cars2 = []

    # For the 256 angle
    for j in range(0,256):
      
      # Rotate car without and with Red Light
      carRot=pygame.Surface((self.sizeRect,self.sizeRect), SRCALPHA|HWSURFACE, 16).convert_alpha()
      carRotLight=pygame.Surface((self.sizeRect,self.sizeRect), SRCALPHA|HWSURFACE, 16).convert_alpha()
      carRot2=pygame.Surface((self.sizeRect,self.sizeRect), SRCALPHA|HWSURFACE, 16).convert_alpha()
      carRotLight2=pygame.Surface((self.sizeRect,self.sizeRect), SRCALPHA|HWSURFACE, 16).convert_alpha()

      carRotRaw=pygame.transform.rotozoom(image, -j*360.0/256.0, misc.zoom)
      carRotLightRaw=pygame.transform.rotozoom(imageLight, -j*360.0/256.0, misc.zoom)

      carRot.blit(carRotRaw, ((self.sizeRect-carRotRaw.get_width())/2, (self.sizeRect-carRotRaw.get_height())/2) )
      carRotLight.blit(carRotLightRaw, ((self.sizeRect-carRotLightRaw.get_width())/2, (self.sizeRect-carRotLightRaw.get_height())/2) )

      # Create the car shadow
      carRotShade = carRot.copy()
      for x in range(0, carRotShade.get_width()):
        for y in range(0, carRotShade.get_height()):
         if carRotShade.get_at((x, y)) != (0,0,0,0):
           carRotShade.set_at((x, y), (50,50,50,100))

      carRot2.blit(carRotShade, (2,1))
      carRot2.blit(carRot, (0,0))
      carRotLight2.blit(carRotShade, (2,1))
      carRotLight2.blit(carRotLight, (0,0))

      self.cars.append(carRot2)
      self.cars2.append(carRotLight2)

      self.x = 0
      self.y = 0
      self.ox = 0
      self.oy = 0
      self.rect = pygame.Rect(int(self.x-self.sizeRect/2),int(self.y-self.sizeRect/2),self.sizeRect,self.sizeRect)
      self.movepos = [0.0,0.0]

  def reInit(self, track, rank):
    self.track = track

    self.blink = 0
    self.blinkCount = 0

    if rank == 0:
      self.x = 0
      self.y = 0
      self.ox = 0
      self.oy = 0
    elif rank == 1:
      self.x = track.startX1
      self.y = track.startY1
      self.ox = track.startX1
      self.oy = track.startY1
    elif rank == 2:
      self.x = track.startX2
      self.y = track.startY2
      self.ox = track.startX2
      self.oy = track.startY2
    elif rank == 3:
      self.x = track.startX3
      self.y = track.startY3
      self.ox = track.startX3
      self.oy = track.startY3
    else:
      if rank%2 == 1:
        precX = track.startX3
        precY = track.startY3
        for i in range(3, rank, 2):
          precX = precX + (track.startX2 - track.startX1)
          precY = precY + (track.startY2 - track.startY1)
          precX = precX + (track.startX3 - track.startX2)
          precY = precY + (track.startY3 - track.startY2)
      else:
        precX = track.startX2
        precY = track.startY2
        for i in range(2, rank, 2):
          precX = precX + (track.startX3 - track.startX2)
          precY = precY + (track.startY3 - track.startY2)
          precX = precX + (track.startX2 - track.startX1)
          precY = precY + (track.startY2 - track.startY1)
      self.x = precX
      self.y = precY
      self.ox = precX
      self.oy = precY

    self.rect = pygame.Rect(int(self.x-self.sizeRect/2),int(self.y-self.sizeRect/2),self.sizeRect,self.sizeRect)
    self.listCarRect = (self.rect, self.rect, self.rect, self.rect)

    self.angle = track.startAngle
    self.oldAngle = track.startAngle

    self.angleW = 0.0
    self.brake = 0.0
    self.slide = 0
    self.throttle = 0.0

    self.speed = 0.0
    self.accel = 0.0

    self.newSpeed = 0

    self.speedR = 0.0
    self.accelR = 0.0

    self.speedL = 0.0
    self.accelL = 0.0

    self.movepos = [0.0,0.0]

    # DRIFT MECHANIC - Initialisation
    self.drifting = False
    self.driftIntensity = 0.0

  def update(self):
    ''' Function called at each frame to update car sprite...
    It's the main computation method for car movement !'''

    # --- Hoist repeated trig/geometry: cos/sin called once instead of 8 times ---
    # Also exploits identities: cos(pi/2 - a) = sin(a),  sin(pi/2 - a) = cos(a)
    cos_a = math.cos(self.angle)
    sin_a = math.sin(self.angle)
    half_h = self.height / 2
    half_w = self.width / 2

    # Get the 4 important points of the car ~ 4 wheels
    coordN = (self.x - cos_a * half_h, self.y - sin_a * half_h)
    coordS = (self.x + cos_a * half_h, self.y + sin_a * half_h)
    coordE = (self.x + sin_a * half_w, self.y - cos_a * half_w)
    coordW = (self.x - sin_a * half_w, self.y + cos_a * half_w)
    coord0 = (int(coordN[0] - sin_a * half_w), int(coordN[1] + cos_a * half_w))
    coord1 = (int(coordN[0] + sin_a * half_w), int(coordN[1] - cos_a * half_w))
    coord2 = (int(coordS[0] - sin_a * half_w), int(coordS[1] + cos_a * half_w))
    coord3 = (int(coordS[0] + sin_a * half_w), int(coordS[1] - cos_a * half_w))

    minXX = min(coord0[0], coord1[0], self.x)
    maxXX = max(coord0[0], coord1[0], self.x)
    minYY = min(coord0[1], coord1[1], self.y)
    maxYY = max(coord0[1], coord1[1], self.y)
    carRectN = (minXX, minYY, maxXX - minXX, maxYY - minYY)
    
    minXX = min(coord2[0], coord3[0], self.x)
    maxXX = max(coord2[0], coord3[0], self.x)
    minYY = min(coord2[1], coord3[1], self.y)
    maxYY = max(coord2[1], coord3[1], self.y)
    carRectS = (minXX, minYY, maxXX - minXX, maxYY - minYY)
    
    minXX = min(coordE[0], self.x)
    maxXX = max(coordE[0], self.x)
    minYY = min(coordE[1], self.y)
    maxYY = max(coordE[1], self.y)
    carRectE = (minXX, minYY, maxXX - minXX, maxYY - minYY)
    
    minXX = min(coordW[0], self.x)
    maxXX = max(coordW[0], self.x)
    minYY = min(coordW[1], self.y)
    maxYY = max(coordW[1], self.y)
    carRectW = (minXX, minYY, maxXX - minXX, maxYY - minYY)
    
    self.listCarRect = (carRectN, carRectS, carRectE, carRectW)

    if min(coord0) < 0 or coord0[0] > 1023*misc.zoom or coord0[1] > 767*misc.zoom:
      g0 = 0
    else:
      g0 = self.track.trackF.get_at(coord0)[1]
    if min(coord1) < 0 or coord1[0] > 1023*misc.zoom or coord1[1] > 767*misc.zoom:
      g1 = 0
    else:
      g1 = self.track.trackF.get_at(coord1)[1]
    if min(coord2) < 0 or coord2[0] > 1023*misc.zoom or coord2[1] > 767*misc.zoom:
      g2 = 0
    else:
      g2 = self.track.trackF.get_at(coord2)[1]
    if min(coord3) < 0 or coord3[0] > 1023*misc.zoom or coord3[1] > 767*misc.zoom:
      g3 = 0
    else:
      g3 = self.track.trackF.get_at(coord3)[1]

    g = (g0 + g1 + g2 + g3)/4.0

    # ── DRIFT MECHANIC ──────────────────────────────────────────────────────
    # Drift triggers when the car is going fast AND steering sharply.
    # Lowered steer threshold to 0.4 so it triggers on normal sharp corners,
    # not only at full lock. Speed threshold kept at 0.60 (60% of max speed).
    DRIFT_SPEED_THRESHOLD = 0.60   # triggers at 60% of max speed
    DRIFT_STEER_THRESHOLD = 0.40   # triggers at 40% of full steer input

    speedRatio = self.speed / self.maxSpeed if self.maxSpeed > 0 else 0
    steerRatio = min(abs(self.angleW), 1.0)  

    speedExcess = max(0.0, (speedRatio - DRIFT_SPEED_THRESHOLD) / (1.0 - DRIFT_SPEED_THRESHOLD))
    steerExcess = max(0.0, (steerRatio - DRIFT_STEER_THRESHOLD) / (1.0 - DRIFT_STEER_THRESHOLD))

    targetDriftIntensity = speedExcess * steerExcess

    # Drift builds quickly (0.25) and fades slowly (0.88) for a natural feel.
    if targetDriftIntensity > self.driftIntensity:
      self.driftIntensity = 0.75 * self.driftIntensity + 0.25 * targetDriftIntensity  # fast build
    else:
      self.driftIntensity = 0.88 * self.driftIntensity + 0.12 * targetDriftIntensity  # slow fade

    self.drifting = self.driftIntensity > 0.05

    # Traction drops by 35% at full drift intensity 
    DRIFT_TRACTION_REDUCTION = 0.35
    tractionMultiplier = 1.0 - (self.driftIntensity * DRIFT_TRACTION_REDUCTION)

    # Compute Accel
    self.accel = self.power * (1.0*self.throttle - 1.7*self.brake) * (g/255.0) * tractionMultiplier

    if self.throttle == 0.0 and self.speed > 0:
      self.accel = self.accel - 0.005
    if self.throttle == 0.0 and self.speed < 0:
      self.accel = self.accel + 0.005

    oldSpeed = self.speed

    self.speed = self.speed + self.accel


    if self.speed <= self.maxSpeedB*(g/255.0):
      self.speed = self.maxSpeedB*(g/255.0)
      self.accel = 0

    if self.speed >= self.maxSpeed*(g/255.0):
      self.speed = self.maxSpeed*(g/255.0)

      self.accel = 0
    
    if self.speed < 0.005 and self.speed > -0.005:
      self.accel = 0.0
      self.speed = 0.0


    # Hoist per-frame constants for oversteer / braking thresholds
    _power_17 = self.power * 1.7
    _brake_thresh = _power_17 * (2.0 / 3)
    _speed_thresh = self.maxSpeed * (2.0 / 3)
    _abs_accel = abs(self.accel)

    # Compute Rotational Speed

    # - Rotational Accel depends only on present datas
    self.accelR=self.angleW*0.007

    # Take in account of rotating of the oversteering at braking
    # - Only acting when the car is braking hard
    # - Acting on the the Rotational Acceleration
    # - Memory because accelR is used the frame after
    # - Depending on the braking power (accel < 0)
    if self.accel < -_brake_thresh and self.accelR > 0 and self.speed > _speed_thresh:
      self.accelR = self.accelR + _abs_accel*0.08
    elif self.accel < -_brake_thresh and self.accelR < 0 and self.speed > _speed_thresh:
      self.accelR = self.accelR - _abs_accel*0.08
    
    # Take in account of understeering at acceleration
    # - Not acting when braking
    # - Acting on accelR
    #if (self.accel >= 0 and self.speed > self.maxSpeed*(2.0/3)) and ((self.speedL > 0.6 and oldSpeedL > 0.6) or (self.speedL < -0.6 and oldSpeedL < -0.6)):
    #if (self.accel >= 0 and self.speed > self.maxSpeed*(2.0/3)) and (self.speedL > 0.6 or self.speedL < -0.6):
    #if self.accel >= 0:# and self.accelR > 0:
    #  self.accelR = self.accelR


    if self.speed >= 0:
      self.speedR = 0.8*self.speedR + self.accelR
    else:
      self.speedR = 0.8*self.speedR - self.accelR

    if self.speedR < 0.003 and self.speedR > -0.003:
      self.accelR = 0.0
      self.speedR = 0.0

    oldoldAngle = self.oldAngle
    self.oldAngle = self.angle
    self.angle = self.angle + self.speedR

    if self.accel == self.power and self.speed > 0:
      self.angle = self.angle + 0.1*self.speedR*(1.5*self.maxSpeed-self.speed)

    # Compute Lateral Speed

    # The lateral acceleration is calculated with the 2 angle
    # - Lateral Accel depends only on present datas
    # - The formula is Flat = M v^2  / radius where radius=L/sin(angle)
    if self.angle-self.oldAngle != 0:
      _dx = (self.ox - self.x) / misc.zoom
      _dy = (self.oy - self.y) / misc.zoom
      radius = math.hypot(_dx, _dy) / math.sin(self.angle-self.oldAngle)
      if radius > 2000 or radius < -2000 or (radius < 1 and radius > -1):
        self.accelL = 0
      else:
        self.accelL = 5*self.speed*self.speed/radius
    else:
      self.accelL = 0

    # Take in account of sliding of the oversteering at braking
    # - Acting on speed and accelL to simulate lateral sliding
    # - Only acting when the braking is hard
    # - The accelL augmentation is based on accel (compared to the max accel)
    if self.accel < -_brake_thresh and self.speed > 0:
      self.accelL = self.accelL * (1 + 1.3*_abs_accel/_power_17)
      self.speed = self.speed - 0.6*_abs_accel

    # ── DRIFT MECHANIC - Professor lerp formula ──────────────────────────────
    # newXvel = alpha * P.x + (1 - alpha) * C.x
    # P.x  = forward speed (where the car wants to go)
    # C.x  = current lateral speed (where the car is sliding)
    # alpha = 0.65 → car keeps 35% of the slide for a visible real drift
    # Old alpha was 0.8 → only 20% slide, felt like mild understeer not a drift
    if self.drifting:
      ALPHA = 0.65
      # Target is 0.0 so lateral slip decays naturally 
      self.speedL = ALPHA * 0.0 + (1.0 - ALPHA) * self.speedL

    self.speedL = 0.2*self.speedL + self.accelL

    if self.speedL < 0.003 and self.speedL > -0.003:
      self.speedL = 0.0

    if self.angle < 0: 
      self.angle = self.angle + 2.0*math.pi
    if self.angle > 2.0*math.pi:
      self.angle = self.angle - 2.0*math.pi

    oldoldx = self.ox
    oldoldy = self.oy
    self.ox = self.x
    self.oy = self.y

    self.speed  = self.speed  * misc.zoom
    self.speedL = self.speedL * misc.zoom
    self.speedR = self.speedR * misc.zoom
    
    # Compute position update — hoist sqrt and acos to avoid 4 redundant calls
    if self.speedL != 0.0:
      _combined = math.hypot(self.speed, self.speedL)
      _drift = math.acos(self.speed / _combined)
      _eff_angle = self.angle - _drift if self.speedL > 0.0 else self.angle + _drift
      self.x -= math.cos(_eff_angle) * _combined
      self.y -= math.sin(_eff_angle) * _combined
    else:
      self.x -= math.cos(self.angle) * self.speed
      self.y -= math.sin(self.angle) * self.speed

    self.speed  = self.speed  / misc.zoom
    self.speedL = self.speedL / misc.zoom
    self.speedR = self.speedR / misc.zoom

    # Collision -> move to the last Nice position
    if (self.x < 16*misc.zoom or self.x > 1024*misc.zoom-14*misc.zoom or self.y < 16*misc.zoom or self.y > 768*misc.zoom-14*misc.zoom) or g0 == 0 or g1 == 0 or g2 == 0 or g3 == 0:
      self.x = oldoldx
      self.y = oldoldy
      self.angle = oldoldAngle
      self.speed = -0.2*oldSpeed
      self.speedL = 0
      # Cancel drift on collision
      self.driftIntensity = 0.0
      self.drifting = False

    self.movepos[0] = int(self.x) - int(self.ox)
    self.movepos[1] = int(self.y) - int(self.oy)

    self.rect.move_ip(self.movepos)

    if self.rect != (int(self.x-self.sizeRect/2), int(self.y-self.sizeRect/2), self.sizeRect, self.sizeRect):
      pass
      

    self.slide = 0
    # Compute tires slide
    if (self.accel >= 0.015 and self.speed <= 2 and self.speed > 0) or self.accelL > 0.4 or self.accelL < -0.4:
      self.slide = 1
    if self.accel < -0.005:
      self.slide = 2

    # Tire marks appear during drift when intensity is above 0.2
    if self.drifting and self.driftIntensity > 0.2:
      self.slide = 2

  def doAccel(self):
    self.throttle = self.throttle + 0.1
    if self.throttle > 1:
      self.throttle = 1

  def noAccel(self):
    self.throttle = self.throttle - 0.05
    if self.throttle < 0:
      self.throttle = 0

  def doBrake(self):
    self.brake = self.brake + 0.2
    if self.brake > 1:
      self.brake = 1

  def noBrake(self):
    self.brake = 0

  def doLeft(self):
    self.angleW = self.angleW - 0.2
    if self.angleW < -1:
      self.angleW = -1

  def doRight(self):
    self.angleW = self.angleW + 0.2
    if self.angleW > 1:
      self.angleW = 1

  def noWheel(self):
    self.angleW = 0.0 

