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

import argparse
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

def _build_arg_parser() -> argparse.ArgumentParser:
  """Return the configured ArgumentParser for pyRacerz."""
  parser = argparse.ArgumentParser(
    prog="pyRacerz.py",
    description="pyRacerz - a top-down 2D racing game.",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=(
      "pyRacerz comes with ABSOLUTELY NO WARRANTY.\n"
      "This is free software; see the COPYING file for details."
    ),
  )
  parser.add_argument(
    "--resolution",
    choices=["640x480", "320x240"],
    default=None,
    metavar="WxH",
    help="set display resolution (default: 1024x768); choices: 640x480, 320x240",
  )
  parser.add_argument(
    "--fullscreen",
    action="store_true",
    help="enable fullscreen display",
  )
  buf_group = parser.add_mutually_exclusive_group()
  buf_group.add_argument(
    "--doublebuf",
    action="store_true",
    help="enable double buffering (default on non-Windows)",
  )
  buf_group.add_argument(
    "--nodoublebuf",
    action="store_true",
    help="disable double buffering (default on Windows)",
  )
  parser.add_argument(
    "--nosound",
    action="store_true",
    help="disable sound and music",
  )
  parser.add_argument(
    "--version",
    action="version",
    version=(
      f"pyRacerz {misc.VERSION}\n"
      "Copyright (C) 2005 Jujucece <jujucece@gmail.com>\n\n"
      "pyRacerz comes with ABSOLUTELY NO WARRANTY.\n"
      "This is free software, and you are welcome to redistribute it\n"
      "under certain conditions; see the COPYING file for details."
    ),
  )
  return parser


def main():

  # --- Parse command-line options via argparse ---
  args = _build_arg_parser().parse_args()

  # Resolution
  if args.resolution == "640x480":
    misc.zoom = 0.625
  elif args.resolution == "320x240":
    misc.zoom = 0.3125

  # Sound
  if args.nosound:
    misc.music = 0

  # Double-buffering: OS default (off on Windows, on elsewhere), overridden by flags
  double = 0 if os.name == "nt" else 1
  if args.doublebuf:
    double = 1
  elif args.nodoublebuf:
    double = 0

  # Build pygame display flags
  displayFlags = HWSURFACE
  if args.fullscreen:
    displayFlags |= FULLSCREEN
  if double:
    displayFlags |= DOUBLEBUF

  try:
    pygame.init()
  except Exception as e:
    print("Cannot initialize pyGame:")
    print(e)
    sys.exit(-1)

  if pygame.display.mode_ok((int(1024*misc.zoom), int(768*misc.zoom)), displayFlags, 24) == 0:
     print("pyRacerz cannot initialize display...")
     sys.exit(-1)
  else:
    misc.screen = pygame.display.set_mode((int(1024*misc.zoom), int(768*misc.zoom)), displayFlags, 24)

  pygame.display.set_caption("pyRacerz v" + misc.VERSION)
  pygame.display.set_icon(pygame.image.load(os.path.join("sprites", "pyRacerzIcon.bmp")))

  if misc.music == 1:
    pygame.mixer.music.load(os.path.join("sounds", "start.ogg"))
    pygame.mixer.music.play()

  #figure out what psyco was
  try:
    import psyco
    psyco.full() 
  except:
    print ("Cannot use psyCo...")
    pass
  
  pygame.mouse.set_visible(0)

  misc.init()

  select1 = 1

  while select1 != -1:
    menu1 = menu.SimpleMenu(misc.titleFont, "pyRacerz v" + misc.VERSION, 20*misc.zoom, misc.itemFont, ["Single Race", "Tournament", "Challenge", "Replays", "Hi Scores", "Credits", "License"])
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
