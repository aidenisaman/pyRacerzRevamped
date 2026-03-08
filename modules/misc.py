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

lightColor = (230, 230, 255)
darkColor = (118, 118, 151)

background = None
screen = None

popUpFont = None
titleFont = None
itemFont = None
smallItemFont = None
bigFont = None

music = 1

zoom = 1

def init():
  global popUpFont
  global titleFont
  global itemFont
  global smallItemFont
  global bigFont
  global background

  try:
    popUpFont = pygame.font.Font(os.path.join("fonts", "arcade_pizzadude", "ARCADE.TTF"), int(24*zoom))
    titleFont = pygame.font.Font(os.path.join("fonts", "alba", "ALBA____.TTF"), int(52*zoom))
    itemFont = pygame.font.Font(os.path.join("fonts", "alba", "ALBA____.TTF"), int(34*zoom))
    smallItemFont = pygame.font.Font(os.path.join("fonts", "alba", "ALBA____.TTF"), int(30*zoom))
    bigFont = pygame.font.Font(os.path.join("fonts", "alba", "ALBA____.TTF"), int(66*zoom))
  except Exception as e:
    print("Cannot initialize fonts:")
    print(e)
    sys.exit(-1)

  background = pygame.transform.scale(pygame.image.load(os.path.join("sprites", "background.png")).convert(), (int(1024*zoom), int(768*zoom)))

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

def startRandomMusic():
  global music

  stopMusic()

  if music == 1:
    # Randomly choose the Music among .ogg files
    musics = []
    listFiles = os.listdir("musics")
    for fileMusic in listFiles:
      if fileMusic.endswith(".ogg") or fileMusic.endswith(".OGG"):
        musics.append(fileMusic)

    if len(musics) > 0:
      rand = random.randint(0, len(musics)-1)
      try:
        pygame.mixer.music.load(os.path.join("musics", musics[rand]))
        pygame.mixer.music.play()
      except Exception as e:
        print("Music: %s unable to play..." % musics[rand]) 
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
    h.update(str("level" + str(level)).encode())
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
    h.update(str("level" + str(level)).encode())
    h.update(hi[0].encode())
    h.update(hi[1].encode())
    if hi[2] == h.hexdigest():
      if int(hi[1]) > player.bestChrono:
        h = sha1()
        h.update(str(track.name).encode())
        h.update(str("level" + str(level)).encode())
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
      h.update(str("level" + str(level)).encode())
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

  def __init__(self, max_length: int, initial: str = "") -> None:
    self.max_length = max_length
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
    return False

  def render_text(self) -> str:
    """Return display string; appends '_' cursor when field is not full."""
    if len(self.text) < self.max_length:
      return self.text + "_"
    return self.text


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

  h = sha1()
  h.update(str("pyRacerz").encode())
  h.update(str(lck).encode())
  fwrite = open(".pyRacerz.conf", "w+")
  confFile.set("unlockLevel", "key", str(lck) + " " + h.hexdigest())
  confFile.write(fwrite)
  fwrite.close()
