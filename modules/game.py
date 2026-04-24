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

import random
import math
import array
import zlib

from . import track
from . import menu
from . import misc
from . import collision

import sys
import os
import datetime

class Game:
  '''Class representing a game: Tournament or Single Race'''

  def __init__(self, gameType, listTrackName=None, listPlayer=None, maxLapNb=-1):
    '''Constructor'''

    self.gameType = gameType
    self.listTrackName = listTrackName
    self.listPlayer = listPlayer
    self.maxLapNb = maxLapNb

  def play(self):

    if self.gameType == None or self.listTrackName == None or self.listPlayer == None or self.maxLapNb == -1:
      print ("Incomplete game")
      return

    # For each track
    for currentTrackName in self.listTrackName:
      try:
        currentTrack = track.Track(currentTrackName[0], currentTrackName[1])
      except Exception as e:
        print("Cannot load track : ")
        print(e)
        sys.exit(1)

      # Play music
      #misc.startRandomMusic()

      # Put players on the rank
      # If it's the first time do Randomly
      if currentTrackName == self.listTrackName[0]:
        listRank = []
        for play in self.listPlayer:
          rank = -1
          while rank in listRank or rank == -1:
            rank = random.randint(1, len(self.listPlayer))
          listRank.append(rank)
          play.play(currentTrack, rank)
      # Else do the inv of the last Race
      else:
        for play in self.listPlayer:
          play.play(currentTrack, len(self.listPlayer) - play.rank + 1)

      # Initialise clock
      clock = pygame.time.Clock()
      # Broad-phase grid: cell_size ~2× car sizeRect (30*zoom) for efficient hashing
      _collision_grid = collision.SpatialGrid(int(64 * misc.zoom))

      # Let AI players inspect the race roster when using new architecture.
      for play in self.listPlayer:
        if hasattr(play, "set_race_context"):
          play.set_race_context(self.listPlayer)


      # Display player names and cars blinking...
      for i in range(0, 4):

        # Display the track
        misc.screen.blit(currentTrack.track, (0, 0))

        # Display the player names
        for play in self.listPlayer:
          text = misc.popUpFont.render(play.name, 1, misc.lightColor, (0, 0, 0))
          textRect = text.get_rect()
          textRect.centerx = play.car.x
          textRect.centery = play.car.y
          misc.screen.blit(text, textRect)

        pygame.display.flip() 
        pygame.time.delay(400)

        # Display the track
        misc.screen.blit(currentTrack.track, (0, 0))

        # Display the cars
        for play in self.listPlayer:
          play.car.image=play.car.cars[int((256.0*play.car.angle/2.0/math.pi)%256)]
          play.car.sprite.draw(misc.screen)

        pygame.display.flip() 
        pygame.time.delay(400)

      i = 0

      l = []

      popUp = misc.PopUp(currentTrack)

      raceFinish = 0

      masterChrono = 0

      replayArray = array.array("h")

      # bestRank is an array indexed by the lap number
      # It's used to indicate the Position of each player at each track Finish
      bestRank = [None]
      for r in range(1, self.maxLapNb+1):
        bestRank.append(1)

      # Display Lights (Red, Orange, Green - like traffic light)
      imgFireG = pygame.transform.rotozoom(pygame.image.load(os.path.join("sprites", "grey.png")).convert_alpha(), 0, misc.zoom)
      misc.screen.blit(imgFireG, (10*misc.zoom,10*misc.zoom))
      misc.screen.blit(imgFireG, (90*misc.zoom,10*misc.zoom))
      misc.screen.blit(imgFireG, (170*misc.zoom,10*misc.zoom))
      pygame.display.flip()
      pygame.time.delay(1000)

      # Prepare countdown font
      countdownFont = pygame.font.Font(None, int(150*misc.zoom))

      # Try to load countdown sound: prefer project `sounds/`, else copy from Downloads, else fall back to bundled countdowns
      # Load countdown sound only from project files
      countdown_sound = None
      countdown_channel = None

      for candidate in (
          "mixkit-melodic-race-countdown-1955.wav",
          "countdown_go.wav",
          "race_start.wav",
          "countdown_3.wav",
          "countdown_2.wav",
          "countdown_1.wav",
      ):
          cand_path = os.path.join("sounds", candidate)
          if os.path.exists(cand_path):
              try:
                  countdown_sound = pygame.mixer.Sound(cand_path)
                  break
              except Exception:
                  countdown_sound = None

      # Show RED light (first signal) with countdown "3"
      imgFireRed = pygame.transform.rotozoom(pygame.image.load(os.path.join("sprites", "red.png")).convert_alpha(), 0, misc.zoom)
      misc.screen.blit(imgFireRed, (10*misc.zoom,10*misc.zoom))
      countdown_text = countdownFont.render("3", 1, misc.lightColor)
      countdown_rect = countdown_text.get_rect()
      countdown_rect.center = (misc.screen.get_rect().centerx, misc.screen.get_rect().centery)
      # Restore only the countdown area from track to preserve lights/background
      misc.screen.blit(currentTrack.track, countdown_rect, countdown_rect)
      misc.screen.blit(countdown_text, countdown_rect)
      # Play countdown sound if available (limit length)
      if countdown_sound:
        try:
          # Extend final beep by +1s so it's still audible when race starts
          countdown_channel = countdown_sound.play(maxtime=2500)
        except Exception:
          countdown_channel = None
      pygame.display.flip()
      pygame.time.delay(1000)

      # Show ORANGE light (second signal) with countdown "2"
      imgFireOrange = pygame.transform.rotozoom(pygame.image.load(os.path.join("sprites", "orange.png")).convert_alpha(), 0, misc.zoom)
      misc.screen.blit(imgFireOrange, (90*misc.zoom,10*misc.zoom))
      countdown_text = countdownFont.render("2", 1, misc.lightColor)
      countdown_rect = countdown_text.get_rect()
      countdown_rect.center = (misc.screen.get_rect().centerx, misc.screen.get_rect().centery)
      misc.screen.blit(currentTrack.track, countdown_rect, countdown_rect)
      misc.screen.blit(countdown_text, countdown_rect)
      # Play countdown sound if available (limit length)
      if countdown_sound:
        try:
          countdown_channel = countdown_sound.play(maxtime=1500)
        except Exception:
          countdown_channel = None
      pygame.display.flip()
      pygame.time.delay(1000)

      # Show GREEN light (third signal - GO!) with countdown "1"
      imgFireGreen = pygame.transform.rotozoom(pygame.image.load(os.path.join("sprites", "green.png")).convert_alpha(), 0, misc.zoom)
      misc.screen.blit(imgFireGreen, (170*misc.zoom,10*misc.zoom))
      countdown_text = countdownFont.render("1", 1, misc.lightColor)
      countdown_rect = countdown_text.get_rect()
      countdown_rect.center = (misc.screen.get_rect().centerx, misc.screen.get_rect().centery)
      misc.screen.blit(currentTrack.track, countdown_rect, countdown_rect)
      misc.screen.blit(countdown_text, countdown_rect)
      # Play countdown sound if available (limit length)
      if countdown_sound:
        try:
          countdown_channel = countdown_sound.play(maxtime=1500)
        except Exception:
          countdown_channel = None
      pygame.display.flip()
      pygame.time.delay(990)

      # Clear event queue
      # Let the countdown sound finish naturally (do not force-stop here)
      pygame.event.clear()

      # Display the track
      misc.screen.blit(currentTrack.track, (0, 0))

      pygame.display.flip()  

      sec = datetime.datetime.now().second
      nbFrame = 0

      # Event loop
      while raceFinish == 0:
        raceFinish = 1

        # Get the event keys
        for event in pygame.event.get():

          if event.type == QUIT:
            # Stop music
            misc.stopMusic()
            sys.exit(0)
          elif event.type == KEYDOWN:

              if event.key == K_ESCAPE:
                  misc.stopMusic()
                  return -1

              # Toggle music during race
              if event.key == K_m:
                  if misc.music == 1:
                      misc.music = 0
                      misc.stopMusic()
                  else:
                      misc.music = 1
                      misc.startRaceMusic(currentTrack.name)

              for play in self.listPlayer:
                  play.handle_keydown(event.key)
          elif event.type == KEYUP:
            for play in self.listPlayer:
              play.handle_keyup(event.key)

        # Apply per-player control updates
        for play in self.listPlayer:
          play.update_controls()

        # TODO ? Manage Rect.union (oldRect and newRect of a car) to optimize !!!!
        # Append the old rect to the dirty Rects
        for play in self.listPlayer:
          oldRect = play.car.rect
          l.append(oldRect.__copy__())
          misc.screen.blit(currentTrack.track, play.car.rect, play.car.rect)

        # For each player, update positions and check checkpoints
        for play in self.listPlayer:
          play.car.update()

          play.chrono = play.chrono + 1

          # Get infos on trackFunction
          color=currentTrack.trackF.get_at((int(play.car.x), int(play.car.y)))
          r=color[0]
          #b=color[2]

          # Manage the checkpoints to count the nb of laps
          if currentTrack.reverse == 0 and play.raceFinish == 0:
            if r == play.lastCheckpoint + 16:
              play.lastCheckpoint = r
              #print "Checkpoint OK"
            # We finish a lap
            elif r == 16:
              # OK
              if play.lastCheckpoint == 16 * currentTrack.nbCheckpoint:
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

          elif currentTrack.reverse == 1 and play.raceFinish == 0:
            if r != 0 and r == play.lastCheckpoint - 16:
              play.lastCheckpoint = r
              #print "Checkpoint OK"
            # We finish a lap
            elif r == 16 * currentTrack.nbCheckpoint:
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
              elif play.lastCheckpoint < 16 * currentTrack.nbCheckpoint:
                play.lastCheckpoint = r
                popUp.addElement(play.car, play.name + " L" + str(play.nbLap+1) + " MISSED")
                play.chrono = 0

        # Manage Collisions
        for play in self.listPlayer:
          for play2 in self.listPlayer:
            if play == play2:
              continue
           # Prevent collisions between cars on different bridge levels in desert tracks
            if currentTrack.name.startswith("desert"):
             # Only allow collision if both are on the bridge (80) or both are not
              if (play.lastCheckpoint == 80) != (play2.lastCheckpoint == 80):
                continue
            if currentTrack.name.startswith("city"):
              if (play.lastCheckpoint == 48) != (play2.lastCheckpoint == 48):
                continue
        # Manage Collisions — broad-phase spatial grid reduces candidate pairs.
        # Rebuild the grid each frame (O(n)), then only run the expensive
        # narrow-phase rect tests on pairs that share a grid cell.
        _collision_grid.rebuild(self.listPlayer, get_rect=lambda p: p.car.rect)
        for _pa, _pb in _collision_grid.candidate_pairs():
          # Process both orderings so each car gets its own directional response.
          for play, play2 in ((_pa, _pb), (_pb, _pa)):
            # Prevent collisions between cars on different bridge levels in desert tracks
            if currentTrack.name.startswith("desert"):
              # Only allow collision if both are on the bridge (80) or both are not
              if (play.lastCheckpoint == 80) != (play2.lastCheckpoint == 80):
                continue
            playCollisionRects = []
            play2CollisionRects = []
            listIndex = pygame.Rect(play.car.listCarRect[0]).collidelistall(play2.car.listCarRect)
            if listIndex != []:
              playCollisionRects.append(0)
              for idx in listIndex:
                if idx not in play2CollisionRects:
                  play2CollisionRects.append(idx)
            listIndex = pygame.Rect(play.car.listCarRect[1]).collidelistall(play2.car.listCarRect)
            if listIndex != []:
              playCollisionRects.append(1)
              for idx in listIndex:
                if idx not in play2CollisionRects:
                  play2CollisionRects.append(idx)
            listIndex = pygame.Rect(play.car.listCarRect[2]).collidelistall(play2.car.listCarRect)
            if listIndex != []:
              playCollisionRects.append(2)
              for idx in listIndex:
                if idx not in play2CollisionRects:
                  play2CollisionRects.append(idx)
            listIndex = pygame.Rect(play.car.listCarRect[3]).collidelistall(play2.car.listCarRect)
            if listIndex != []:
              playCollisionRects.append(3)
              for idx in listIndex:
                if idx not in play2CollisionRects:
                  play2CollisionRects.append(idx)

            playCollisionRects.sort()
            play2CollisionRects.sort()
            #if playCollisionRects != []:
              #print playCollisionRects
            if playCollisionRects == [0]:
              play.car.newSpeed = play.car.speed/2 - abs(play2.car.speed/2)
            elif playCollisionRects == [1]:
              play.car.newSpeed = play.car.speed/2 + abs(play2.car.speed/2)
            elif playCollisionRects == [2] or playCollisionRects == [0,1,2] or playCollisionRects == [0,2] or playCollisionRects == [1,2]:
              play.car.speedL = play.car.speedL + abs(play2.car.speed/2)*10
              play.car.newSpeed = 0
            elif playCollisionRects == [3] or playCollisionRects == [0,1,3] or playCollisionRects == [0,3] or playCollisionRects == [1,3]:
              play.car.speedL = play.car.speedL - abs(play2.car.speed/2)*10
              play.car.newSpeed = 0
            elif playCollisionRects != [] :
              #TODO
              #print "Strange Collision !!!"
              #print playCollisionRects
              play.car.newSpeed = 0
        
        for play in self.listPlayer:
          #print play.name
          #print play.car.speedL
          if play.car.newSpeed != 0:
            play.car.speed = play.car.newSpeed
            play.car.newSpeed = 0

        # Display PopUp
        popUp.display()
        l.append(popUp.rect.__copy__())

        for play in self.listPlayer:

          # Change the car sprite
          if play.car.brake == 0:
            play.car.image=play.car.cars[int((256.0*play.car.angle/2.0/math.pi)%256)].copy()
          else:
            play.car.image=play.car.cars2[int((256.0*play.car.angle/2.0/math.pi)%256)].copy()

          # If there's something on the car (the car is in a tunnel), manage mask to hide the car
          # Specific code for desertf in which the car will be shown above overpass at checkpoint 5 (red=80), reverts when reaching checkpoint 6 (red=96)
          if (currentTrack.name.startswith("desert") and play.lastCheckpoint == 80) or (currentTrack.name.startswith("city") and play.lastCheckpoint == 48):
            pass
          else:
            part=pygame.Surface((play.car.sizeRect,play.car.sizeRect), HWSURFACE, 24).convert()
            part.blit(currentTrack.trackF, (0,0), (play.car.x-play.car.sizeRect/2, play.car.y-play.car.sizeRect/2, play.car.sizeRect, play.car.sizeRect))
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
            if currentTrack.trackF.get_at(coord2)[2] != 255 and currentTrack.trackF.get_at(oldCoord2)[2] != 255:
              pygame.draw.line(currentTrack.track, (0,0,0), coord2, oldCoord2)
            if currentTrack.trackF.get_at(coord3)[2] != 255 and currentTrack.trackF.get_at(oldCoord3)[2] != 255:
              pygame.draw.line(currentTrack.track, (0,0,0), coord3, oldCoord3)

            # Also Front tires if it's a braking slide
            if play.car.slide == 2:
              if currentTrack.trackF.get_at(coord0)[2] != 255 and currentTrack.trackF.get_at(oldCoord0)[2] != 255:
                pygame.draw.line(currentTrack.track, (0,0,0), coord0, oldCoord0)
              if currentTrack.trackF.get_at(coord1)[2] != 255 and currentTrack.trackF.get_at(oldCoord1)[2] != 255:
                pygame.draw.line(currentTrack.track, (0,0,0), coord1, oldCoord1)


          # Test if the player has finished
          if play.nbLap == self.maxLapNb and play.raceFinish != 1:
            play.raceFinish = 1
            play.car.blink = 1

          # Test is somebody has not finished
          if play.nbLap != self.maxLapNb:
            raceFinish = 0

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

        currentTrack.track.unlock()

        if i == 1:
          # Compute the FPS
          sec2 = datetime.datetime.now().second
          if sec2 > sec or (sec == 59 and sec2 > 0):
            fps = nbFrame
            nbFrame = 1
            sec = sec2
            text = misc.popUpFont.render(str(fps), 1, misc.lightColor, (0, 0, 0))
            textRect = text.get_rect()
            textRect.x = 0
            textRect.y = 0
            misc.screen.blit(text, textRect)
            l.append(textRect.__copy__())
          else:
            nbFrame = nbFrame + 1

          pygame.display.update(l)
          i=0
          l = []
        else:
          i=i+1

        masterChrono = masterChrono + 1

        # Record datas
        for play in self.listPlayer:
          replayArray.append(int(play.car.x/misc.zoom))
          replayArray.append(int(play.car.y/misc.zoom))
          replayArray.append(int(play.car.angle*1000))

          # val = 100*car.blink + 10*car.brake + 1*car.slide
          val = play.car.blink*100
          if play.car.brake > 0:
            val = val + 10
          val = val + play.car.slide*1
          replayArray.append(val)

          # val = 1000*keyAccel + 100*keyBrake + 10*keyLeft + 1*keyRight
          if play.__class__.__name__ == "HumanPlayer" or play.__class__.__name__ == "RobotPlayer":
            val = play.keyAccelPressed*1000 + play.keyBrakePressed*100 + play.keyLeftPressed*10 + play.keyRightPressed*1
            replayArray.append(val)
          else:
            replayArray.append(0)

        # Make sure game doesn't run at more than 100 frames per second
        clock.tick(100)

      # Display the last PopUp
      popUp.display()
      l.append(popUp.rect.__copy__())
      
      misc.startResultMusic()
      self.computeScores(currentTrack)

      menu1 = menu.SimpleMenu(misc.titleFont, "save Replay?", 20*misc.zoom, misc.itemFont, ["No", "Yes"])
      select1 = menu1.getInput()

      if select1 == 2:
        menu2 = menu.ChooseTextMenu(misc.titleFont, "enter a Replay Name:", 20*misc.zoom, misc.itemFont, 8)
        select2 = menu2.getInput()
        
        waitMenu = menu.SimpleTitleOnlyMenu(misc.titleFont, "recording Replay...")

        if select2 is not None and select2 != "":
          # Build text header then write binary frame data
          header = (
            f"{misc.VERSION} {currentTrack.name} {currentTrack.reverse} "
            f"{masterChrono} {len(self.listPlayer)} "
          )
          for play in self.listPlayer:
            header += f"{play.name} {play.car.color} {play.car.level} "
          header += "\n"

          with open(os.path.join("replays", select2 + ".rep"), "wb") as f:
            f.write(header.encode())
            # Serialize frame array as raw binary (5 signed 16-bit ints per
            # player per frame), then zlib-compress for compact storage.
            f.write(zlib.compress(replayArray.tobytes()))

      

      # Return to menu music
      misc.startMenuMusic()

    if self.gameType == "tournament":
      self.displayFinalScores()

    # If it's a challenge there's only 1 player, and return bestChrono
    if self.gameType == "challenge":
      return self.listPlayer[0].bestChrono

  def computeScores(self, track):

      misc.screen.blit(misc.background, (0, 0))

      overlay = pygame.Surface(misc.screen.get_size())
      overlay.set_alpha(100)
      overlay.fill((0, 0, 0))
      misc.screen.blit(overlay, (0, 0))

      screen_rect = misc.screen.get_rect()
      center_x = screen_rect.centerx

            # Main results board
      board_width = int(760 * misc.zoom)

      player_count = len(self.listPlayer)
      row_height = int(82 * misc.zoom)
      row_gap = int(10 * misc.zoom)

      board_height = int(170 * misc.zoom) + player_count * (row_height + row_gap)
      max_board_height = int(650 * misc.zoom)

      if board_height > max_board_height:
        board_height = max_board_height
        row_height = int(70 * misc.zoom)
        row_gap = int(6 * misc.zoom)
      board_rect = pygame.Rect(0, 0, board_width, board_height)
      board_rect.centerx = center_x
      board_rect.y = int(70 * misc.zoom)

      board_surface = pygame.Surface((board_width, board_height))
      board_surface.fill((28, 32, 48))
      board_surface.set_alpha(235)
      misc.screen.blit(board_surface, board_rect)
      pygame.draw.rect(misc.screen, (220, 220, 230), board_rect, 3)

      # Title
      title_text = misc.titleFont.render("RACE RESULTS", True, misc.lightColor)
      title_rect = title_text.get_rect()
      title_rect.centerx = center_x
      title_rect.y = board_rect.y + int(18 * misc.zoom)
      misc.screen.blit(title_text, title_rect)

      # Header line
      pygame.draw.line(
          misc.screen,
          (180, 180, 190),
          (board_rect.x + int(30 * misc.zoom), title_rect.bottom + int(10 * misc.zoom)),
          (board_rect.right - int(30 * misc.zoom), title_rect.bottom + int(10 * misc.zoom)),
          2
      )

      # Sort players by rank
      sorted_players = sorted(self.listPlayer, key=lambda p: p.rank)

      row_y = title_rect.bottom + int(28 * misc.zoom)

      for idx, play in enumerate(sorted_players):
          # Row background
          row_rect = pygame.Rect(
              board_rect.x + int(25 * misc.zoom),
              row_y,
              board_width - int(50 * misc.zoom),
              row_height
          )

          if play.rank == 1:
              row_fill = (70, 60, 25)   # gold-ish
              border_color = (255, 215, 0)
          elif play.rank == 2:
              row_fill = (55, 55, 65)   # silver-ish
              border_color = (192, 192, 192)
          elif play.rank == 3:
              row_fill = (70, 50, 35)   # bronze-ish
              border_color = (205, 127, 50)
          else:
              row_fill = (45, 48, 62)
              border_color = (120, 120, 140)

          pygame.draw.rect(misc.screen, row_fill, row_rect)
          pygame.draw.rect(misc.screen, border_color, row_rect, 2)

          # Position text
          if play.rank == 1:
              pos_text = "1st"
              pos_color = (255, 215, 0)
          elif play.rank == 2:
              pos_text = "2nd"
              pos_color = (192, 192, 192)
          elif play.rank == 3:
              pos_text = "3rd"
              pos_color = (205, 127, 50)
          else:
              pos_text = str(play.rank) + "th"
              pos_color = misc.lightColor

          pos_surface = misc.itemFont.render(pos_text, True, pos_color)
          pos_rect = pos_surface.get_rect()
          pos_rect.x = row_rect.x + int(18 * misc.zoom)
          pos_rect.centery = row_rect.centery
          misc.screen.blit(pos_surface, pos_rect)

          # Car image
          playCar = pygame.transform.rotozoom(
              pygame.image.load(
                  os.path.join("sprites", "cars", "car" + str(play.car.color) + ".png")
              ).convert_alpha(),
              270,
              1.0 * misc.zoom
          )

          playCarRect = playCar.get_rect()
          playCarRect.x = pos_rect.right + int(25 * misc.zoom)
          playCarRect.centery = row_rect.y + int(row_height / 2)
          misc.screen.blit(playCar, playCarRect)

          # Player name
          text_x = playCarRect.right + int(20 * misc.zoom)

          name_surface = misc.itemFont.render(play.name, True, misc.lightColor)
          name_rect = name_surface.get_rect()
          name_rect.x = text_x
          name_rect.y = row_rect.y + int(5 * misc.zoom)
          misc.screen.blit(name_surface, name_rect)

          # Time / score text
          if self.gameType == "tournament":
              info_text = "Points: " + str(play.point)
          else:
              info_text = "Best Time: " + misc.chrono2Str(play.bestChrono)

          bestChrono = 1
          for play2 in self.listPlayer:
              if play.bestChrono > play2.bestChrono:
                  bestChrono = 0
                  break

          if self.gameType != "tournament" and bestChrono == 1:
              if misc.addHiScore(track, play) == 1:
                  info_text += "   |   HiScore!"

          info_color = misc.lightColor if play.rank == 1 else (210, 210, 210)
          info_surface = misc.smallItemFont.render(info_text, True, info_color)
          info_rect = info_surface.get_rect()
          info_rect.x = text_x
          info_rect.y = row_rect.y + int(42 * misc.zoom)
          misc.screen.blit(info_surface, info_rect)

          row_y += row_height + int(12 * misc.zoom)

      # Footer hint
      hint_surface = misc.smallItemFont.render("Press ENTER to continue", True, misc.lightColor)
      hint_rect = hint_surface.get_rect()
      hint_rect.centerx = misc.screen.get_rect().centerx
      hint_rect.y = min(board_rect.bottom + int(14 * misc.zoom), int(725 * misc.zoom))
      misc.screen.blit(hint_surface, hint_rect)

      pygame.display.flip()

      # Clear old events first
      pygame.event.clear()

      # Wait until all currently held keys are released
      waiting_release = True
      while waiting_release:
        pressed = pygame.key.get_pressed()
        if not any(pressed):
          waiting_release = False
        pygame.time.delay(10)

      # Now wait only for ENTER
      waiting_enter = True
      while waiting_enter:
        for event in pygame.event.get():
          if event.type == QUIT:
            misc.stopMusic()
            sys.exit(0)
          if event.type == KEYDOWN and event.key == K_RETURN:
            waiting_enter = False
            break
        pygame.time.delay(10)
      
  def displayFinalScores(self):

    titleMenu = menu.SimpleTitleOnlyMenu(misc.titleFont, "finalResult")

    y = titleMenu.startY
    for play in self.listPlayer:

      # Get the final rank
      self.rank = 1
      for play2 in self.listPlayer:
        if play.point < play2.point:
          self.rank = self.rank + 1

      playCar = pygame.transform.rotozoom(pygame.image.load(os.path.join("sprites", "cars", "car" + str(play.car.color) + ".png")).convert_alpha(), 270, 1.2*misc.zoom)

      if self.rank == 1:
        text = misc.titleFont.render(str(play.rank) + "' " + play.name + " :  >> " + str(play.point) + " <<", 1, misc.lightColor)
      else:
        text = misc.titleFont.render(str(play.rank) + "' " + play.name + " : " + str(play.point), 1, misc.darkColor)

      # Display the car with statistics
      playCarRect = playCar.get_rect()
      textRect = text.get_rect()
      textRect.centerx = misc.screen.get_rect().centerx + (playCarRect.width + 20*misc.zoom) /2
      textRect.y = y + 80*misc.zoom*play.rank
      playCarRect.x = textRect.x - (playCarRect.width + 20*misc.zoom)
      playCarRect.centery = textRect.centery
      misc.screen.blit(playCar, playCarRect)
      misc.screen.blit(text, textRect)

    pygame.display.flip()

    pygame.event.clear()

    waiting_release = True
    while waiting_release:
      pressed = pygame.key.get_pressed()
      if not any(pressed):
        waiting_release = False
      pygame.time.delay(10)

    waiting_enter = True
    while waiting_enter:
      for event in pygame.event.get():
        if event.type == QUIT:
          misc.stopMusic()
          sys.exit(0)
        if event.type == KEYDOWN and event.key == K_RETURN:
          waiting_enter = False
          break
      pygame.time.delay(10)
