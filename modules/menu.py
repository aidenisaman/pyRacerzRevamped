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

class Menu:
  '''Base class for any pyRacerz Menu'''

  def __init__(self, titleFont, title, background=None):

    self.titleFont = titleFont
    self.title = title
    self.background = background or misc.background


class SimpleMenu(Menu):
  '''Menu with a simple selection between items'''

  def __init__(self, titleFont, title, gap, itemFont, listItem, background=None):

    Menu.__init__(self, titleFont, title, background)

    self.gap = gap
    self.itemFont = itemFont
    self.listItem = listItem
    
    # Display the Title    
    titleMenu = SimpleTitleOnlyMenu(self.titleFont, self.title, self.background)

    self.startY = titleMenu.startY

    # The first item is selected
    self.select = 1

  def getInput(self):
  
    self.refresh()

    while 1:

      # Get the event keys
      for event in pygame.event.get():
    
        if event.type == QUIT:
          sys.exit(0)
        elif event.type == KEYDOWN:
          if event.key == K_ESCAPE:
            return -1
          if event.key == K_UP:
            if self.select != 1:
              self.select = self.select - 1
            else:
              self.select = len(self.listItem)
            self.refresh()
          if event.key == K_DOWN:
            if self.select != len(self.listItem):
              self.select = self.select + 1
            else:
              self.select = 1
            self.refresh()
          if event.key == K_RETURN:
            return self.select
      pygame.time.delay(10)

  def refresh(self):

    # Calculate total height of menu items
    item_height = self.itemFont.get_height()
    total_items = len(self.listItem)
    total_height = total_items * item_height + (total_items - 1) * self.gap
    screen_h = int(768 * misc.zoom)
    center_y = (screen_h - total_height) // 2
    y = center_y - 10  # Move up a little

    i = 1

    # Print the menu items
    for item in self.listItem:
      if i == self.select:
        text = self.itemFont.render("> " + item + " <", 1, misc.lightColor)
      else:
        text = self.itemFont.render(item, 1, misc.darkColor)
      textRect = text.get_rect()
      textRect.centerx = misc.screen.get_rect().centerx
      textRect.y = y
      deleteRect = (0, textRect.y, 1024*misc.zoom, textRect.height)
      misc.screen.blit(self.background, deleteRect, deleteRect)
      misc.screen.blit(text, textRect)
      y = y + textRect.height + self.gap
      i = i + 1

    pygame.display.flip()


class SimpleTitleOnlyMenu(Menu):
  '''Menu only with a title'''

  def __init__(self, titleFont, title, background=None):

    Menu.__init__(self, titleFont, title, background)

    # Put the background
    misc.screen.blit(self.background, (0, 0))
    overlay = pygame.Surface(misc.screen.get_size())
    overlay.set_alpha(80)
    overlay.fill((0, 0, 0))
    misc.screen.blit(overlay, (0, 0))

    # Put title at different positions depending on which background is used
    if self.background == misc.main_menu_background:
        y = int(680 * misc.zoom)   # landing page title near bottom
    else:
        y = 10                     # all other menus stay at top

    # Print the title
    textTitle = self.titleFont.render(self.title, 1, misc.lightColor)
    textRectTitle = textTitle.get_rect()
    textRectTitle.centerx = misc.screen.get_rect().centerx
    textRectTitle.y = y
    y = y + textRectTitle.height / 2

    # Print the dotted line only for non-landing pages
    if self.background == misc.main_menu_background:
        text = self.titleFont.render("", 1, misc.lightColor)
    else:
        text = self.titleFont.render("...............", 1, misc.lightColor)

    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y

    deleteRect = (0, textRect.y, 1024 * misc.zoom, textRect.height)
    deleteRectTitle = (0, textRectTitle.y, 1024 * misc.zoom, textRectTitle.height)

    misc.screen.blit(self.background, deleteRectTitle, deleteRectTitle)
    misc.screen.blit(self.background, deleteRect, deleteRect)
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
            self.listIconTracks.append(
                pygame.transform.scale(
                    track.getImageFromTrackName(trackName),
                    (int(1024 * 0.1 * misc.zoom), int(768 * 0.1 * misc.zoom))
                )
            )

        # Display the Title
# Display the Title    
        titleMenu = SimpleTitleOnlyMenu(self.titleFont, self.title)
        self.startY = titleMenu.startY

        # The first item is selected
        self.select = 1
        self.reverse = 0

        self.moveSound = pygame.mixer.Sound(os.path.join("sounds", "menu_move.wav"))
        self.moveSound.set_volume(0.5)

    def getInput(self):
      self.refresh()

      cols = 4
      total_tracks = len(self.listIconTracks)

      while 1:
          for event in pygame.event.get():
              if event.type == QUIT:
                  sys.exit(0)

              elif event.type == KEYDOWN:
                  if event.key == K_ESCAPE:
                      return -1

                  if event.key == K_LEFT:
                      if self.select > 1:
                          self.select -= 1
                      else:
                          self.select = total_tracks
                      self.moveSound.play()
                      self.refresh()

                  if event.key == K_RIGHT:
                      if self.select < total_tracks:
                          self.select += 1
                      else:
                          self.select = 1
                      self.moveSound.play()
                      self.refresh()

                  if event.key == K_UP:
                      new_select = self.select - cols
                      if new_select >= 1:
                          self.select = new_select
                          self.moveSound.play()
                      self.refresh()

                  if event.key == K_DOWN:
                      new_select = self.select + cols
                      if new_select <= total_tracks:
                          self.select = new_select
                          self.moveSound.play()
                      self.refresh()

                  if event.key == K_r:
                      if self.reverse == 0:
                          self.reverse = 1
                      else:
                          self.reverse = 0
                      self.moveSound.play()
                      self.refresh()

                  if event.key == K_RETURN:
                      return [self.listAvailableTrackNames[self.select - 1], self.reverse]

          pygame.time.delay(10)

    def refresh(self):
      misc.screen.blit(self.background, (0, 0))
      titleMenu = SimpleTitleOnlyMenu(self.titleFont, self.title)

      tile_w = int(180 * misc.zoom)
      tile_h = int(110 * misc.zoom)

      selected_w = int(205 * misc.zoom)
      selected_h = int(130 * misc.zoom)

      gap_x = int(30 * misc.zoom)
      gap_y = int(50 * misc.zoom)
      cols = 4

      screen_rect = misc.screen.get_rect()
      grid_start_y = self.startY + int(80 * misc.zoom)

      total_grid_w = cols * tile_w + (cols - 1) * gap_x
      start_x = (screen_rect.width - total_grid_w) // 2

      for idx, iconTrack in enumerate(self.listIconTracks):
          row = idx // cols
          col = idx % cols

          base_x = start_x + col * (tile_w + gap_x)
          base_y = grid_start_y + row * (tile_h + gap_y + 30)

          display_name = self.listAvailableTrackNames[idx].capitalize()
          if idx + 1 == self.select and self.reverse == 1:
              display_name += " REV"

          if idx + 1 == self.select:
              draw_w = selected_w
              draw_h = selected_h
              draw_x = base_x - (selected_w - tile_w) // 2
              draw_y = base_y - int(10 * misc.zoom)

              scaled_icon = pygame.transform.scale(iconTrack, (draw_w, draw_h))
              icon_rect = pygame.Rect(draw_x, draw_y, draw_w, draw_h)

              misc.screen.blit(scaled_icon, icon_rect)
              pygame.draw.rect(misc.screen, misc.lightColor, icon_rect, 4)

              label = self.itemFont.render(display_name, True, misc.lightColor)
              label_rect = label.get_rect()
              label_rect.centerx = icon_rect.centerx
              label_rect.y = icon_rect.bottom + int(8 * misc.zoom)
              misc.screen.blit(label, label_rect)

          else:
              scaled_icon = pygame.transform.scale(iconTrack, (tile_w, tile_h))
              icon_rect = pygame.Rect(base_x, base_y, tile_w, tile_h)

              misc.screen.blit(scaled_icon, icon_rect)
              pygame.draw.rect(misc.screen, misc.darkColor, icon_rect, 2)

              label = self.itemFont.render(display_name, True, misc.darkColor)
              label_rect = label.get_rect()
              label_rect.centerx = icon_rect.centerx
              label_rect.y = icon_rect.bottom + int(8 * misc.zoom)
              misc.screen.blit(label, label_rect)

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
      self.refresh()

      cols = 4
      total_values = self.vMax - self.vMin + 1

      while 1:
          for event in pygame.event.get():
              if event.type == QUIT:
                  sys.exit(0)

              elif event.type == KEYDOWN:
                  if event.key == K_ESCAPE:
                      return -1

                  if event.key == K_LEFT:
                      if self.select > self.vMin:
                          self.select -= 1
                      else:
                          self.select = self.vMax
                      self.refresh()

                  if event.key == K_RIGHT:
                      if self.select < self.vMax:
                          self.select += 1
                      else:
                          self.select = self.vMin
                      self.refresh()

                  if event.key == K_UP:
                      new_select = self.select - cols
                      if new_select >= self.vMin:
                          self.select = new_select
                      self.refresh()

                  if event.key == K_DOWN:
                      new_select = self.select + cols
                      if new_select <= self.vMax:
                          self.select = new_select
                      self.refresh()

                  if event.key == K_RETURN:
                      return self.select

          pygame.time.delay(10)

  def refresh(self):
    misc.screen.blit(self.background, (0, 0))
    titleMenu = SimpleTitleOnlyMenu(self.titleFont, self.title)

    tile_w = int(100 * misc.zoom)
    tile_h = int(100 * misc.zoom)
    selected_w = int(115 * misc.zoom)
    selected_h = int(115 * misc.zoom)

    gap_x = int(25 * misc.zoom)
    gap_y = int(35 * misc.zoom)
    cols = 4

    values = list(range(self.vMin, self.vMax + 1))

    screen_rect = misc.screen.get_rect()
    grid_start_y = self.startY + int(100 * misc.zoom)

    total_grid_w = cols * tile_w + (cols - 1) * gap_x
    start_x = (screen_rect.width - total_grid_w) // 2

    for idx, value in enumerate(values):
        row = idx // cols
        col = idx % cols

        x = start_x + col * (tile_w + gap_x)
        y = grid_start_y + row * (tile_h + gap_y)

        if value == self.select:
            draw_w = selected_w
            draw_h = selected_h
            draw_x = x - (selected_w - tile_w) // 2
            draw_y = y - int(8 * misc.zoom)

            rect = pygame.Rect(draw_x, draw_y, draw_w, draw_h)
            pygame.draw.rect(misc.screen, misc.lightColor, rect, 4)

            text = self.itemFont.render(str(value), True, misc.lightColor)
            text_rect = text.get_rect(center=rect.center)
            misc.screen.blit(text, text_rect)

        else:
            rect = pygame.Rect(x, y, tile_w, tile_h)
            pygame.draw.rect(misc.screen, misc.darkColor, rect, 2)

            text = self.itemFont.render(str(value), True, misc.darkColor)
            text_rect = text.get_rect(center=rect.center)
            misc.screen.blit(text, text_rect)

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

    # "" is default
    self.text = ""

  def getInput(self):
  
    self.refresh()

    while 1:

      # Get the event keys
      for event in pygame.event.get():
    
        if event.type == QUIT:
          sys.exit(0)
        elif event.type == KEYDOWN:
          if event.key == K_ESCAPE:
            return None
          if event.key >= K_a and event.key <= K_z:
            if len(self.text) < self.maxLenght:
              self.text = self.text + pygame.key.name(event.key).upper()
            self.refresh()
          if event.key == K_BACKSPACE:
            if len(self.text) > 0:
              # There's surely a simpler way to erase the last Char !!!
              self.text = string.rstrip(self.text, self.text[len(self.text)-1])
              self.refresh()
          if event.key == K_RETURN:
            return self.text
      pygame.time.delay(10)

  def refresh(self):

    y = self.startY

    # Print the Text
    if len(self.text) != self.maxLenght:
      text = self.itemFont.render(self.text + "_", 1, misc.lightColor)
    else:
      text = self.itemFont.render(self.text, 1, misc.lightColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    deleteRect = (0, textRect.y, 1024*misc.zoom, textRect.height)
    misc.screen.blit(self.background, deleteRect, deleteRect)
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

    self.level = 1

    self.keyAccel = K_UP
    self.keyBrake = K_DOWN
    self.keyLeft = K_LEFT
    self.keyRight = K_RIGHT

  def getInput(self):
  
    self.refresh()

    while 1:

      # Get the event keys
      for event in pygame.event.get():
    
        if event.type == QUIT:
          sys.exit(0)
        elif event.type == KEYDOWN:
          if event.key == K_ESCAPE:
            return -1
          if event.key == K_UP:
            if self.select != 1:
              self.select = self.select - 1
            else:
              self.select = 8
            self.refresh()
          if event.key == K_DOWN:
            if self.select != 8:
              self.select = self.select + 1
            else:
              self.select = 1
            self.refresh()
          if event.key == K_LEFT:
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
            self.refresh()
          if event.key == K_RIGHT:
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
            self.refresh()

          # Key Enter used for Command Keys Enter
          if event.key == K_RETURN:
            if self.select == 4:
              self.keyAccel = None
              self.refresh()
              key = 0
              while key == 0:
                for event2 in pygame.event.get():
                  if event2.type == KEYDOWN:
                    self.keyAccel = event2.key
                    key = 1
            if self.select == 5:
              self.keyBrake = None
              self.refresh()
              key = 0
              while key == 0:
                for event2 in pygame.event.get():
                  if event2.type == KEYDOWN:
                    self.keyBrake = event2.key
                    key = 1
            if self.select == 6:
              self.keyLeft = None
              self.refresh()
              key = 0
              while key == 0:
                for event2 in pygame.event.get():
                  if event2.type == KEYDOWN:
                    self.keyLeft = event2.key
                    key = 1
            if self.select == 7:
              self.keyRight = None
              self.refresh()
              key = 0
              while key == 0:
                for event2 in pygame.event.get():
                  if event2.type == KEYDOWN:
                    self.keyRight = event2.key
                    key = 1
            self.refresh()

          # Enter the Pseudo
          if event.key >= K_a and event.key <= K_z  and self.select == 2:
            if len(self.pseudo) >= 3:
              self.pseudo = pygame.key.name(event.key).upper()
            else:
              self.pseudo = self.pseudo + pygame.key.name(event.key).upper()
            self.refresh()

          if event.key == K_RETURN and self.select == 8:
            # Careful to get the real carColor number and not the fake one (caused by the listdir)
            return player.HumanPlayer(self.pseudo, int(self.listAvailableCarNames[self.carColor-1].replace("car", "")), self.level, self.keyAccel, self.keyBrake, self.keyLeft, self.keyRight)

      pygame.time.delay(10)


  def refresh(self):

    y = self.startY

    i = 1


    # 1. is Car selection
    if i == self.select:
      text = self.itemFont.render("<     >", 1, misc.lightColor)
    else:
      text = self.itemFont.render("<     >", 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    deleteRect = (0, textRect.y, 1024*misc.zoom, textRect.height)
    misc.screen.blit(self.background, deleteRect, deleteRect)
    misc.screen.blit(text, textRect)

    # Print the selected Car
    carRect = self.listCars[self.carColor - 1].get_rect()
    carRect.centerx = misc.screen.get_rect().centerx
    carRect.y = y + (textRect.height - carRect.height)/2

    misc.screen.blit(self.listCars[self.carColor - 1], carRect)
    y = y + textRect.height + self.gap
    i = i + 1

    
    # 2. is Pseudo selection
    if i == self.select:
      text = self.itemFont.render(self.pseudo, 1, misc.lightColor)
    else:
      text = self.itemFont.render(self.pseudo, 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    deleteRect = (0, textRect.y, 1024*misc.zoom, textRect.height)
    misc.screen.blit(self.background, deleteRect, deleteRect)
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap
    i = i + 1

    # 3. is Level selection
    if i == self.select:
      text = self.itemFont.render("< Level " + str(self.level) + " >", 1, misc.lightColor)
    else:
      text = self.itemFont.render("< Level " + str(self.level) + " >", 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    deleteRect = (0, textRect.y, 1024*misc.zoom, textRect.height)
    misc.screen.blit(self.background, deleteRect, deleteRect)
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
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    deleteRect = (0, textRect.y, 1024*misc.zoom, textRect.height)
    misc.screen.blit(self.background, deleteRect, deleteRect)
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
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    deleteRect = (0, textRect.y, 1024*misc.zoom, textRect.height)
    misc.screen.blit(self.background, deleteRect, deleteRect)
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
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    deleteRect = (0, textRect.y, 1024*misc.zoom, textRect.height)
    misc.screen.blit(self.background, deleteRect, deleteRect)
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
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    deleteRect = (0, textRect.y, 1024*misc.zoom, textRect.height)
    misc.screen.blit(self.background, deleteRect, deleteRect)
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap
    i = i + 1

    # 8. is Go
    if i == self.select:
      text = self.itemFont.render("GO", 1, misc.lightColor)
    else:
      text = self.itemFont.render("GO", 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    deleteRect = (0, textRect.y, 1024*misc.zoom, textRect.height)
    misc.screen.blit(self.background, deleteRect, deleteRect)
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
  
    self.refresh()

    while 1:

      # Get the event keys
      for event in pygame.event.get():
    
        if event.type == QUIT:
          sys.exit(0)
        elif event.type == KEYDOWN:
          if event.key == K_ESCAPE:
            return -1
          if event.key == K_UP:
            if self.select != 1:
              self.select = self.select - 1
            else:
              self.select = 3
            self.refresh()
          if event.key == K_DOWN:
            if self.select != 3:
              self.select = self.select + 1
            else:
              self.select = 1
            self.refresh()
          if event.key == K_LEFT:
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
            self.refresh()
          if event.key == K_RIGHT:
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
            self.refresh()

          if event.key == K_RETURN and self.select == 3:
            # Careful to get the real carColor number and not the fake one (caused by the listdir)
            return player.RobotPlayer(int(self.listAvailableCarNames[self.carColor-1].replace("car", "")), self.level)

      pygame.time.delay(10)


  def refresh(self):

    y = self.startY

    i = 1


    # 1. is Car selection
    if i == self.select:
      text = self.itemFont.render("<     >", 1, misc.lightColor)
    else:
      text = self.itemFont.render("<     >", 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    deleteRect = (0, textRect.y, 1024*misc.zoom, textRect.height)
    misc.screen.blit(self.background, deleteRect, deleteRect)
    misc.screen.blit(text, textRect)

    # Print the selected Car
    carRect = self.listCars[self.carColor - 1].get_rect()
    carRect.centerx = misc.screen.get_rect().centerx
    carRect.y = y + (textRect.height - carRect.height)/2

    misc.screen.blit(self.listCars[self.carColor - 1], carRect)
    y = y + textRect.height + self.gap
    i = i + 1

    # 2. is Level selection
    if i == self.select:
      text = self.itemFont.render("< Level " + str(self.level) + " >", 1, misc.lightColor)
    else:
      text = self.itemFont.render("< Level " + str(self.level) + " >", 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    deleteRect = (0, textRect.y, 1024*misc.zoom, textRect.height)
    misc.screen.blit(self.background, deleteRect, deleteRect)
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap
    i = i + 1

    # 3. is Go
    if i == self.select:
      text = self.itemFont.render("GO", 1, misc.lightColor)
    else:
      text = self.itemFont.render("GO", 1, misc.darkColor)
    textRect = text.get_rect()
    textRect.centerx = misc.screen.get_rect().centerx
    textRect.y = y
    deleteRect = (0, textRect.y, 1024*misc.zoom, textRect.height)
    misc.screen.blit(self.background, deleteRect, deleteRect)
    misc.screen.blit(text, textRect)
    y = y + textRect.height + self.gap
    i = i + 1

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
  
    self.refresh()

    while 1:

      # Get the event keys
      for event in pygame.event.get():
    
        if event.type == QUIT:
          sys.exit(0)
        elif event.type == KEYDOWN:
          if event.key == K_UP:
            if self.nbItem > 5 :
              if self.startItem != 0:
                self.startItem = self.startItem - 1
                self.refresh()
          elif event.key == K_DOWN:
            if self.nbItem > 5 :
              if self.startItem != self.nbItem - 4:
                self.startItem = self.startItem + 1
                self.refresh()
          else:
            return
      pygame.time.delay(10)

  def refresh(self):

    y = self.startY

    confFile=configparser.SafeConfigParser() 
    try:
      confFile.readfp(open(".pyRacerz.conf", "r")) 
    except Exception:
      return

    deleteRect = (0, self.startY, 1024*misc.zoom, 768*misc.zoom-self.startY)
    misc.screen.blit(self.background, deleteRect, deleteRect)

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

