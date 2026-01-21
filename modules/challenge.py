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
from . import game
from . import menu

challenges= [
             [["formula", 0], 630, 5, None],
             [["http", 0], 630, 5, None],
             [["bio", 0], 570, 5, None],
             [["wave", 0], 780, 3, None],
             [["desert", 0], 765, 3, None],
             [["kart", 0], 1122, 1, 1]
            ]

class Challenge:
  '''Class representing a challenge race'''

  def __init__(self, thePlayer):
    '''Constructor'''

    self.thePlayer = thePlayer

    i = 0

    while i < len(challenges):
      chal = challenges[i]

      texts = ["You should do a better chrono than",
               misc.chrono2Str(chal[1]),
               "on track"]
      if chal[0][1] == 0:
        texts.append(chal[0][0])
      else:
        texts.append(chal[0][0] + " REV")

      if chal[2] == 1:
        texts.append("in ONLY " + str(chal[2]) + " lap")
      else:
        texts.append("in " + str(chal[2]) + " laps")

      menuT = menu.MenuText(misc.titleFont, "challenge " + str(i+1), 10*misc.zoom, misc.itemFont, texts)
      misc.wait4Key()

      chalRace = game.Game("challenge", [chal[0]], [thePlayer], chal[2])
      chrono = chalRace.play()

      if chrono == -1:
        return
      if chrono < chal[1]:
        texts = ["Challenge Done: ", misc.chrono2Str(chrono) + " better than " + misc.chrono2Str(chal[1])]
        if chal[3] != None:
          texts.append("Unlocking of a new track !!!")
          misc.setUnlockLevel(chal[3])
        menuT = menu.MenuText(misc.titleFont, "challenge " + str(i+1), 10*misc.zoom, misc.itemFont, texts)
        misc.wait4Key()

        i = i + 1
      else:
        texts = ["Challenge Failed: ", misc.chrono2Str(chrono) + " worst than " + misc.chrono2Str(chal[1])]
        menuT = menu.MenuText(misc.titleFont, "challenge " + str(i+1), 10*misc.zoom, misc.itemFont, texts)
        misc.wait4Key()

    texts = ["Challenges Finished..."]
    menuT = menu.MenuText(misc.titleFont, "challenges", 10*misc.zoom, misc.itemFont, texts)
    misc.wait4Key()
