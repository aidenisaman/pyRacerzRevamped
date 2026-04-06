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

import os
import configparser
import zlib

from . import misc

def getImageFromTrackName(name):

  # If it's a bonus (locked) track, act differently
  if name.startswith("bonus"):
    return pygame.image.fromstring(zlib.decompress(open(os.path.join("tracks", name + ".png"), "rb").read()), (1024, 768), "RGBA").convert()

  return pygame.image.load(os.path.join("tracks", name + ".png")).convert()

def getImageFFromTrackName(name):

  # If it's a bonus (locked) track, act differently
  if name.startswith("bonus"):
    return pygame.image.fromstring(zlib.decompress(open(os.path.join("tracks", name + "F.png"), "rb").read()), (1024, 768), "RGBA").convert()

  return pygame.image.load(os.path.join("tracks", name + "F.png")).convert()

class Track:
  '''Class representing a track (with the 2 track pictures)'''

  def __init__(self, name, reverse=0):
    self.track = pygame.transform.scale(getImageFromTrackName(name), (int(1024*misc.zoom), int(768*misc.zoom)))
    self.trackF = pygame.transform.scale(getImageFFromTrackName(name), (int(1024*misc.zoom), int(768*misc.zoom)))
    # Optional nav-only AI surface (e.g. cityF2.png). Keep trackF unchanged.
    bot_nav_path = os.path.join("tracks", name + "F2.png")
    if os.path.exists(bot_nav_path):
      self.trackF_bot_nav = pygame.transform.scale(pygame.image.load(bot_nav_path).convert(), (int(1024*misc.zoom), int(768*misc.zoom)))
    else:
      self.trackF_bot_nav = None
    confFile=configparser.ConfigParser()
    confFile.read_file(open(os.path.join("tracks", name + ".conf"), "r"))

    self.name = name
    self.author = confFile.get("track", "author")
    self.nbCheckpoint = int(confFile.get("track", "nbCheckpoint"))

    # Flag use to race in the opposite way
    self.reverse = reverse

    if self.reverse == 0:
      section = "normal"
    else:
      section = "reverse"

    self.startX1 = int(confFile.get(section, "startX1"))*misc.zoom
    self.startY1 = int(confFile.get(section, "startY1"))*misc.zoom
    self.startX2 = int(confFile.get(section, "startX2"))*misc.zoom
    self.startY2 = int(confFile.get(section, "startY2"))*misc.zoom
    self.startX3 = int(confFile.get(section, "startX3"))*misc.zoom
    self.startY3 = int(confFile.get(section, "startY3"))*misc.zoom

    self.startAngle = float(confFile.get(section, "startAngle"))

def getAvailableTrackNames():
  # Find tracks with browsing and finding the 3 files
  listAvailableTrackNames = []

  listFiles = os.listdir("tracks")
  for fileTrack in listFiles:
    if fileTrack.endswith(".conf"):
      trackName = fileTrack.replace(".conf", "")
      track = 1

      # Test if the user has unlocked the Bonus Level
      try:
        if trackName.startswith("bonus") and misc.getUnlockLevel() < int(trackName.replace("bonus", "")):
          continue
      except Exception as e:
        continue

      for fileTrack2 in listFiles:
        if fileTrack2 == trackName + ".png":
           track = track + 1
        if fileTrack2 == trackName + "F.png":
           track = track + 1
      if track == 3:
        listAvailableTrackNames.append(trackName)
  return listAvailableTrackNames
