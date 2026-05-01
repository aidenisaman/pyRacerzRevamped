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

import random
import os
import sys
import configparser
#import sha

VERSION = "0.2"

# Bright white (for selected text)
lightColor = (255, 255, 255)

# Strong gray (for unselected text)
darkColor = (180, 180, 180)

background = None
main_menu_background = None
screen = None

popUpFont = None
titleFont = None
itemFont = None
smallItemFont = None
bigFont = None

music = 1

zoom = 1
USE_SYS_FONT = True
FONT_NAME = "verdana"
USE_BG_IMAGE = True
BACKGROUND_FILE = os.path.join("credits", "regular_menu_bg.png")
main_menu_bg_file = os.path.join("credits", "pyracerz menu.png")
BACKGROUND_COLOR = (0, 0, 0)

def init():
  global popUpFont
  global titleFont
  global itemFont
  global smallItemFont
  global bigFont
  global background

  # Prefer system font if requested (useful for quick changes)
  if USE_SYS_FONT:
    popUpFont = pygame.font.SysFont(FONT_NAME, int(24*zoom))
    titleFont = pygame.font.SysFont(FONT_NAME, int(52*zoom))
    itemFont = pygame.font.SysFont(FONT_NAME, int(34*zoom))
    smallItemFont = pygame.font.SysFont(FONT_NAME, int(30*zoom))
    bigFont = pygame.font.SysFont(FONT_NAME, int(66*zoom))
  else:
    try:
      popUpFont = pygame.font.Font(os.path.join("fonts", "arcade_pizzadude", "ARCADE.TTF"), int(24*zoom))
      titleFont = pygame.font.Font(os.path.join("fonts", "alba", "ALBA____.TTF"), int(52*zoom))
      itemFont = pygame.font.Font(os.path.join("fonts", "alba", "ALBA____.TTF"), int(34*zoom))
      smallItemFont = pygame.font.Font(os.path.join("fonts", "alba", "ALBA____.TTF"), int(30*zoom))
      bigFont = pygame.font.Font(os.path.join("fonts", "alba", "ALBA____.TTF"), int(66*zoom))
    except Exception as e:
      print("Cannot initialize bundled TTF fonts, falling back to system fonts:")
      print(e)
      popUpFont = pygame.font.SysFont(FONT_NAME, int(24*zoom))
      titleFont = pygame.font.SysFont(FONT_NAME, int(52*zoom))
      itemFont = pygame.font.SysFont(FONT_NAME, int(34*zoom))
      smallItemFont = pygame.font.SysFont(FONT_NAME, int(30*zoom))
      bigFont = pygame.font.SysFont(FONT_NAME, int(66*zoom))

  # Configure background: use image only if enabled, otherwise solid color
  # Configure background: use image only if enabled, otherwise solid color
  target_w = int(1024 * zoom)
  target_h = int(768 * zoom)
  if USE_BG_IMAGE:
    try:
      img = pygame.image.load(BACKGROUND_FILE)
      # Prefer convert_alpha if the image has transparency, fall back to convert
      try:
        img = img.convert_alpha()
      except Exception:
        img = img.convert()

      iw, ih = img.get_size()
      # Stretch the image to fill the entire screen
      new_w = target_w
      new_h = target_h

      # Use smoothscale when available for better quality
      try:
        img = pygame.transform.smoothscale(img, (new_w, new_h))
      except Exception:
        img = pygame.transform.scale(img, (new_w, new_h))

      # No offset needed since we're stretching to full size
      offset_x = 0
      offset_y = 0
      background = pygame.Surface((target_w, target_h)).convert()
      background.blit(img, (offset_x, offset_y))
    except Exception as e:
      print("Warning: unable to load background image, using solid color background:")
      print(e)
      background = pygame.Surface((target_w, target_h))
      background.fill(BACKGROUND_COLOR)
  else:
    background = pygame.Surface((target_w, target_h))
    background.fill(BACKGROUND_COLOR)

  # Load main menu background
  global main_menu_background
  main_menu_bg_file = os.path.join("credits", "pyracerz menu.png")
  try:
    img = pygame.image.load(main_menu_bg_file)
    try:
      img = img.convert_alpha()
    except Exception:
      img = img.convert()

    iw, ih = img.get_size()
    new_w = target_w
    new_h = target_h

    try:
      img = pygame.transform.smoothscale(img, (new_w, new_h))
    except Exception:
      img = pygame.transform.scale(img, (new_w, new_h))

    offset_x = 0
    offset_y = 0
    main_menu_background = pygame.Surface((target_w, target_h)).convert()
    main_menu_background.blit(img, (offset_x, offset_y))
  except Exception as e:
    print("Warning: unable to load main menu background image, using default background:")
    print(e)
    main_menu_background = background

  # Enable key repeat so held backspace/letters repeat in text-entry menus
  # (400 ms initial delay, 50 ms repeat interval)
  pygame.key.set_repeat(400, 50)

def chrono2Str(chrono):
  return str(chrono/100.0).replace(".", "''")

def wait4Key():
  # Clear event queue
  pygame.event.clear()

  # Wait for key Input
  ok = 0
  while ok == 0:
    for event in pygame.event.get():
      if event.type == QUIT:
        sys.exit(0)
      if event.type == KEYDOWN:
        ok = 1
        break

  # Clear event queue
  pygame.event.clear()  

def startMenuMusic():
  global music

  stopMusic()

  if music != 1:
    return

  try:
    music_file = os.path.join("musics", "menu_music.mp3")
    pygame.mixer.music.load(music_file)
    pygame.mixer.music.set_volume(0.35)
    pygame.mixer.music.play(-1)
  except Exception as e:
    print("Menu music unable to play...")
    print(e)


def startRaceMusic(track_name=None):
  global music

  stopMusic()

  if music != 1:
    return

  try:
    track_music = {
      "beach": "track_music_2.mp3",
      "wave": "track_music_1.mp3",

      "city": "track_music_3.mp3",
      "forest": "track_music_2.mp3",

      "desert": "track_music_1.mp3",
      "mountain": "track_music_3.mp3",

      "formula": "track_music_4.mp3",
      "nascar": "track_music_4.mp3",
    }

    filename = track_music.get(track_name, "track_music_1.mp3")
    music_file = os.path.join("musics", filename)

    pygame.mixer.music.load(music_file)
    pygame.mixer.music.set_volume(0.55)
    pygame.mixer.music.play(-1)
  except Exception as e:
    print("Race music unable to play for track:", track_name)
    print(e)


def startResultMusic():
  global music

  stopMusic()

  if music != 1:
    return

  try:
    music_file = os.path.join("musics", "result_music.mp3")
    pygame.mixer.music.load(music_file)
    pygame.mixer.music.set_volume(0.45)
    pygame.mixer.music.play(-1)
  except Exception as e:
    print("Result music unable to play...")
    print(e)

def stopMusic():
  pygame.mixer.music.fadeout(1000)

class PopUp:
  def __init__(self, track):
    self.track = track
    self.listElement = []
    self.rect = pygame.Rect(0, 688*zoom, 260*zoom, 80*zoom)

  def addElement(self, car, text):
    self.listElement.append([car, text, 0])

  def display(self):

    #Erase PopUp Area
    screen.blit(self.track.track, self.rect, self.rect)
        
    #If useful, display PopUp Area
    if self.listElement != []:

      y = 750*zoom

      for elem in self.listElement:
        x = 0
        carMini = elem[0].miniCar
        carMiniRect = carMini.get_rect()
        carMiniRect.x = x
        x = x + carMiniRect.width

        text = popUpFont.render(elem[1], 1, lightColor, (0, 0, 0))
        textRect = text.get_rect()
        textRect.x = x
        textRect.y = y
        screen.blit(text, textRect)

        carMiniRect.centery = textRect.centery 
        screen.blit(carMini, carMiniRect)

        # Remove an old element
        if elem[2] == 400:
          self.listElement.remove(elem)
        else:
          elem[2] = elem[2] + 1
        y = y - textRect.height

def addHiScore(track, player):

  fileExist = 1

  confFile=configparser.ConfigParser() 
  try:
    confFile.read_file(open(".pyRacerz.conf", "r")) 
  except Exception:
    fileExist = 0
  
  # If the track is not represented, create it
  if fileExist == 0 or not confFile.has_section("hi " + track.name):
    fwrite = open(".pyRacerz.conf", "w+")
    confFile.add_section("hi " + track.name)
    confFile.write(fwrite)
    confFile.read_file(open(".pyRacerz.conf", "r")) 

  # For the Inverse
  if track.reverse == 0:
    level = player.level
  else:
    level = -player.level

  # If the Level is not represented create it and put the Hi-scores
  if not confFile.has_option("hi " + track.name, "level" + str(level)):
    h = sha1()
    h.update(str(track.name).encode())
    h.update(("level" + str(level)).encode())
    h.update(player.name.encode())
    h.update(str(player.bestChrono).encode())
    fwrite = open(".pyRacerz.conf", "w+")
    confFile.set("hi " + track.name, "level" + str(level), player.name + " " + str(player.bestChrono) + " " + h.hexdigest())
    confFile.write(fwrite)
    return 1
  else:
    hi = confFile.get("hi " + track.name, "level" + str(level)).split()
    h = sha1()
    h.update(str(track.name).encode())
    h.update(("level" + str(level)).encode())
    h.update(hi[0].encode())
    h.update(hi[1].encode())
    if hi[2] == h.hexdigest():
      if int(hi[1]) > player.bestChrono:
        h = sha1()
        h.update(str(track.name).encode())
        h.update(("level" + str(level)).encode())
        h.update(player.name.encode())
        h.update(str(player.bestChrono).encode())
        fwrite = open(".pyRacerz.conf", "w+")
        confFile.set("hi " + track.name, "level" + str(level), player.name + " " + str(player.bestChrono) + " " + h.hexdigest())
        confFile.write(fwrite)
        return 1
      else:
        return 0
    else:
      # If the HiScore is Corrupted, erase it
      h = sha1()
      h.update(str(track.name).encode())
      h.update(("level" + str(level)).encode())
      h.update(player.name.encode())
      h.update(str(player.bestChrono).encode())
      fwrite = open(".pyRacerz.conf", "w+")
      confFile.set("hi " + track.name, "level" + str(level), player.name + " " + str(player.bestChrono) + " " + h.hexdigest())
      confFile.write(fwrite)
      return 1
    
def getUnlockLevel():

  confFile=configparser.ConfigParser() 
  try:
    confFile.readfp(open(".pyRacerz.conf", "r")) 
  except Exception:
    return 0

  if not confFile.has_section("unlockLevel"):
    return 0
  if not confFile.has_option("unlockLevel", "key"):
    return 0

  key = confFile.get("unlockLevel", "key").split()
  h = sha1()
  h.update(str("pyRacerz").encode())

  h.update(str(key[0]).encode())
  if h.hexdigest() == key[1]:
    return key[0]
  else:
    return 0

class TextInput:
  """Reusable single-line text-input helper.

  Decouples key-handling from any specific menu class.  Call ``feed_key``
  on each KEYDOWN event; it returns ``True`` when the text changed so the
  caller knows to trigger a refresh.  ``render_text`` returns the display
  string with a blinking-cursor ``_`` appended when the field is not full.

  Supported keys: K_a–K_z (uppercased), K_0–K_9, K_BACKSPACE.
  """

  def __init__(self, max_length: int, initial: str = "", allow_space: bool = False) -> None:
    self.max_length  = max_length
    self.allow_space = allow_space
    self.text = initial[:max_length]

  def feed_key(self, key) -> bool:
    """Process a pygame key code. Returns True if the text changed."""
    if key == K_BACKSPACE:
      if self.text:
        self.text = self.text[:-1]
        return True
    elif K_a <= key <= K_z:
      if len(self.text) < self.max_length:
        self.text += pygame.key.name(key).upper()
        return True
    elif K_0 <= key <= K_9:
      if len(self.text) < self.max_length:
        self.text += pygame.key.name(key)
        return True
    elif key == K_SPACE and self.allow_space:
      if len(self.text) < self.max_length:
        self.text += " "
        return True
    return False

  def render_text(self) -> str:
    """Return display string; appends '_' cursor when field is not full."""
    if len(self.text) < self.max_length:
      return self.text + "_"
    return self.text


class IPTextInput(TextInput):
  """TextInput variant for IPv4 address entry.

  Accepts digits (0-9) and dots (.) only; letters are ignored.
  Max length defaults to 15 ("255.255.255.255").
  """

  def __init__(self, max_length: int = 15, initial: str = "") -> None:
    super().__init__(max_length, initial, allow_space=False)

  def feed_key(self, key) -> bool:
    if key == K_BACKSPACE:
      if self.text:
        self.text = self.text[:-1]
        return True
    elif K_0 <= key <= K_9:
      if len(self.text) < self.max_length:
        self.text += pygame.key.name(key)
        return True
    elif key == K_PERIOD:
      if len(self.text) < self.max_length and not self.text.endswith("."):
        self.text += "."
        return True
    return False


def setUnlockLevel(lck):
  # Only change the unlock level if it's better than the actual one
  if getUnlockLevel() >= lck:
    return

  fileExist = 1

  confFile=configparser.ConfigParser() 
  try:
    confFile.read_file(open(".pyRacerz.conf", "r")) 
  except Exception:
    fileExist = 0

  if fileExist == 0 or not confFile.has_section("unlockLevel"):
    fwrite = open(".pyRacerz.conf", "w+")
    confFile.add_section("unlockLevel")
    confFile.write(fwrite)
    confFile.read_file(open(".pyRacerz.conf", "r"))

  h = sha1("pyRacerz".encode())

  h.update(str(lck).encode())
  fwrite = open(".pyRacerz.conf", "w+")
  confFile.set("unlockLevel", "key", str(lck) + " " + h.hexdigest())
  confFile.write(fwrite)
  fwrite.close()
