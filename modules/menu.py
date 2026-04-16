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

from hashlib import sha1
import pygame
from pygame.locals import *

import sys
import string
import os
import random
import configparser
#import sha

from . import game
from . import player
from . import track
from . import misc


def _screen_rect():
  return misc.screen.get_rect()


def _clear_row(y, height):
  rect = pygame.Rect(0, y, _screen_rect().width, height)
  misc.screen.blit(misc.background, rect, rect)


def _blit_center(surf, y):
  rect = surf.get_rect()
  rect.centerx = _screen_rect().centerx
  rect.y = y
  misc.screen.blit(surf, rect)
  return rect


def _menu_loop(refresh_cb, handle_keydown):
  """Shared event loop for menu screens.

  refresh_cb: callable that redraws the menu state.
  handle_keydown: callable taking a pygame key code, returning either:
    - "refresh" to trigger a redraw and continue the loop
    - any other non-None value to return that value and exit the loop
  """

  refresh_cb()

  while 1:
    for event in pygame.event.get():
      if event.type == QUIT:
        sys.exit(0)
      elif event.type == KEYDOWN:
        result = handle_keydown(event.key)
        if result == "refresh":
          refresh_cb()
        elif result is not None:
          return result
    pygame.time.delay(10)

class Menu:
  '''Base class for any pyRacerz Menu'''

  def __init__(self, titleFont, title):

    self.titleFont = titleFont
    self.title = title


class SimpleMenu(Menu):
  '''Menu with a simple selection between items'''

  def __init__(self, titleFont, title, gap, itemFont, listItem):

    Menu.__init__(self, titleFont, title)

    self.gap = gap
    self.itemFont = itemFont
    self.listItem = listItem
    
    # Display the Title    
    titleMenu = SimpleTitleOnlyMenu(self.titleFont, self.title)

    self.startY = titleMenu.startY

    # The first item is selected
    self.select = 1

  def getInput(self):
  
    def handle_key(key):
      if key == K_ESCAPE:
        return -1
      if key == K_UP:
        if self.select != 1:
          self.select = self.select - 1
        else:
          self.select = len(self.listItem)
        return "refresh"
      if key == K_DOWN:
        if self.select != len(self.listItem):
          self.select = self.select + 1
        else:
          self.select = 1
        return "refresh"
      if key == K_RETURN:
        return self.select
      return None

    return _menu_loop(self.refresh, handle_key)

  def refresh(self):

    y = self.startY

    i = 1

    # Print the menu items
    for item in self.listItem:
      if i == self.select:
        text = self.itemFont.render(item, 1, misc.lightColor)
      else:
        text = self.itemFont.render(item, 1, misc.darkColor)
      textRect = text.get_rect()
      textRect.centerx = _screen_rect().centerx
      textRect.y = y
      _clear_row(textRect.y, textRect.height)
      misc.screen.blit(text, textRect)
      y = y + textRect.height + self.gap
      i = i + 1

    pygame.display.flip()


class SimpleTitleOnlyMenu(Menu):
  '''Menu only with a title'''

  def __init__(self, titleFont, title):

    Menu.__init__(self, titleFont, title)

    # Put the background
    misc.screen.blit(misc.background, (0, 0))

    y = 10

    # Print the title
    textTitle = self.titleFont.render(self.title, 1, misc.lightColor)
    textRectTitle = textTitle.get_rect()
    textRectTitle.centerx = _screen_rect().centerx
    textRectTitle.y = y
    y = y + textRectTitle.height/2

    # Print the ---
    #text = self.titleFont.render("---------------", 1, misc.lightColor)
    text = self.titleFont.render("...............", 1, misc.lightColor)
    textRect = text.get_rect()
    textRect.centerx = _screen_rect().centerx
    textRect.y = y
    _clear_row(textRectTitle.y, textRectTitle.height)
    _clear_row(textRect.y, textRect.height)
    misc.screen.blit(textTitle, textRectTitle)
    misc.screen.blit(text, textRect)
    y = y + textRect.height

    self.startY = y

    pygame.display.flip()


class ChooseTrackMenu(Menu):
  '''Menu to choose between available tracks'''

  def __init__(self, titleFont, title, gap, itemFont):

    Menu.__init__(self, titleFont, title)

    self.gap = gap
    self.itemFont = itemFont

    # Get available tracks
    self.listAvailableTrackNames = track.getAvailableTrackNames()

    self.listIconTracks = []

    for trackName in self.listAvailableTrackNames:
      self.listIconTracks.append(pygame.transform.scale(track.getImageFromTrackName(trackName), (int(1024*0.1*misc.zoom), int(768*0.1*misc.zoom))))
    
    # Display the Title    
    titleMenu = SimpleTitleOnlyMenu(self.titleFont, self.title)

    self.startY = titleMenu.startY

    # The first item is selected
    self.select = 1

    self.reverse = 0

  def getInput(self):
  
    def handle_key(key):
      if key == K_ESCAPE:
        return -1
      if key == K_UP:
        if self.select != 1:
          self.select = self.select - 1
        else:
          self.select = len(self.listIconTracks)
        return "refresh"
      if key == K_DOWN:
        if self.select != len(self.listIconTracks):
          self.select = self.select + 1
        else:
          self.select = 1
        return "refresh"
      if key == K_LEFT or key == K_RIGHT:
        self.reverse = 1 - self.reverse
        return "refresh"
      if key == K_RETURN:
        return [self.listAvailableTrackNames[self.select-1], self.reverse]
      return None

    return _menu_loop(self.refresh, handle_key)

  def refresh(self):

    y = self.startY

    i = 1

    for iconTrack in self.listIconTracks:
      if i == self.select:
        if self.reverse == 0:
          text = self.itemFont.render("< " + self.listAvailableTrackNames[i-1] + " >", 1, misc.lightColor)
        else:
          text = self.itemFont.render("< " + self.listAvailableTrackNames[i-1] + " REV >", 1, misc.lightColor)
      else:
        text = self.itemFont.render(self.listAvailableTrackNames[i-1], 1, misc.darkColor)
      textRect = text.get_rect()
      textRect.centerx = _screen_rect().centerx
      textRect.y = y
      _clear_row(textRect.y, textRect.height + iconTrack.get_rect().height + 10)
      misc.screen.blit(text, textRect)
      y = y + textRect.height + self.gap
      if i == self.select:
        iconRect = iconTrack.get_rect()
        iconRect.centerx = _screen_rect().centerx
        iconRect.y = y
        y = y + self.gap + 76*misc.zoom
        misc.screen.blit(iconTrack, iconRect)
      i = i + 1

    pygame.display.flip()


class ChooseValueMenu(Menu):
  '''Menu to choose a value between a Min and a Max'''

  def __init__(self, titleFont, title, gap, itemFont, vMin, vMax):

    Menu.__init__(self, titleFont, title)

    self.gap = gap
    self.itemFont = itemFont
    self.vMin = vMin
    self.vMax = vMax
    
    # Display the Title    
    titleMenu = SimpleTitleOnlyMenu(self.titleFont, self.title)

    self.startY = titleMenu.startY

    # The 1 is selected
    self.select = self.vMin

  def getInput(self):
  
    def handle_key(key):
      if key == K_ESCAPE:
        return -1
      if key == K_UP:
        if self.select != self.vMin:
          self.select = self.select - 1
        else:
          self.select = self.vMax
        return "refresh"
      if key == K_DOWN:
        if self.select != self.vMax:
          self.select = self.select + 1
        else:
          self.select = self.vMin
        return "refresh"
      if key == K_RETURN:
        return self.select
      return None

    return _menu_loop(self.refresh, handle_key)

  def refresh(self):

    y = self.startY

    i = 1

    # Print the Values
    for i in range(self.vMin, self.vMax+1):
      if i == self.select:
        text = self.itemFont.render(str(i), 1, misc.lightColor)
      else:
        text = self.itemFont.render(str(i), 1, misc.darkColor)
      textRect = text.get_rect()
      textRect.centerx = _screen_rect().centerx
      textRect.y = y
      _clear_row(textRect.y, textRect.height)
      misc.screen.blit(text, textRect)
      y = y + textRect.height + self.gap
      i = i + 1

    pygame.display.flip()


class ChooseTextMenu(Menu):
  '''Menu to choose a Test'''

  def __init__(self, titleFont, title, gap, itemFont, maxLenght):

    Menu.__init__(self, titleFont, title)

    self.gap = gap
    self.itemFont = itemFont
    self.maxLenght = maxLenght
    
    # Display the Title    
    titleMenu = SimpleTitleOnlyMenu(self.titleFont, self.title)

    self.startY = titleMenu.startY

    # Shared text-input helper handles insert, backspace, and cursor display
    self._input = misc.TextInput(self.maxLenght)

  def getInput(self):
  
    def handle_key(key):
      if key == K_ESCAPE:
        return None
      if key == K_RETURN:
        return self._input.text
      if self._input.feed_key(key):
        return "refresh"
      return None

    return _menu_loop(self.refresh, handle_key)

  def refresh(self):

    y = self.startY

    # Print the Text (TextInput.render_text appends '_' cursor when not full)
    text = self.itemFont.render(self._input.render_text(), 1, misc.lightColor)
    textRect = text.get_rect()
    textRect.centerx = _screen_rect().centerx
    textRect.y = y
    _clear_row(textRect.y, textRect.height)
    misc.screen.blit(text, textRect)

    pygame.display.flip()


class ChooseHumanPlayerMenu(Menu):
  '''Menu to choose a Human Player'''

  def __init__(self, titleFont, title, gap, itemFont):

    Menu.__init__(self, titleFont, title)

    self.gap = gap
    self.itemFont = itemFont

    # Find cars with browsing and finding the 2 files
    self.listAvailableCarNames = []

    listFiles = os.listdir(os.path.join("sprites", "cars"))
    for fileCar in listFiles:
      if fileCar.endswith("B.png"):
        carName = fileCar.replace("B.png", "")
        carC = 1
        for fileCar2 in listFiles:
          if fileCar2 == carName + ".png":
             carC = carC + 1
             break
        if carC == 2:
          self.listAvailableCarNames.append(carName)

    self.listCars = []

    for carName in self.listAvailableCarNames:
      self.listCars.append(pygame.transform.rotozoom(pygame.image.load(os.path.join("sprites", "cars", carName + ".png")).convert_alpha(), 270, 1.2*misc.zoom))
    
    # Display the Title    
    titleMenu = SimpleTitleOnlyMenu(self.titleFont, self.title)

    self.startY = titleMenu.startY

    # The first item is selected
    self.select = 1

    # Car color and Pseudo are choosed randomly
    self.carColor = random.randint(1, len(self.listCars))

    listPseudos = ["ZUT", "ABC", "TOC", "TIC", "TAC", "PIL", "AJT", "KK", "OQP", "PQ", "SSH", "FTP", "PNG", "BSD", "BB", "PAF", "PIF", "HAL", "FSF", "OSS", "GNU", "TUX", "ZOB"]
    self.pseudo = listPseudos[random.randint(0, len(listPseudos)-1)]
    # Shared text-input helper: max 3 chars, pre-seeded with random pseudo
    self._pseudo_input = misc.TextInput(3, self.pseudo)

    self.level = 1

    self.keyAccel = K_UP
    self.keyBrake = K_DOWN
    self.keyLeft = K_LEFT
    self.keyRight = K_RIGHT

  def getInput(self):

    awaiting_key = [None]

    def handle_key(key):
      if awaiting_key[0] != None:
        if awaiting_key[0] == "accel":
          self.keyAccel = key
        elif awaiting_key[0] == "brake":
          self.keyBrake = key
        elif awaiting_key[0] == "left":
          self.keyLeft = key
        elif awaiting_key[0] == "right":
          self.keyRight = key
        awaiting_key[0] = None
        return "refresh"

      if key == K_ESCAPE:
        return -1
      if key == K_UP:
        if self.select != 1:
          self.select = self.select - 1
        else:
          self.select = 8
        return "refresh"
      if key == K_DOWN:
        if self.select != 8:
          self.select = self.select + 1
        else:
          self.select = 1
        return "refresh"
      if key == K_LEFT:
        if self.select == 1:
          if self.carColor != 1:
            self.carColor = self.carColor - 1
          else:
            self.carColor = len(self.listCars)
        if self.select == 3:
          if self.level != 1:
            self.level = self.level - 1
          else:
            self.level = 3
        return "refresh"
      if key == K_RIGHT:
        if self.select == 1:
          if self.carColor != len(self.listCars):
            self.carColor = self.carColor + 1
          else:
            self.carColor = 1
        if self.select == 3:
          if self.level != 3:
            self.level = self.level + 1
          else:
            self.level = 1
        return "refresh"
      if key == K_RETURN:
        if self.select == 4:
          self.keyAccel = None
          awaiting_key[0] = "accel"
          return "refresh"
        if self.select == 5:
          self.keyBrake = None
          awaiting_key[0] = "brake"
          return "refresh"
        if self.select == 6:
          self.keyLeft = None
          awaiting_key[0] = "left"
          return "refresh"
        if self.select == 7:
          self.keyRight = None
          awaiting_key[0] = "right"
          return "refresh"
        if self.select == 8:
          return player.HumanPlayer(self.pseudo, int(self.listAvailableCarNames[self.carColor-1].replace("car", "")), self.level, self.keyAccel, self.keyBrake, self.keyLeft, self.keyRight)
      if self.select == 2 and self._pseudo_input.feed_key(key):
        self.pseudo = self._pseudo_input.text
        return "refresh"
      return None

    return _menu_loop(self.refresh, handle_key)


  def refresh(self):

    y = self.startY

    i = 1


    # 1. is Car selection
    if i == self.select:
      text = self.itemFont.render("<     >", 1, misc.lightColor)
    else:
      text = self.itemFont.render("<     >", 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = _screen_rect().centerx
    textRect.y = y
    carRect = self.listCars[self.carColor - 1].get_rect()
    carRect.centerx = _screen_rect().centerx
    carRect.y = y + (textRect.height - carRect.height)/2
    _clear_row(textRect.y, max(textRect.height, carRect.height))
    misc.screen.blit(text, textRect)
    misc.screen.blit(self.listCars[self.carColor - 1], carRect)
    y = y + textRect.height + self.gap
    i = i + 1

    
    # 2. is Pseudo selection (TextInput shows '_' cursor when field not full)
    if i == self.select:
      text = self.itemFont.render(self._pseudo_input.render_text(), 1, misc.lightColor)
    else:
      text = self.itemFont.render(self._pseudo_input.text, 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = _screen_rect().centerx
    textRect.y = y
    _clear_row(textRect.y, textRect.height)
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap
    i = i + 1

    # 3. is Level selection
    if i == self.select:
      text = self.itemFont.render("< Level " + str(self.level) + " >", 1, misc.lightColor)
    else:
      text = self.itemFont.render("< Level " + str(self.level) + " >", 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = _screen_rect().centerx
    textRect.y = y
    _clear_row(textRect.y, textRect.height)
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap
    i = i + 1

    # 4. is Key Accel selection
    if i == self.select:
      if self.keyAccel == None:
        text = self.itemFont.render("AccelKey: _", 1, misc.lightColor)
      else:
        text = self.itemFont.render("AccelKey: " + pygame.key.name(self.keyAccel), 1, misc.lightColor)
    else:
      text = self.itemFont.render("AccelKey: " + pygame.key.name(self.keyAccel), 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = _screen_rect().centerx
    textRect.y = y
    _clear_row(textRect.y, textRect.height)
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap
    i = i + 1

    # 5. is Key Brake selection
    if i == self.select:
      if self.keyBrake == None:
        text = self.itemFont.render("BrakeKey: _", 1, misc.lightColor)
      else:
        text = self.itemFont.render("BrakeKey: " + pygame.key.name(self.keyBrake), 1, misc.lightColor)
    else:
      text = self.itemFont.render("BrakeKey: " + pygame.key.name(self.keyBrake), 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = _screen_rect().centerx
    textRect.y = y
    _clear_row(textRect.y, textRect.height)
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap
    i = i + 1

    # 6. is Key Left selection
    if i == self.select:
      if self.keyLeft == None:
        text = self.itemFont.render("LeftKey: _", 1, misc.lightColor)
      else:
        text = self.itemFont.render("LeftKey: " + pygame.key.name(self.keyLeft), 1, misc.lightColor)
    else:
      text = self.itemFont.render("LeftKey: " + pygame.key.name(self.keyLeft), 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = _screen_rect().centerx
    textRect.y = y
    _clear_row(textRect.y, textRect.height)
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap
    i = i + 1

    # 7. is Key Right selection
    if i == self.select:
      if self.keyRight == None:
        text = self.itemFont.render("RightKey: _", 1, misc.lightColor)
      else:
        text = self.itemFont.render("RightKey: " + pygame.key.name(self.keyRight), 1, misc.lightColor)
    else:
      text = self.itemFont.render("RightKey: " + pygame.key.name(self.keyRight), 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = _screen_rect().centerx
    textRect.y = y
    _clear_row(textRect.y, textRect.height)
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap
    i = i + 1

    # 8. is Go
    if i == self.select:
      text = self.itemFont.render("GO", 1, misc.lightColor)
    else:
      text = self.itemFont.render("GO", 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = _screen_rect().centerx
    textRect.y = y
    _clear_row(textRect.y, textRect.height)
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap
    i = i + 1

    pygame.display.flip()


class ChooseRobotPlayerMenu(Menu):
  '''Menu to choose a Robot Player'''

  def __init__(self, titleFont, title, gap, itemFont):

    Menu.__init__(self, titleFont, title)

    self.gap = gap
    self.itemFont = itemFont

    # Find cars with browsing and finding the 2 files
    self.listAvailableCarNames = []

    listFiles = os.listdir(os.path.join("sprites", "cars"))
    for fileCar in listFiles:
      if fileCar.endswith("B.png"):
        carName = fileCar.replace("B.png", "")
        carC = 1
        for fileCar2 in listFiles:
          if fileCar2 == carName + ".png":
             carC = carC + 1
             break
        if carC == 2:
          self.listAvailableCarNames.append(carName)

    self.listCars = []

    for carName in self.listAvailableCarNames:
      self.listCars.append(pygame.transform.rotozoom(pygame.image.load(os.path.join("sprites", "cars", carName + ".png")).convert_alpha(), 270, 1.2*misc.zoom))
    
    # Display the Title    
    titleMenu = SimpleTitleOnlyMenu(self.titleFont, self.title)

    self.startY = titleMenu.startY

    # The first item is selected
    self.select = 1

    # Car color and Pseudo are choosed randomly
    self.carColor = random.randint(1, len(self.listCars))

    self.level = 1

  def getInput(self):
  
    def handle_key(key):
      if key == K_ESCAPE:
        return -1
      if key == K_UP:
        if self.select != 1:
          self.select = self.select - 1
        else:
          self.select = 3
        return "refresh"
      if key == K_DOWN:
        if self.select != 3:
          self.select = self.select + 1
        else:
          self.select = 1
        return "refresh"
      if key == K_LEFT:
        if self.select == 1:
          if self.carColor != 1:
            self.carColor = self.carColor - 1
          else:
            self.carColor = len(self.listCars)
        if self.select == 2:
          if self.level != 1:
            self.level = self.level - 1
          else:
            self.level = 3
        return "refresh"
      if key == K_RIGHT:
        if self.select == 1:
          if self.carColor != len(self.listCars):
            self.carColor = self.carColor + 1
          else:
            self.carColor = 1
        if self.select == 2:
          if self.level != 3:
            self.level = self.level + 1
          else:
            self.level = 1
        return "refresh"
      if key == K_RETURN and self.select == 3:
        return player.RobotPlayer(int(self.listAvailableCarNames[self.carColor-1].replace("car", "")), self.level)
      return None

    return _menu_loop(self.refresh, handle_key)


  def refresh(self):

    y = self.startY

    i = 1


    # 1. is Car selection
    if i == self.select:
      text = self.itemFont.render("<     >", 1, misc.lightColor)
    else:
      text = self.itemFont.render("<     >", 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = _screen_rect().centerx
    textRect.y = y
    carRect = self.listCars[self.carColor - 1].get_rect()
    carRect.centerx = _screen_rect().centerx
    carRect.y = y + (textRect.height - carRect.height)/2
    _clear_row(textRect.y, max(textRect.height, carRect.height))
    misc.screen.blit(text, textRect)
    misc.screen.blit(self.listCars[self.carColor - 1], carRect)
    y = y + textRect.height + self.gap
    i = i + 1

    # 2. is Level selection
    if i == self.select:
      text = self.itemFont.render("< Level " + str(self.level) + " >", 1, misc.lightColor)
    else:
      text = self.itemFont.render("< Level " + str(self.level) + " >", 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = _screen_rect().centerx
    textRect.y = y
    _clear_row(textRect.y, textRect.height)
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap
    i = i + 1

    # 3. is Go
    if i == self.select:
      text = self.itemFont.render("GO", 1, misc.lightColor)
    else:
      text = self.itemFont.render("GO", 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = _screen_rect().centerx
    textRect.y = y
    _clear_row(textRect.y, textRect.height)
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap
    i = i + 1

    pygame.display.flip()


# ===========================================================================
# Network multiplayer menus
# ===========================================================================

def _net_menu_loop(refresh_cb, handle_keydown, poll_network):
  """Like _menu_loop but also calls poll_network() each iteration.

  poll_network() may return:
    "refresh"  – trigger a redraw and keep looping
    non-None   – exit the loop and return that value
    None       – nothing to do this tick
  """
  refresh_cb()
  while True:
    for event in pygame.event.get():
      if event.type == QUIT:
        sys.exit(0)
      elif event.type == KEYDOWN:
        result = handle_keydown(event.key)
        if result == "refresh":
          refresh_cb()
        elif result is not None:
          return result
    net_result = poll_network()
    if net_result == "refresh":
      refresh_cb()
    elif net_result is not None:
      return net_result
    pygame.time.delay(10)


class NetworkModeMenu(Menu):
  """Two-button menu: Host or Join."""

  def __init__(self, titleFont, itemFont):
    Menu.__init__(self, titleFont, "Network Multiplayer")
    self._itemFont = itemFont
    titleMenu    = SimpleTitleOnlyMenu(self.titleFont, self.title)
    self.startY  = titleMenu.startY
    self.select  = 1

  def getInput(self):
    def handle_key(key):
      if key == K_ESCAPE:
        return "back"
      if key in (K_UP, K_DOWN):
        self.select = 2 if self.select == 1 else 1
        return "refresh"
      if key == K_RETURN:
        return "host" if self.select == 1 else "join"
      return None

    return _menu_loop(self.refresh, handle_key)

  def refresh(self):
    y = self.startY
    for idx, label in enumerate(["Host a Lobby", "Join a Lobby"], start=1):
      color = misc.lightColor if idx == self.select else misc.darkColor
      surf  = self._itemFont.render(label, 1, color)
      r     = surf.get_rect()
      r.centerx = _screen_rect().centerx
      r.y = y
      _clear_row(r.y, r.height)
      misc.screen.blit(surf, r)
      y += r.height + int(20 * misc.zoom)
    pygame.display.flip()


class NetworkIPMenu(Menu):
  """Enter the host IP address (digits + dots only)."""

  def __init__(self, titleFont, itemFont):
    Menu.__init__(self, titleFont, "Enter Host IP")
    self._itemFont = itemFont
    titleMenu   = SimpleTitleOnlyMenu(self.titleFont, self.title)
    self.startY = titleMenu.startY
    self._input = misc.IPTextInput(15)

  def getInput(self):
    def handle_key(key):
      if key == K_ESCAPE:
        return None          # cancelled
      if key == K_RETURN:
        ip = self._input.text.strip(".")
        return ip if ip else None
      if self._input.feed_key(key):
        return "refresh"
      return None

    return _menu_loop(self.refresh, handle_key)

  def refresh(self):
    y = self.startY
    surf = self._itemFont.render(self._input.render_text(), 1, misc.lightColor)
    r    = surf.get_rect()
    r.centerx = _screen_rect().centerx
    r.y = y
    _clear_row(r.y, r.height)
    misc.screen.blit(surf, r)
    y += r.height + int(10 * misc.zoom)
    hint = misc.popUpFont.render("[ENTER] Connect   [ESC] Back", 1, misc.darkColor)
    hr   = hint.get_rect()
    hr.centerx = _screen_rect().centerx
    hr.y = y
    misc.screen.blit(hint, hr)
    pygame.display.flip()


class NetworkLobbyMenu(Menu):
  """Lobby screen shown to both host and clients.

  Parameters
  ----------
  net_obj    : NetworkServer (is_host=True) or NetworkClient (is_host=False)
  is_host    : bool
  local_name : str   – this player's display name
  track_name : str   – (host only) track chosen for next race
  track_rev  : int   – (host only) 0 = normal, 1 = reverse

  Return value (dict)
  -------------------
  {"action": "start",  ...race info...}   – start race
  {"action": "close"}                     – host closed the lobby
  {"action": "leave"}                     – client left
  """

  _MAX_CHAT   = 10    # lines kept in chat log
  _ROW_H      = int(28 * 1)   # approx; scaled at refresh time

  def __init__(self, net_obj, is_host, local_name,
               track_name="city", track_rev=0,
               host_color=1, host_level=1, laps=3):
    Menu.__init__(self, misc.titleFont, "Lobby")
    self._net        = net_obj
    self._is_host    = is_host
    self._local_name = local_name
    self._track_name = track_name
    self._track_rev  = track_rev
    self._host_color = host_color
    self._host_level = host_level
    self._laps       = laps

    self._players   = [local_name]   # roster; updated by server broadcasts
    self._chat_log  = []
    self._chat_in   = misc.TextInput(48, allow_space=True)
    self._is_typing = False

    # Resolve local LAN IP once so refresh() can display it
    try:
      import socket as _socket
      _s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
      _s.connect(("8.8.8.8", 80))
      self._local_ip = _s.getsockname()[0]
      _s.close()
    except Exception:
      self._local_ip = "unknown"

    SimpleTitleOnlyMenu(misc.titleFont, "Network Lobby")

  # ------------------------------------------------------------------
  def getInput(self):
    return _net_menu_loop(self.refresh, self._handle_key, self._poll_net)

  # ------------------------------------------------------------------
  def _handle_key(self, key):
    if self._is_typing:
      if key == K_RETURN:
        text = self._chat_in.text.strip()
        if text:
          msg = {"type": "chat", "sender": self._local_name, "text": text}
          if self._is_host:
            self._net.broadcast(msg)
            self._chat_log.append(self._local_name + ": " + text)
          else:
            self._net.send(msg)
        self._chat_in   = misc.TextInput(48, allow_space=True)
        self._is_typing = False
        return "refresh"
      if key == K_ESCAPE:
        self._chat_in   = misc.TextInput(48, allow_space=True)
        self._is_typing = False
        return "refresh"
      if self._chat_in.feed_key(key):
        return "refresh"
      return None

    # not typing
    if key == K_t:
      self._is_typing = True
      return "refresh"
    if key == K_ESCAPE:
      if self._is_host:
        self._net.broadcast({"type": "finish"})
        self._net.stop()
        return {"action": "close"}
      else:
        self._net.send({
          "type": "bye",
          "name": self._local_name,
          "pid":  getattr(self._net, "player_id", -1),
        })
        self._net.disconnect()
        return {"action": "leave"}
    if key == K_s and self._is_host:
      roster = self._net.get_player_list()
      # Start race: broadcast start message then return
      self._net.broadcast({
        "type":       "start",
        "track":      self._track_name,
        "reverse":    self._track_rev,
        "laps":       self._laps,
        "host_name":  self._local_name,
        "host_color": self._host_color,
        "host_level": self._host_level,
        "roster":     roster,
      })
      return {"action": "start", "roster": roster}
    return None

  # ------------------------------------------------------------------
  def _poll_net(self):
    """Process incoming network messages; return "refresh" or a result dict."""
    changed = False
    result  = None

    for msg in self._net.recv_all():
      mtype = msg.get("type")

      if mtype == "hello" and self._is_host:
        name   = msg.get("name", "unknown")
        color  = msg.get("color", 1)
        level  = msg.get("level", 1)
        cidx   = msg.get("_client_idx", 0)
        pid = self._net.register_player(cidx, name, color, level)
        self._net.send_to(cidx, {"type": "assigned", "pid": pid})
        if name not in self._players:
          self._players.append(name)
        self._chat_log.append("*** " + name + " joined ***")
        self._net.broadcast({
          "type":   "players",
          "list":   self._players,
          "roster": self._net.get_player_list(),
        })
        changed = True

      elif mtype == "assigned" and not self._is_host:
        pid = msg.get("pid", -1)
        self._net.player_id = pid
        self._chat_log.append("*** assigned racer id P" + str(pid) + " ***")
        changed = True

      elif mtype == "players" and not self._is_host:
        self._players = msg.get("list", self._players)
        changed = True

      elif mtype == "chat":
        entry = msg.get("sender", "?") + ": " + msg.get("text", "")
        self._chat_log = self._chat_log[-self._MAX_CHAT:]
        self._chat_log.append(entry)
        if self._is_host:
          # Re-broadcast so all clients see it
          self._net.broadcast(msg)
        changed = True

      elif mtype == "bye" and self._is_host:
        cidx = msg.get("_client_idx", -1)
        reg  = self._net.get_player(cidx) if cidx >= 0 else None
        name = msg.get("name", reg["name"] if reg else "?")
        self._players = [p for p in self._players if p != name]
        self._chat_log.append("*** " + name + " left ***")
        if cidx >= 0:
          self._net.remove_player(cidx)
        self._net.broadcast({
          "type":   "players",
          "list":   self._players,
          "roster": self._net.get_player_list(),
        })
        changed = True

      elif mtype == "start" and not self._is_host:
        result = {
          "action":     "start",
          "track":      msg.get("track", "city"),
          "reverse":    msg.get("reverse", 0),
          "laps":       msg.get("laps", 3),
          "host_name":  msg.get("host_name", "HOST"),
          "host_color": msg.get("host_color", 1),
          "host_level": msg.get("host_level", 1),
          "roster":     msg.get("roster", []),
        }

      elif mtype == "finish" and not self._is_host:
        # Host closed the lobby — leave gracefully
        self._net.disconnect()
        result = {"action": "leave"}

    if result:
      return result
    return "refresh" if changed else None

  # ------------------------------------------------------------------
  def refresh(self):
    sw = _screen_rect().width

    # Background
    misc.screen.blit(misc.background, (0, 0))

    # Title + separator already drawn by SimpleTitleOnlyMenu in __init__;
    # re-draw them here so refresh works after the initial display.
    y = 10
    title_surf = misc.titleFont.render("Network Lobby", 1, misc.lightColor)
    title_r    = title_surf.get_rect()
    title_r.centerx = sw // 2
    title_r.y = y
    misc.screen.blit(title_surf, title_r)
    y += title_r.height

    sep_surf = misc.titleFont.render("...............", 1, misc.lightColor)
    sep_r    = sep_surf.get_rect()
    sep_r.centerx = sw // 2
    sep_r.y = y
    misc.screen.blit(sep_surf, sep_r)
    y += sep_r.height + int(6 * misc.zoom)

    # ── Players ──────────────────────────────────────────────────────
    hdr = misc.itemFont.render("Players:", 1, misc.lightColor)
    misc.screen.blit(hdr, (int(30 * misc.zoom), y))
    y += hdr.get_height() + int(4 * misc.zoom)

    for name in self._players:
      marker = "> " if name == self._local_name else "  "
      psurf  = misc.smallItemFont.render(marker + name, 1, misc.lightColor)
      misc.screen.blit(psurf, (int(50 * misc.zoom), y))
      y += psurf.get_height() + int(2 * misc.zoom)

    y += int(10 * misc.zoom)

    # ── Chat log ─────────────────────────────────────────────────────
    chat_hdr = misc.itemFont.render("Chat:", 1, misc.lightColor)
    misc.screen.blit(chat_hdr, (int(30 * misc.zoom), y))
    y += chat_hdr.get_height() + int(4 * misc.zoom)

    for line in self._chat_log[-self._MAX_CHAT:]:
      lsurf = misc.popUpFont.render(line[:64], 1, misc.lightColor, (0, 0, 0))
      misc.screen.blit(lsurf, (int(30 * misc.zoom), y))
      y += lsurf.get_height() + int(2 * misc.zoom)

    # ── Chat input bar ───────────────────────────────────────────────
    input_y = int(misc.screen.get_height() * 0.85)
    if self._is_typing:
      in_surf = misc.popUpFont.render("> " + self._chat_in.render_text(), 1, (255, 255, 180), (0, 0, 0))
    else:
      in_surf = misc.popUpFont.render("", 1, misc.lightColor)
    misc.screen.blit(in_surf, (int(30 * misc.zoom), input_y))

    # ── Footer instructions ──────────────────────────────────────────
    foot_y = int(misc.screen.get_height() * 0.92)
    if self._is_host:
      foot = "[S] Start Race   [T] Chat   [ESC] Close Lobby"
      ip_text = "Your IP: " + self._local_ip
      ip_surf = misc.popUpFont.render(ip_text, 1, misc.darkColor, (0, 0, 0))
      misc.screen.blit(ip_surf, (int(30 * misc.zoom), foot_y - ip_surf.get_height() - 4))
    else:
      foot = "[T] Chat   [ESC] Leave"
    foot_surf = misc.popUpFont.render(foot, 1, misc.darkColor, (0, 0, 0))
    misc.screen.blit(foot_surf, (int(30 * misc.zoom), foot_y))

    pygame.display.flip()


class MenuText(Menu):
  '''Menu to display Text only'''

  def __init__(self, titleFont, title, gap, itemFont, listTexts):

    Menu.__init__(self, titleFont, title)

    self.gap = gap
    self.itemFont = itemFont
    self.listTexts = listTexts

    # Display the Title    
    titleMenu = SimpleTitleOnlyMenu(self.titleFont, self.title)

    y = titleMenu.startY

    for text in listTexts:
      # Display one line
      text = self.itemFont.render(text, 1, misc.lightColor)
      textRect = text.get_rect()
      textRect.centerx = misc.screen.get_rect().centerx
      textRect.y = y
      misc.screen.blit(text, textRect)
      y = y + textRect.height + self.gap

    pygame.display.flip()


class MenuLicense(Menu):
  '''Menu to display License'''

  def __init__(self, titleFont, title, gap, itemFont):

    Menu.__init__(self, titleFont, title)

    self.gap = gap
    self.itemFont = itemFont

    # Display the Title    
    titleMenu = SimpleTitleOnlyMenu(self.titleFont, self.title)

    y = titleMenu.startY

    # Display license on different lines
    text = self.itemFont.render("pyRacerz version " + misc.VERSION, 1, misc.lightColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap

    text = self.itemFont.render("Copyright (C) 2005 Jujucece (Julien Devemy) <jujucece@gmail.com>", 1, misc.lightColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap

    text = self.itemFont.render("pyRacerz comes with ABSOLUTELY NO WARRANTY.", 1, misc.lightColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap

    text = self.itemFont.render("This is free software, and you are welcome to redistribute it", 1, misc.lightColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap

    text = self.itemFont.render("under certain conditions; see the COPYING file for details.", 1, misc.lightColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    misc.screen.blit(text, textRect)
    textRect.y = y

    pygame.display.flip()


class MenuCredits(Menu):
  '''Menu to display Credits'''

  def __init__(self, titleFont, title, gap, itemFont):

    Menu.__init__(self, titleFont, title)

    self.gap = gap
    self.itemFont = itemFont

    # Display the Title    
    titleMenu = SimpleTitleOnlyMenu(self.titleFont, self.title)

    y = titleMenu.startY

    # Display license on different lines
    text = self.itemFont.render("Programming and tracks design: Jujucece <jujucece@gmail.com>", 1, misc.lightColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap

    text = self.itemFont.render("Base idea: Royale <http://royale.zerezo.com>", 1, misc.lightColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap

    text = self.itemFont.render("Font: Fontalicious <http://www.fontalicious.com>", 1, misc.lightColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap*3

    misc.screen.blit(text, textRect)

    text = self.itemFont.render("pyRacers would be nothing without:", 1, misc.lightColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    misc.screen.blit(text, textRect)
    y = y + textRect.height# + self.gap


    text = self.itemFont.render("GNU/Linux", 1, (255, 255, 255))
    textRect = text.get_rect()
    image = pygame.transform.rotozoom(pygame.image.load(os.path.join("credits", "linux.png")).convert_alpha(), 0, misc.zoom)
    imageRect = image.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx + imageRect.width/2
    textRect.y = y
    imageRect.x = textRect.x - imageRect.width - self.gap*3
    imageRect.centery = textRect.centery
    misc.screen.blit(text, textRect)
    misc.screen.blit(image, imageRect)
    y = y + textRect.height

    text = self.itemFont.render("Python", 1, (255, 255, 255))
    textRect = text.get_rect()
    image = pygame.transform.rotozoom(pygame.image.load(os.path.join("credits", "python.png")).convert_alpha(), 0, misc.zoom)
    imageRect = image.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx + imageRect.width/2
    textRect.y = y
    imageRect.x = textRect.x - imageRect.width - self.gap*3
    imageRect.centery = textRect.centery
    misc.screen.blit(text, textRect)
    misc.screen.blit(image, imageRect)
    y = y + textRect.height

    text = self.itemFont.render("Pygame", 1, (255, 255, 255))
    textRect = text.get_rect()
    image = pygame.transform.rotozoom(pygame.image.load(os.path.join("credits", "pygame.png")).convert_alpha(), 0, misc.zoom)
    imageRect = image.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx + imageRect.width/2
    textRect.y = y
    imageRect.x = textRect.x - imageRect.width - self.gap*3
    imageRect.centery = textRect.centery
    misc.screen.blit(text, textRect)
    misc.screen.blit(image, imageRect)
    y = y + textRect.height

    text = self.itemFont.render("Inkscape", 1, (255, 255, 255))
    textRect = text.get_rect()
    image = pygame.transform.rotozoom(pygame.image.load(os.path.join("credits", "inkscape.png")).convert_alpha(), 0, misc.zoom)
    imageRect = image.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx + imageRect.width/2
    textRect.y = y
    imageRect.x = textRect.x - imageRect.width - self.gap*3
    imageRect.centery = textRect.centery
    misc.screen.blit(text, textRect)
    misc.screen.blit(image, imageRect)
    y = y + textRect.height

    text = self.itemFont.render("The Gimp", 1, (255, 255, 255))
    textRect = text.get_rect()
    image = pygame.transform.rotozoom(pygame.image.load(os.path.join("credits", "gimp.png")).convert_alpha(), 0, misc.zoom)
    imageRect = image.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx + imageRect.width/2
    textRect.y = y
    imageRect.x = textRect.x - imageRect.width - self.gap*3
    imageRect.centery = textRect.centery
    misc.screen.blit(text, textRect)
    misc.screen.blit(image, imageRect)
    y = y + textRect.height

    text = self.itemFont.render("Vim", 1, (255, 255, 255))
    textRect = text.get_rect()
    image = pygame.transform.rotozoom(pygame.image.load(os.path.join("credits", "vim.png")).convert_alpha(), 0, misc.zoom)
    imageRect = image.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx + imageRect.width/2
    textRect.y = y
    imageRect.x = textRect.x - imageRect.width - self.gap*3
    imageRect.centery = textRect.centery
    misc.screen.blit(text, textRect)
    misc.screen.blit(image, imageRect)
    y = y + textRect.height

    pygame.display.flip()

class MenuHiscores(Menu):
  '''Menu to display Hiscores'''

  def __init__(self, titleFont, title, gap, itemFont):

    Menu.__init__(self, titleFont, title)

    self.gap = gap
    self.itemFont = itemFont

    # Display the Title    
    titleMenu = SimpleTitleOnlyMenu(self.titleFont, self.title)
    
    confFile=configparser.ConfigParser() 
    try:
      confFile.readfp(open(".pyRacerz.conf", "r")) 
      self.nbItem = 0

      for sect in confFile.sections():
        # If it's a Hi Score
        if sect.startswith("hi "):
          self.nbItem = self.nbItem + 1
    except Exception:
      self.nbItem = 0

    self.startItem = 0

    self.startY = titleMenu.startY

  def getInput(self):
  
    def handle_key(key):
      if key == K_UP:
        if self.nbItem > 5:
          if self.startItem != 0:
            self.startItem = self.startItem - 1
            return "refresh"
      elif key == K_DOWN:
        if self.nbItem > 5:
          if self.startItem != self.nbItem - 4:
            self.startItem = self.startItem + 1
            return "refresh"
      else:
        return 0
      return None

    return _menu_loop(self.refresh, handle_key)

  def refresh(self):

    y = self.startY

    confFile=configparser.SafeConfigParser() 
    try:
      confFile.readfp(open(".pyRacerz.conf", "r")) 
    except Exception:
      return

    deleteRect = pygame.Rect(0, self.startY, _screen_rect().width, _screen_rect().height - self.startY)
    misc.screen.blit(misc.background, deleteRect, deleteRect)

    # If there'are skipped items, display ...
    if self.startItem != 0:
      text = self.itemFont.render(". . .", 1, misc.lightColor)
    else:
      text = self.itemFont.render("", 1, misc.lightColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap

    j = 0
    for sect in confFile.sections():

      # If it's not a Hi Score
      if not sect.startswith("hi "):
        continue

      # Skip the first non visible items
      if self.startItem <= j and j < 4 + self.startItem:
        # Display Track information
        text = self.itemFont.render(sect.split()[1], 1, misc.lightColor)
        textRect = text.get_rect()
        textRect.centerx = misc.screen.get_rect().centerx
        textRect.y = y
        misc.screen.blit(text, textRect)
        y = y + textRect.height + self.gap

        # Search for each level HiScore
        textHi = ""
        for i in [1, 2, 3]:
          try:
            hL = confFile.get(sect, "level" + str(i)).split()
            h = sha1.new(sect.split()[1])
            h.update("level" + str(i))
            h.update(hL[0])
            h.update(hL[1])
            if hL[2] == h.hexdigest():
              textHi = textHi + hL[0] + " " + misc.chrono2Str(int(hL[1])) + " / "
            else:
              textHi = textHi + "CORRUPTED /"
          except Exception:
            textHi = textHi + "- / "
      
        textHi = textHi.rstrip('/ ')
      
        textHi = textHi + " | "

        for i in [-1, -2, -3]:
          try:
            hL = confFile.get(sect, "level" + str(i)).split()
            h = sha1.new(sect.split()[1])
            h.update("level" + str(i))
            h.update(hL[0])
            h.update(hL[1])
            if hL[2] == h.hexdigest():
              textHi = textHi + hL[0] + " " + misc.chrono2Str(int(hL[1])) + " / "
            else:
              textHi = textHi + "CORRUPTED /"
          except Exception:
            textHi = textHi + "- / "

        textHi = textHi.rstrip('/ ')

        text = self.itemFont.render(textHi, 1, misc.lightColor)
        textRect = text.get_rect()
        textRect.centerx = misc.screen.get_rect().centerx
        textRect.y = y
        misc.screen.blit(text, textRect)
        y = y + textRect.height + self.gap

      j = j + 1

    # If there'are skipped items after, display ...
    if self.nbItem - self.startItem > 4:
      text = self.itemFont.render(". . .", 1, misc.lightColor)
    else:
      text = self.itemFont.render("", 1, misc.lightColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap
    
    pygame.display.flip()

