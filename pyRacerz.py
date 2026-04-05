#!/usr/bin/env python

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

import time
import sys
import os

sys.path.append("modules")
import modules.misc as misc
import modules.player as player
import modules.game as game
import modules.menu as menu
import modules.track as track
import modules.replay as replay
import modules.challenge as challenge

def main():

  if os.name == "nt":
    full = 0
    double = 0
  else:
    full = 0
    double = 1

  displayFlags = HWSURFACE

  # Get commandline options
  if len(sys.argv) != 1:
    for i in range(1, len(sys.argv)):
      if sys.argv[i].upper() == "--RESOLUTION":
        # Get the resolution
        if i != len(sys.argv)-1 and sys.argv[i+1].upper() == "640X480":
          misc.zoom = 0.625
        elif i != len(sys.argv)-1 and sys.argv[i+1].upper() == "320X240":
          misc.zoom = 0.3125
      if sys.argv[i].upper() == "--FULLSCREEN":
        full = 1
      if sys.argv[i].upper() == "--DOUBLEBUF":
        double = 1
      if sys.argv[i].upper() == "--NODOUBLEBUF":
        double = 0
      if sys.argv[i].upper() == "--NOSOUND":
        misc.music = 0
      if sys.argv[i].upper() == "--HELP" or sys.argv[i].upper() == "-H":
        print ("USAGE: pyRacerz.py [--resolution 640x480|320x240] [--fullscreen] [--doublebuf|--nodoublebuf] [--nosound] [--help|-h] [--version]")
        print()
        print("  --resolution   Change resolution (default is 1024x768)")
        print("  --fullscreen   Enable fullscreen display")
        print("  --doublebuf    Enable double buffering display (DEFAULT on other platform than Windows)")
        print("  --nodoublebuf  Disable double buffering display (DEFAULT on Windows)")
        print("  --nosound      Disable Sound")
        print("  --help|-h      Display this help and exit")
        print("  --version      Output version information and exit")
        sys.exit(0)
      if sys.argv[i].upper() == "--VERSION":
        print("pyRacerz version " + misc.VERSION + ", Copyright (C) 2005 Jujucece <jujucece@gmail.com>")
        print()
        print("pyRacerz comes with ABSOLUTELY NO WARRANTY.")
        print("This is free software, and you are welcome to redistribute it")
        print("under certain conditions; see the COPYING file for details.")
        sys.exit(0)
      
  if full == 1 and double == 1:
    displayFlags = displayFlags|DOUBLEBUF|FULLSCREEN
  elif full == 1 and double == 0:
    displayFlags = displayFlags|FULLSCREEN
  elif full == 0 and double == 1:
    displayFlags = displayFlags|DOUBLEBUF
  elif full == 0 and double == 0:
    displayFlags = displayFlags

  try:
    pygame.init()
  except Exception as e:
    print("Cannot initialize pyGame:")
    print(e)
    sys.exit(-1)

  try:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if base_dir:
      os.chdir(base_dir)
  except Exception:
    pass

  if pygame.display.mode_ok((int(1024*misc.zoom), int(768*misc.zoom)), displayFlags, 24) == 0:
     print("pyRacerz cannot initialize display...")
     sys.exit(-1)
  else:
    misc.screen = pygame.display.set_mode((int(1024*misc.zoom), int(768*misc.zoom)), displayFlags, 24)

  pygame.display.set_caption("pyRacerz v" + misc.VERSION)
  pygame.display.set_icon(pygame.image.load(os.path.join("sprites", "pyRacerzIcon.bmp")))

  pygame.mixer.music.load(os.path.join("musics", "menu_music.wav"))
  pygame.mixer.music.set_volume(0.5)
  pygame.mixer.music.play(-1)

  #figure out what psyco was
  try:
    import psyco
    psyco.full() 
  except:
    print ("Cannot use psyCo...")
    pass
  
  # pygame.mouse.set_visible(1)
  pygame.mouse.set_visible(1)

  misc.init()

  select1 = 1

  while select1 != -1:
    menu1 = menu.SimpleMenu(misc.titleFont, "pyRacerz v" + misc.VERSION, 20*misc.zoom, misc.itemFont, ["Single Race", "Tournament", "Challenge", "Replays", "Hi Scores"], misc.main_menu_background)
    select1 = menu1.getInput()

    # Single Race
    if select1 == 1:
      race = game.Game("singleRace")

      menu2 = menu.ChooseTrackMenu(misc.titleFont, "singleRace: chooseTrack", 2*misc.zoom, misc.itemFont)
      select2 = menu2.getInput()
      if select2 != -1:
        race.listTrackName = [[select2[0], select2[1]] ]

        menu3 = menu.ChooseValueMenu(misc.titleFont, "singleRace: chooseNbLaps", 0, misc.itemFont, 1, 10)
        select3 = menu3.getInput()
        if select3 != -1:
          race.maxLapNb = select3

          menu4 = menu.ChooseValueMenu(misc.titleFont, "singleRace: chooseNbHumanPlayers", 0, misc.itemFont, 0, 4)
          select4 = menu4.getInput()
          if select4 != -1:

            isExit = 0
            race.listPlayer = []
            for i in range(1, select4+1):
              menu5 = menu.ChooseHumanPlayerMenu(misc.titleFont, "singleRace: chooseHumanPlayer" + str(i), 5*misc.zoom, misc.itemFont)
              thePlayer = menu5.getInput()
              if thePlayer == -1:
                isExit = 1
                break
              race.listPlayer.append(thePlayer)

            # If there's no exit during enter of player
            if isExit == 0:
              # If there's no Human player, there should exist at least a Bot player
              if select4 == 0:
                minBot = 1
              else:
                minBot = 0
              menu6 = menu.ChooseValueMenu(misc.titleFont, "singleRace: chooseNbRobotPlayers", 0, misc.itemFont, minBot, 4)
              select6 = menu6.getInput()
              if select6 != -1:
                isExit = 0
                for i in range(1, select6+1):
                  menu7 = menu.ChooseRobotPlayerMenu(misc.titleFont, "singleRace: chooseRobotPlayer" + str(i), 5*misc.zoom, misc.itemFont)
                  thePlayer = menu7.getInput()
                  if thePlayer == -1:
                    isExit = 1
                    break
                  race.listPlayer.append(thePlayer)
 
                # If there's no exit during enter of player
                if isExit == 0:
                  race.play()

    # Tournament
    elif select1 == 2:
      tournament = game.Game("tournament")

      tournament.listTrackName = []

      # Get all tracks to put in the tournament
      listAvailableTrackNames = track.getAvailableTrackNames()

      for trackName in listAvailableTrackNames:
        tournament.listTrackName.append([trackName, 0])

      # Also Reverse tracks
      for trackName in listAvailableTrackNames:
        tournament.listTrackName.append([trackName, 1])

      menu2 = menu.ChooseValueMenu(misc.titleFont, "tournament: chooseNbLaps", 0, misc.itemFont,1 ,10)
      select2 = menu2.getInput()
      if select2 != -1:
        tournament.maxLapNb = select2

        menu3 = menu.ChooseValueMenu(misc.titleFont, "tournament: chooseNbHumanPlayers", 0, misc.itemFont, 0, 4)
        select3 = menu3.getInput()
        if select3 != -1:

          isExit = 0
          tournament.listPlayer = []
          for i in range(1, select3+1):
            menu4 = menu.ChooseHumanPlayerMenu(misc.titleFont, "tournament: chooseHumanPlayer" + str(i), 5*misc.zoom, misc.itemFont)
            thePlayer = menu4.getInput()
            if thePlayer == -1:
              isExit = 1
              break
            tournament.listPlayer.append(thePlayer)

          # If there's no exit during enter of player
          if isExit == 0:
            # If there's no Human player, there should exist at least a Bot player
            if select3 == 0:
              minBot = 1
            else:
              minBot = 0
            menu6 = menu.ChooseValueMenu(misc.titleFont, "tournament: chooseNbRobotPlayers", 0, misc.itemFont, minBot, 4)
            select6 = menu6.getInput()
            if select6 != -1:
              isExit = 0
              for i in range(1, select6+1):
                menu7 = menu.ChooseRobotPlayerMenu(misc.titleFont, "tournament: chooseRobotPlayer" + str(i), 5*misc.zoom, misc.itemFont)
                thePlayer = menu7.getInput()
                if thePlayer == -1:
                  isExit = 1
                  break
                tournament.listPlayer.append(thePlayer)

           
          # If there's no exit during enter of player
          if isExit == 0:
            tournament.play()

    # Evolution
    elif select1 == 3:
      tournament = game.Game("challenge")

      menu2 = menu.ChooseHumanPlayerMenu(misc.titleFont, "challenge: chooseHumanPlayer", 5*misc.zoom, misc.itemFont)
      thePlayer = menu2.getInput()
      if thePlayer != -1:
        challenge.Challenge(thePlayer)

    elif select1 == 4:
      replays = []

      listFiles = os.listdir("replays")
      for fileReplay in listFiles:
        if fileReplay.endswith(".rep"):
          replays.append(fileReplay.replace(".rep", ""))

      menu7 = menu.SimpleMenu(misc.titleFont, "replay: chooseFile", 1*misc.zoom, misc.smallItemFont, replays)
      select7 = menu7.getInput()

      if select7 != -1 and len(replays) != 0:
        rep = replay.Replay(os.path.join("replays", replays[select7-1] + ".rep"))
        rep.play()

    elif select1 == 5:
      hiscoresMenu = menu.MenuHiscores(misc.titleFont, "hiscores", 10*misc.zoom, misc.smallItemFont)
      hiscoresMenu.getInput()
    elif select1 == 6:
      creditsMenu = menu.MenuCredits(misc.titleFont, "credits", 10*misc.zoom, misc.itemFont)
      misc.wait4Key()
    elif select1 == 7:
      licenseMenu = menu.MenuLicense(misc.titleFont, "license", 10*misc.zoom, misc.smallItemFont)
      misc.wait4Key()

#import profile
#profile.run('main()')
if __name__ == '__main__': main()
