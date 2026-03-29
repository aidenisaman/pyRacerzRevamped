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
import pygame.surfarray

from . import track
from . import player
from . import menu
from . import misc

import array
import math
import os
import zlib

class Replay:
  '''Class representing a replay'''

  def __init__(self, repFile):
    '''Constructor'''

    self.repFile = repFile

    try:
      with open(self.repFile, "rb") as f:
        header = f.readline().decode()
        stringList = header.split()
        self.currentTrack = track.Track(stringList[1], int(stringList[2]))

        self.nbEnreg = int(stringList[3])

        nbPlayer = int(stringList[4])

        self.listPlayer = []
        for i in range(0, nbPlayer):
          self.listPlayer.append(player.ReplayPlayer(stringList[5+3*i], int(stringList[5+3*i+1]), int(stringList[5+3*i+2])))

        # Binary frame data: 5 signed 16-bit ints per player per frame,
        # zlib-compressed.  Falls back to the legacy space-separated text
        # format for old .rep files.
        raw = zlib.decompress(f.read())
        self.replayArray = array.array("h")
        try:
          self.replayArray.frombytes(raw)
        except Exception:
          # Legacy format: space-separated integer strings
          for elem in raw.split():
            self.replayArray.append(int(elem))
        self._replay_idx = 0

    except Exception as e:
      errorMenu = menu.SimpleTitleOnlyMenu(misc.titleFont, "cannot Load Replay !")
      misc.wait4Key()
      self.listPlayer = None
      print(e)
      return

  def _pop(self) -> int:
    """Return the next replay value by index (O(1)), advancing the pointer."""
    val = self.replayArray[self._replay_idx]
    self._replay_idx += 1
    return val

  def play(self):

    if self.listPlayer == None or self.listPlayer == []:
      return

    # Play music
    misc.startRandomMusic()

    for play in self.listPlayer:
      play.play(self.currentTrack)

    # Initialise clock
    clock = pygame.time.Clock()

    # Display the track
    misc.screen.blit(self.currentTrack.track, (0, 0))
    pygame.display.flip()

    nb = 0

    # Clear event queue
    pygame.event.clear()

    i = 0
    j = 0

    l = []

    popUp = misc.PopUp(self.currentTrack)

    # Speed of the replay (controlled by <- and -> )
    repSpeed = 1

    # bestRank is an array indexed by the lap number
    # It's used to indicate the Position of each player at each track Finish
    bestRank = [None]
    # 99 represents the maximum of Lap Number
    for r in range(1, 99):
      bestRank.append(1)

    while nb < self.nbEnreg:
      nb = nb + 1

      # Get the event keys
      for event in pygame.event.get():
    
        if event.type == QUIT:
          # Stop music
          misc.stopMusic()
          return
        elif event.type == KEYDOWN:
          if event.key == K_ESCAPE:
            # Stop music
            misc.stopMusic()
            return
          if event.key == K_LEFT and repSpeed > 0.2:
            repSpeed = repSpeed/1.5
          if event.key == K_RIGHT and repSpeed < 5:
            repSpeed = repSpeed*1.5
          if repSpeed < 1.2 and repSpeed > 0.8:
            repSpeed = 1


      for play in self.listPlayer:
        oldRect = play.car.rect
        l.append(oldRect.__copy__())
        misc.screen.blit(self.currentTrack.track, play.car.rect, play.car.rect)

      for play in self.listPlayer:
        play.car.ox = play.car.x
        play.car.oy = play.car.y
        play.car.x = self._pop()*misc.zoom
        play.car.y = self._pop()*misc.zoom
        play.car.oldAngle = play.car.angle
        play.car.angle = self._pop()/1000.0
        val = self._pop()
        if val >= 100:
          play.car.blink = 1
          val = val - 100
        else:
          play.car.blink = 0
        if val >= 10:
          play.car.brake = 1
          val = val - 10
        else:
          play.car.brake = 0

        play.car.slide = val

        self._pop()  # key-state field (not needed for playback)

        # Move the car
        play.car.movepos[0]=int(play.car.x) - int(play.car.ox)
        play.car.movepos[1]=int(play.car.y) - int(play.car.oy)
        play.car.rect.move_ip(play.car.movepos)

      # Display PopUp
      popUp.display()
      l.append(popUp.rect.__copy__())

      # Display the arrows
      if repSpeed <= 0.6:
        text = misc.bigFont.render("<<  ", 1, misc.lightColor)
        textRect = text.get_rect()
        textRect.centerx = 900*misc.zoom
        textRect.centery = 740*misc.zoom
        # Erase Past arrows
        misc.screen.blit(self.currentTrack.track, textRect, textRect)
        misc.screen.blit(text, textRect)
        l.append(textRect.__copy__())
      elif repSpeed < 1:
        text = misc.bigFont.render(" <  ", 1, misc.lightColor)
        textRect = text.get_rect()
        textRect.centerx = 900*misc.zoom
        textRect.centery = 740*misc.zoom
        # Erase Past arrows
        misc.screen.blit(self.currentTrack.track, textRect, textRect)
        misc.screen.blit(text, textRect)
        l.append(textRect.__copy__())
      elif repSpeed >= 3:
        text = misc.bigFont.render("  >>", 1, misc.lightColor)
        textRect = text.get_rect()
        textRect.centerx = 900*misc.zoom
        textRect.centery = 740*misc.zoom
        # Erase Past arrows
        misc.screen.blit(self.currentTrack.track, textRect, textRect)
        misc.screen.blit(text, textRect)
        l.append(textRect.__copy__())
      elif repSpeed > 1:
        text = misc.bigFont.render("  > ", 1, misc.lightColor)
        textRect = text.get_rect()
        textRect.centerx = 900*misc.zoom
        textRect.centery = 740*misc.zoom
        # Erase Past arrows
        misc.screen.blit(self.currentTrack.track, textRect, textRect)
        misc.screen.blit(text, textRect)
        l.append(textRect.__copy__())
      else:
        text = misc.bigFont.render("    ", 1, misc.lightColor)
        textRect = text.get_rect()
        textRect.centerx = 900*misc.zoom
        textRect.centery = 740*misc.zoom
        # Erase Past arrows
        misc.screen.blit(self.currentTrack.track, textRect, textRect)
        #misc.screen.blit(text, textRect)
        l.append(textRect.__copy__())

      self.currentTrack.track.lock()

      # Display cars
      for play in self.listPlayer:
        play.chrono = play.chrono + 1

        # Get infos on trackFunction
        color=self.currentTrack.trackF.get_at((int(play.car.x*misc.zoom), int(play.car.y*misc.zoom)))
        r=color[0]

        # Manage the checkpoints to count the nb of laps
        if self.currentTrack.reverse == 0 and play.raceFinish == 0:
          if r == play.lastCheckpoint + 16:
            play.lastCheckpoint = r
            #print "Checkpoint OK"
          # We finish a lap
          elif r == 16:
            # OK
            if play.lastCheckpoint == 16 * self.currentTrack.nbCheckpoint:
              play.lastCheckpoint = r
              play.nbLap = play.nbLap +1

              # Get the current rank (position)
              play.rank = bestRank[play.nbLap]
              bestRank[play.nbLap] = bestRank[play.nbLap] + 1

              # Get the best chrono   
              if play.chrono < play.bestChrono:
                play.bestChrono = play.chrono
                popUp.addElement(play.car, play.name + " L" + str(play.nbLap) + " P" + str(play.rank) + " " + misc.chrono2Str(play.chrono) + "B")
              else:
                popUp.addElement(play.car, play.name + " L" + str(play.nbLap) + " P" + str(play.rank) + " " + misc.chrono2Str(play.chrono))

              play.chrono = 0

            # NOK
            elif play.lastCheckpoint > 16:
              play.lastCheckpoint = r
              popUp.addElement(play.car, play.name + " L" + str(play.nbLap+1) + " MISSED")
              play.chrono = 0
        elif self.currentTrack.reverse == 1 and play.raceFinish == 0:
          if r != 0 and r == play.lastCheckpoint - 16:
            play.lastCheckpoint = r
            #print "Checkpoint OK"
          # We finish a lap
          elif r == 16 * self.currentTrack.nbCheckpoint:
            # OK
            if play.lastCheckpoint == 16:
              play.lastCheckpoint = r
              play.nbLap = play.nbLap +1
               # Get the current rank (position)
              play.rank = bestRank[play.nbLap]
              bestRank[play.nbLap] = bestRank[play.nbLap] + 1
               # Get the best chrono   
              if play.chrono < play.bestChrono:
                play.bestChrono = play.chrono
                popUp.addElement(play.car, play.name + " L" + str(play.nbLap) + " P" + str(play.rank) + " " + misc.chrono2Str(play.chrono) + "B")
              else:
                popUp.addElement(play.car, play.name + " L" + str(play.nbLap) + " P" + str(play.rank) + " " + misc.chrono2Str(play.chrono))
              play.chrono = 0

            # NOK
            elif play.lastCheckpoint < 16 * self.currentTrack.nbCheckpoint:
              play.lastCheckpoint = r
              popUp.addElement(play.car, play.name + " L" + str(play.nbLap+1) + " MISSED")
              play.chrono = 0

        # Use the blink to see if the player have finish the game
        if play.car.blink == 1:
          play.raceFinish = 1

        newRect = play.car.rect
        l.append(newRect.__copy__())

        # Change the sprite for the red lights
        if play.car.brake == 0:
          play.car.image=play.car.cars[int((256.0*play.car.angle/2.0/math.pi)%256)]
        else:
          play.car.image=play.car.cars2[int((256.0*play.car.angle/2.0/math.pi)%256)]

        # If there's something on the car (the car is in a tunnel), manage mask to hide the car
        part=pygame.Surface((play.car.sizeRect,play.car.sizeRect), HWSURFACE, 24).convert()
        part.blit(self.currentTrack.trackF, (0,0), (play.car.x-play.car.sizeRect/2, play.car.y-play.car.sizeRect/2, play.car.sizeRect, play.car.sizeRect))
        partArray = pygame.surfarray.array2d(part)
        aX = 0
        for arrayX in partArray:
          aY = 0
          for col in arrayX:
            if col % 256 != 0:
              play.car.image.set_at((aX, aY), (255, 255, 255, 0))
            aY = aY + 1
          aX = aX + 1

        # Display tires slide
        if play.car.slide == 1 or play.car.slide == 2:
          coordN = (play.car.x - math.cos(play.car.angle)*play.car.height*0.4, play.car.y - math.sin(play.car.angle)*play.car.height*0.4)
          coordS = (play.car.x + math.cos(play.car.angle)*play.car.height*0.4, play.car.y + math.sin(play.car.angle)*play.car.height*0.4)
          coord0 = (int(coordN[0] - math.sin(play.car.angle)*play.car.width*0.3), int(coordN[1] + math.cos(play.car.angle)*play.car.width*0.3))
          coord1 = (int(coordN[0] + math.sin(play.car.angle)*play.car.width*0.3), int(coordN[1] - math.cos(play.car.angle)*play.car.width*0.3))
          coord2 = (int(coordS[0] - math.sin(play.car.angle)*play.car.width*0.3), int(coordS[1] + math.cos(play.car.angle)*play.car.width*0.3))
          coord3 = (int(coordS[0] + math.sin(play.car.angle)*play.car.width*0.3), int(coordS[1] - math.cos(play.car.angle)*play.car.width*0.3))
          oldCoordN = (play.car.ox - math.cos(play.car.oldAngle)*play.car.height*0.4, play.car.oy - math.sin(play.car.oldAngle)*play.car.height*0.4)
          oldCoordS = (play.car.ox + math.cos(play.car.oldAngle)*play.car.height*0.4, play.car.oy + math.sin(play.car.oldAngle)*play.car.height*0.4)
          oldCoord0 = (int(oldCoordN[0] - math.sin(play.car.oldAngle)*play.car.width*0.3), int(oldCoordN[1] + math.cos(play.car.oldAngle)*play.car.width*0.3))
          oldCoord1 = (int(oldCoordN[0] + math.sin(play.car.oldAngle)*play.car.width*0.3), int(oldCoordN[1] - math.cos(play.car.oldAngle)*play.car.width*0.3))
          oldCoord2 = (int(oldCoordS[0] - math.sin(play.car.oldAngle)*play.car.width*0.3), int(oldCoordS[1] + math.cos(play.car.oldAngle)*play.car.width*0.3))
          oldCoord3 = (int(oldCoordS[0] + math.sin(play.car.oldAngle)*play.car.width*0.3), int(oldCoordS[1] - math.cos(play.car.oldAngle)*play.car.width*0.3))

          # Back tires
          if self.currentTrack.trackF.get_at(coord2)[2] != 255 and self.currentTrack.trackF.get_at(oldCoord2)[2] != 255:
            pygame.draw.line(self.currentTrack.track, (0,0,0), coord2, oldCoord2)
          if self.currentTrack.trackF.get_at(coord3)[2] != 255 and self.currentTrack.trackF.get_at(oldCoord3)[2] != 255:
            pygame.draw.line(self.currentTrack.track, (0,0,0), coord3, oldCoord3)

          # Also Front tires if it's a braking slide
          if play.car.slide == 2:
            if self.currentTrack.trackF.get_at(coord0)[2] != 255 and self.currentTrack.trackF.get_at(oldCoord0)[2] != 255:
              pygame.draw.line(self.currentTrack.track, (0,0,0), coord0, oldCoord0)
            if self.currentTrack.trackF.get_at(coord1)[2] != 255 and self.currentTrack.trackF.get_at(oldCoord1)[2] != 255:
              pygame.draw.line(self.currentTrack.track, (0,0,0), coord1, oldCoord1)
       

        # Blink = 0, no blink
        if play.car.blink == 0:
          newRect = play.car.rect
          l.append(newRect.__copy__())
          play.car.sprite.draw(misc.screen)

        # Blink = 1, fast blink indicating the end of the race
        if play.car.blink == 1 and play.car.blinkCount < 10:
          play.car.blinkCount = play.car.blinkCount + 1
          newRect = play.car.rect
          l.append(newRect.__copy__())

          # Display the car
          play.car.sprite.draw(misc.screen)

        elif play.car.blink == 1 and play.car.blinkCount >= 10:
          play.car.blinkCount = play.car.blinkCount +1

        if play.car.blink == 1 and play.car.blinkCount == 20:
          play.car.blinkCount = 0
      
      self.currentTrack.track.unlock()

      if i == 1:
        pygame.display.update(l)
        i=0
        l = []
      else:
        i=i+1

      # Make sure game doesn't run at more than 100 frames per second
      if repSpeed < 1:
        clock.tick(100*repSpeed)
      else:
        if j >= repSpeed-1:
          clock.tick(100)
          j=0
        else:
          j=j+1
      
    # Display the last PopUp
    popUp.display()
    l.append(popUp.rect.__copy__())

    text = pygame.transform.rotozoom(misc.bigFont.render("Replay finish, press a key to continue", 1, misc.lightColor), 20, 1)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.centery = misc.screen.get_rect().centery
    misc.screen.blit(text, textRect)

    pygame.display.flip()

    misc.wait4Key()
 
    self.computeScores()

    # Stop music
    misc.stopMusic()

  def computeScores(self):

    titleMenu = menu.SimpleTitleOnlyMenu(misc.titleFont, "raceResult")

    y = titleMenu.startY
    for play in self.listPlayer:

      # Test if the current player has the best chrono
      bestChrono = 1
      for play2 in self.listPlayer:
        if play.bestChrono > play2.bestChrono:
          bestChrono = 0
          break

      playCar = pygame.transform.rotozoom(pygame.image.load(os.path.join("sprites", "cars", "car" + str(play.car.color) + ".png")).convert_alpha(), 270, 1.2*misc.zoom)

      if bestChrono == 1:
        text = misc.titleFont.render(str(play.rank) + "' " + play.name + " :    >> " + misc.chrono2Str(play.bestChrono) + " <<", 1, misc.lightColor)
      else:
        text = misc.titleFont.render(str(play.rank) + "' " + play.name + " :       " + misc.chrono2Str(play.bestChrono), 1, misc.darkColor)

      # Display the car with statistics
      playCarRect = playCar.get_rect()
      textRect = text.get_rect()
      textRect.centerx = misc.screen.get_rect().centerx + (playCarRect.width + 20*misc.zoom) /2
      textRect.y = y + 80*play.rank*misc.zoom
      playCarRect.x = textRect.x - (playCarRect.width + 20*misc.zoom)
      playCarRect.centery = textRect.centery
      misc.screen.blit(playCar, playCarRect)
      misc.screen.blit(text, textRect)

    pygame.display.flip()
    
    misc.wait4Key()


