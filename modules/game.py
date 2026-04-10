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

import modules.track as track
import modules.menu as menu
import modules.misc as misc

import sys
import os
import datetime

# MINIMAP SETTINGS
MINIMAP_SIZE = 85

# HUD SETTINGS
HUD_X = 8
HUD_Y = 8
HUD_W = 160
HUD_H = 88

_FNT       = None
_FNT_LG    = None
_FNT_TITLE = None
_FNT_BTN   = None
_FNT_INFO  = None

def _init_fonts():
    global _FNT, _FNT_LG, _FNT_TITLE, _FNT_BTN, _FNT_INFO
    if _FNT is not None:
        return
    try:
        _FNT       = pygame.font.SysFont("Arial", 13, bold=True)
        _FNT_LG    = pygame.font.SysFont("Arial", 15, bold=True)
        _FNT_TITLE = pygame.font.SysFont("Arial", 48, bold=True)
        _FNT_BTN   = pygame.font.SysFont("Arial", 26, bold=True)
        _FNT_INFO  = pygame.font.SysFont("Arial", 14, bold=True)
    except Exception:
        _FNT       = pygame.font.Font(None, 16)
        _FNT_LG    = pygame.font.Font(None, 18)
        _FNT_TITLE = pygame.font.Font(None, 48)
        _FNT_BTN   = pygame.font.Font(None, 28)
        _FNT_INFO  = pygame.font.Font(None, 16)


def is_human(play):
    return play.__class__.__name__ == "HumanPlayer"

def is_robot(play):
    return play.__class__.__name__ == "RobotPlayer"

def is_human_or_robot(play):
    return is_human(play) or is_robot(play)


def fmt_time(t):
    if t <= 0 or t >= 999999:
        return "----"
    mins   = t // 6000
    secs   = (t % 6000) // 100
    tenths = (t % 100) // 10
    if mins > 0:
        return f"{mins}:{secs:02d}.{tenths}"
    return f"{secs}.{tenths}s"


def ordinal(n):
    suffixes = {1: "st", 2: "nd", 3: "rd"}
    return str(n) + suffixes.get(n if n < 20 else n % 10, "th")


def draw_rounded_rect(surface, color, rect, radius, width=0):
    x, y, w, h = rect
    r = min(radius, w // 2, h // 2)
    if width == 0:
        pygame.draw.rect(surface, color, (x + r, y,     w - 2*r, h))
        pygame.draw.rect(surface, color, (x,     y + r, w,       h - 2*r))
        for cx, cy in [(x+r, y+r), (x+w-r, y+r), (x+r, y+h-r), (x+w-r, y+h-r)]:
            pygame.draw.circle(surface, color, (cx, cy), r)
    else:
        pygame.draw.rect(surface, color, (x + r,         y,           w - 2*r, width))
        pygame.draw.rect(surface, color, (x + r,         y+h-width,   w - 2*r, width))
        pygame.draw.rect(surface, color, (x,             y + r,       width,   h - 2*r))
        pygame.draw.rect(surface, color, (x + w - width, y + r,       width,   h - 2*r))
        for cx, cy in [(x+r, y+r), (x+w-r, y+r), (x+r, y+h-r), (x+w-r, y+h-r)]:
            pygame.draw.circle(surface, color, (cx, cy), r, width)


def draw_hud(screen, player, masterChrono, maxLapNb, lap_flash_timer):
    bg = pygame.Surface((HUD_W, HUD_H), pygame.SRCALPHA)
    for row in range(HUD_H):
        v = 18 + int(row / HUD_H * 10)
        bg.fill((v, v, v, 210), (0, row, HUD_W, 1))
    screen.blit(bg, (HUD_X, HUD_Y))

    pygame.draw.rect(screen, (230, 0, 0), (HUD_X, HUD_Y, 4, HUD_H))
    pygame.draw.rect(screen, (255, 255, 255), (HUD_X, HUD_Y,         HUD_W, 2))
    pygame.draw.rect(screen, (80,  80,  80),  (HUD_X, HUD_Y+HUD_H-1, HUD_W, 1))

    pad = 12
    lh  = 19
    tx  = HUD_X + pad
    ty  = HUD_Y + 8

    screen.blit(_FNT.render("TIME  " + fmt_time(masterChrono), True, (180, 180, 180)), (tx, ty))
    current_lap = min(player.nbLap + 1, maxLapNb)
    lap_surf = _FNT_LG.render(f"LAP {current_lap}/{maxLapNb}", True, (230, 0, 0))
    screen.blit(lap_surf, (HUD_X + HUD_W - lap_surf.get_width() - 8, ty))
    ty += lh + 1

    pygame.draw.line(screen, (60, 60, 60), (HUD_X + 4, ty), (HUD_X + HUD_W, ty), 1)
    ty += 4

    screen.blit(_FNT.render("LAP   " + fmt_time(player.chrono), True, (255, 255, 255)), (tx, ty))
    ty += lh

    if player.bestChrono < 999999:
        best_col = (180, 80, 255) if lap_flash_timer > 0 else (160, 80, 220)
        best_str = fmt_time(player.bestChrono)
    else:
        best_col = (120, 120, 120)
        best_str = "----"
    screen.blit(_FNT.render("BEST  " + best_str, True, best_col), (tx, ty))
    ty += lh

    speed_val = int(abs(getattr(player.car, 'speed', 0)) * 50)
    if speed_val > 200:
        spd_col = (230, 0, 0)
    elif speed_val > 120:
        spd_col = (255, 165, 0)
    else:
        spd_col = (255, 255, 255)
    screen.blit(_FNT.render(f"SPD   {speed_val} km/h", True, spd_col), (tx, ty))

    if lap_flash_timer > 0:
        alpha = min(180, lap_flash_timer * 7)
        flash = pygame.Surface((HUD_W, HUD_H), pygame.SRCALPHA)
        flash.fill((180, 0, 255, alpha))
        screen.blit(flash, (HUD_X, HUD_Y))


def draw_minimap(screen, currentTrack, listPlayer, minimap_cache, minimap_pos):
    mx, my = minimap_pos

    if minimap_cache[0] is None:
        minimap_cache[0] = pygame.transform.smoothscale(
            currentTrack.track, (MINIMAP_SIZE, MINIMAP_SIZE))

    bg = pygame.Surface((MINIMAP_SIZE, MINIMAP_SIZE), pygame.SRCALPHA)
    bg.fill((10, 10, 10, 200))
    screen.blit(bg, (mx, my))
    screen.blit(minimap_cache[0], (mx, my))

    pygame.draw.rect(screen, (255, 255, 255), (mx, my, MINIMAP_SIZE, MINIMAP_SIZE), 2)
    pygame.draw.rect(screen, (230, 0, 0),     (mx, my, MINIMAP_SIZE, 3))

    tw = currentTrack.track.get_width()
    th = currentTrack.track.get_height()
    dot_colors = [(255, 60, 60), (60, 180, 255), (60, 255, 120), (255, 255, 60)]
    pulse = (pygame.time.get_ticks() // 180) % 4

    for idx, play in enumerate(listPlayer):
        dx  = mx + int(play.car.x / tw * MINIMAP_SIZE)
        dy  = my + int(play.car.y / th * MINIMAP_SIZE)
        col = dot_colors[idx % len(dot_colors)]

        if idx == 0:
            hr = 5 + pulse
            halo = pygame.Surface((hr*2+4, hr*2+4), pygame.SRCALPHA)
            pygame.draw.circle(halo, (255, 255, 255, 90), (hr+2, hr+2), hr)
            screen.blit(halo, (dx - hr - 2, dy - hr - 2))
            pygame.draw.circle(screen, col, (dx, dy), 4)
            pygame.draw.circle(screen, (255, 255, 255), (dx, dy), 4, 1)
        else:
            pygame.draw.circle(screen, col, (dx, dy), 3)


def draw_pause_menu(screen, player, masterChrono, slide_y):
    sw = screen.get_width()
    sh = screen.get_height()

    veil = pygame.Surface((sw, sh), pygame.SRCALPHA)
    veil.fill((0, 0, 0, 160))
    screen.blit(veil, (0, 0))

    box_w, box_h = 380, 310
    bx = (sw - box_w) // 2
    by = (sh - box_h) // 2 + slide_y

    box = pygame.Surface((box_w, box_h))
    for row in range(box_h):
        v = 20 + int(row / box_h * 15)
        pygame.draw.line(box, (v, v, v), (0, row), (box_w, row))
    screen.blit(box, (bx, by))

    pygame.draw.rect(screen, (255, 255, 255), (bx, by,         box_w, box_h), 2)
    pygame.draw.rect(screen, (230, 0,   0),   (bx, by,         box_w, 5))
    pygame.draw.rect(screen, (230, 0,   0),   (bx, by+box_h-5, box_w, 5))

    cx = bx + box_w // 2

    def shadow_blit(fnt, text, col, shadow_col, centre_x, y, offset=2):
        sh_s = fnt.render(text, True, shadow_col)
        tx_s = fnt.render(text, True, col)
        screen.blit(sh_s, (centre_x - sh_s.get_width()//2 + offset, y + offset))
        screen.blit(tx_s, (centre_x - tx_s.get_width()//2, y))

    shadow_blit(_FNT_TITLE, "PAUSED", (255, 255, 255), (80, 0, 0), cx, by + 18)
    pygame.draw.line(screen, (255, 255, 255),
                     (bx + 40, by + 72), (bx + box_w - 40, by + 72), 1)

    stats = [
        ("RACE TIME", fmt_time(masterChrono),  (180, 180, 180)),
        ("LAP  TIME", fmt_time(player.chrono), (255, 255, 255)),
        ("BEST  LAP",
         fmt_time(player.bestChrono) if player.bestChrono < 999999 else "----",
         (180, 80, 255)),
    ]
    sx = by + 78
    for label, val, val_col in stats:
        lbl_s = _FNT_INFO.render(label, True, (110, 110, 110))
        val_s = _FNT_INFO.render(val,   True, val_col)
        screen.blit(lbl_s, (bx + 30, sx))
        screen.blit(val_s, (bx + box_w - 30 - val_s.get_width(), sx))
        sx += 18

    pygame.draw.rect(screen, (50, 50, 50), (bx + 20, sx + 2, box_w - 40, 1))

    buttons = [
        ("R", "RESUME",  (230, 0,   0),   (255, 255, 255)),
        ("T", "RESTART", (230, 0,   0),   (255, 255, 255)),
        ("Q", "QUIT",    (180, 180, 180), (100, 100, 100)),
    ]
    btn_w, btn_h, btn_gap = 280, 44, 8
    btn_x = bx + (box_w - btn_w) // 2
    sy    = sx + 10

    for key, label, key_col, lbl_col in buttons:
        btn_surf = pygame.Surface((btn_w, btn_h))
        for row in range(btn_h):
            v = 35 + int(row / btn_h * 20)
            pygame.draw.line(btn_surf, (v, v, v), (0, row), (btn_w, row))
        screen.blit(btn_surf, (btn_x, sy))
        pygame.draw.rect(screen, (80, 80, 80), (btn_x, sy, btn_w, btn_h), 1)
        pygame.draw.rect(screen, key_col, (btn_x, sy, 4, btn_h))
        key_surf = _FNT_BTN.render(key, True, key_col)
        screen.blit(key_surf, (btn_x + 14, sy + (btn_h - key_surf.get_height())//2))
        pygame.draw.line(screen, (60, 60, 60),
                         (btn_x + 38, sy + 6), (btn_x + 38, sy + btn_h - 6), 1)
        lbl_surf = _FNT_BTN.render(label, True, lbl_col)
        screen.blit(lbl_surf, (btn_x + 50, sy + (btn_h - lbl_surf.get_height())//2))
        sy += btn_h + btn_gap


class Game:
    '''Class representing a game: Tournament or Single Race'''

    def __init__(self, gameType, listTrackName=None, listPlayer=None, maxLapNb=-1):
        self.gameType      = gameType
        self.listTrackName = listTrackName
        self.listPlayer    = listPlayer
        self.maxLapNb      = maxLapNb

    def play(self):
        if (self.gameType is None or self.listTrackName is None
                or self.listPlayer is None or self.maxLapNb == -1):
            print("Incomplete game")
            return

        restart = True
        while restart:
            restart = False
            self._run_race()

    def _run_race(self):
        _init_fonts()

        # Load sound effects
        try:
            _snd_collision = pygame.mixer.Sound(os.path.join("sounds", "collision.mp3"))
            _snd_drift     = pygame.mixer.Sound(os.path.join("sounds", "drift.mp3"))
            _snd_collision.set_volume(0.6)
            _snd_drift.set_volume(0.5)
        except Exception:
            _snd_collision = None
            _snd_drift     = None

        _drift_playing = False

        for currentTrackName in self.listTrackName:
            try:
                currentTrack = track.Track(currentTrackName[0], currentTrackName[1])
            except Exception as e:
                print("Cannot load track :", e)
                sys.exit(1)

            misc.startRandomMusic()

            minimap_pos = (misc.screen.get_width() - MINIMAP_SIZE - 6, 6)

            if currentTrackName == self.listTrackName[0]:
                listRank = []
                for play in self.listPlayer:
                    rank = -1
                    while rank in listRank or rank == -1:
                        rank = random.randint(1, len(self.listPlayer))
                    listRank.append(rank)
                    play.play(currentTrack, rank)
            else:
                for play in self.listPlayer:
                    play.play(currentTrack, len(self.listPlayer) - play.rank + 1)

            clock = pygame.time.Clock()

            for i in range(4):
                misc.screen.blit(currentTrack.track, (0, 0))
                for play in self.listPlayer:
                    text = misc.popUpFont.render(play.name, 1, misc.lightColor, (0, 0, 0))
                    tr = text.get_rect()
                    tr.centerx = play.car.x
                    tr.centery = play.car.y
                    misc.screen.blit(text, tr)
                pygame.display.flip()
                pygame.time.delay(400)

                misc.screen.blit(currentTrack.track, (0, 0))
                for play in self.listPlayer:
                    play.car.image = play.car.cars[int((256.0*play.car.angle/2.0/math.pi)%256)]
                    play.car.sprite.draw(misc.screen)
                pygame.display.flip()
                pygame.time.delay(400)

            i   = 0
            l   = []

            popUp           = misc.PopUp(currentTrack)
            raceFinish      = 0
            masterChrono    = 0
            paused          = False
            slide_y         = 60
            lap_flash_timer = 0
            minimap_cache   = [None]
            _drift_playing  = False

            for play in self.listPlayer:
                play.bestChrono = 999999
                play.chrono     = 0
                play.nbLap      = 0
                play.raceFinish = 0

            replayArray = array.array("h")

            bestRank = [None]
            for r in range(1, self.maxLapNb + 1):
                bestRank.append(1)

            imgFireG = pygame.transform.rotozoom(
                pygame.image.load(os.path.join("sprites", "grey.png")).convert_alpha(),
                0, misc.zoom)
            misc.screen.blit(imgFireG, (10*misc.zoom, 10*misc.zoom))
            misc.screen.blit(imgFireG, (90*misc.zoom, 10*misc.zoom))
            misc.screen.blit(imgFireG, (170*misc.zoom, 10*misc.zoom))
            pygame.display.flip()
            pygame.time.delay(1000)

            imgFire = pygame.transform.rotozoom(
                pygame.image.load(os.path.join("sprites", "red.png")).convert_alpha(),
                0, misc.zoom)
            misc.screen.blit(imgFire, (10*misc.zoom,  10*misc.zoom))
            pygame.display.flip()
            pygame.time.delay(1000)
            misc.screen.blit(imgFire, (90*misc.zoom,  10*misc.zoom))
            pygame.display.flip()
            pygame.time.delay(1000)
            misc.screen.blit(imgFire, (170*misc.zoom, 10*misc.zoom))
            pygame.display.flip()
            pygame.time.delay(990)

            pygame.event.clear()
            misc.screen.blit(currentTrack.track, (0, 0))
            pygame.display.flip()

            sec     = datetime.datetime.now().second
            nbFrame = 0

            while raceFinish == 0:

                for event in pygame.event.get():
                    if event.type == QUIT:
                        misc.stopMusic()
                        sys.exit(0)

                    elif event.type == KEYDOWN:
                        if event.key == K_ESCAPE:
                            misc.stopMusic()
                            if _snd_drift and _drift_playing:
                                _snd_drift.stop()
                            return

                        if event.key == K_p:
                            paused  = not paused
                            slide_y = 60

                        if paused:
                            if event.key == K_r:
                                paused = False
                                misc.screen.blit(currentTrack.track, (0, 0))
                                pygame.display.flip()
                            elif event.key == K_t:
                                misc.stopMusic()
                                if _snd_drift and _drift_playing:
                                    _snd_drift.stop()
                                self._restart_requested = True
                                return
                            elif event.key == K_q:
                                misc.stopMusic()
                                if _snd_drift and _drift_playing:
                                    _snd_drift.stop()
                                return
                        else:
                            for play in self.listPlayer:
                                if is_human(play):
                                    if event.key == play.keyAccel:  play.keyAccelPressed = 1
                                    if event.key == play.keyBrake:  play.keyBrakePressed = 1
                                    if event.key == play.keyLeft:   play.keyLeftPressed  = 1
                                    if event.key == play.keyRight:  play.keyRightPressed = 1

                    elif event.type == KEYUP:
                        for play in self.listPlayer:
                            if is_human(play):
                                if event.key == play.keyAccel:  play.keyAccelPressed = 0
                                if event.key == play.keyBrake:  play.keyBrakePressed = 0
                                if event.key == play.keyLeft:   play.keyLeftPressed  = 0
                                if event.key == play.keyRight:  play.keyRightPressed = 0

                if paused:
                    if slide_y > 0:
                        slide_y = max(0, slide_y - 6)
                    misc.screen.blit(currentTrack.track, (0, 0))
                    for play in self.listPlayer:
                        play.car.sprite.draw(misc.screen)
                    draw_hud(misc.screen, self.listPlayer[0], masterChrono,
                             self.maxLapNb, lap_flash_timer)
                    draw_minimap(misc.screen, currentTrack, self.listPlayer,
                                 minimap_cache, minimap_pos)
                    draw_pause_menu(misc.screen, self.listPlayer[0], masterChrono, slide_y)
                    pygame.display.flip()
                    clock.tick(60)
                    continue

                for play in self.listPlayer:
                    if is_robot(play):
                        play.compute()
                    if is_human_or_robot(play):
                        if play.keyAccelPressed: play.car.doAccel()
                        else:                    play.car.noAccel()
                        if play.keyBrakePressed: play.car.doBrake()
                        else:                    play.car.noBrake()
                        if play.keyLeftPressed:  play.car.doLeft()
                        if play.keyRightPressed: play.car.doRight()
                        if not play.keyLeftPressed and not play.keyRightPressed:
                            play.car.noWheel()

                for play in self.listPlayer:
                    oldRect = play.car.rect
                    l.append(oldRect.__copy__())
                    misc.screen.blit(currentTrack.track, play.car.rect, play.car.rect)

                for play in self.listPlayer:
                    play.car.update()
                    play.chrono += 1

                    color = currentTrack.trackF.get_at((int(play.car.x), int(play.car.y)))
                    r = color[0]

                    if currentTrack.reverse == 0 and play.raceFinish == 0:
                        if r == play.lastCheckpoint + 16:
                            play.lastCheckpoint = r
                        elif r == 16:
                            if play.lastCheckpoint == 16 * currentTrack.nbCheckpoint:
                                play.lastCheckpoint = r
                                play.nbLap += 1
                                play.rank   = bestRank[play.nbLap]
                                bestRank[play.nbLap] += 1
                                if play.chrono < play.bestChrono:
                                    play.bestChrono  = play.chrono
                                    lap_flash_timer  = 25
                                    popUp.addElement(play.car, play.name + " L" + str(play.nbLap) + " P" + str(play.rank) + " " + misc.chrono2Str(play.chrono) + "B")
                                else:
                                    popUp.addElement(play.car, play.name + " L" + str(play.nbLap) + " P" + str(play.rank) + " " + misc.chrono2Str(play.chrono))
                                play.chrono = 0
                            elif play.lastCheckpoint > 16:
                                play.lastCheckpoint = r
                                popUp.addElement(play.car, play.name + " L" + str(play.nbLap+1) + " MISSED")
                                play.chrono = 0

                    elif currentTrack.reverse == 1 and play.raceFinish == 0:
                        if r != 0 and r == play.lastCheckpoint - 16:
                            play.lastCheckpoint = r
                        elif r == 16 * currentTrack.nbCheckpoint:
                            if play.lastCheckpoint == 16:
                                play.lastCheckpoint = r
                                play.nbLap += 1
                                play.rank   = bestRank[play.nbLap]
                                bestRank[play.nbLap] += 1
                                if play.chrono < play.bestChrono:
                                    play.bestChrono  = play.chrono
                                    lap_flash_timer  = 25
                                    popUp.addElement(play.car, play.name + " L" + str(play.nbLap) + " P" + str(play.rank) + " " + misc.chrono2Str(play.chrono) + "B")
                                else:
                                    popUp.addElement(play.car, play.name + " L" + str(play.nbLap) + " P" + str(play.rank) + " " + misc.chrono2Str(play.chrono))
                                play.chrono = 0
                            elif play.lastCheckpoint < 16 * currentTrack.nbCheckpoint:
                                play.lastCheckpoint = r
                                popUp.addElement(play.car, play.name + " L" + str(play.nbLap+1) + " MISSED")
                                play.chrono = 0

                for play in self.listPlayer:
                    for play2 in self.listPlayer:
                        if play == play2:
                            continue
                        pCR  = []
                        p2CR = []
                        for slot in range(4):
                            listIndex = pygame.Rect(play.car.listCarRect[slot]).collidelistall(play2.car.listCarRect)
                            if listIndex:
                                if slot not in pCR:
                                    pCR.append(slot)
                                for idx in listIndex:
                                    if idx not in p2CR:
                                        p2CR.append(idx)
                        pCR.sort()
                        if pCR == [0]:
                            play.car.newSpeed = play.car.speed/2 - abs(play2.car.speed/2)
                        elif pCR == [1]:
                            play.car.newSpeed = play.car.speed/2 + abs(play2.car.speed/2)
                        elif pCR in ([2],[0,1,2],[0,2],[1,2]):
                            play.car.speedL   += abs(play2.car.speed/2)*10
                            play.car.newSpeed  = 0
                        elif pCR in ([3],[0,1,3],[0,3],[1,3]):
                            play.car.speedL   -= abs(play2.car.speed/2)*10
                            play.car.newSpeed  = 0
                        elif pCR:
                            play.car.newSpeed = 0

                # Play collision sound when cars hit each other
                for play in self.listPlayer:
                    if play.car.newSpeed != 0:
                        play.car.speed    = play.car.newSpeed
                        play.car.newSpeed = 0
                        if _snd_collision:
                            _snd_collision.play()

                popUp.display()
                l.append(popUp.rect.__copy__())

                raceFinish = 1

                currentTrack.track.lock()

                for play in self.listPlayer:
                    if play.car.brake == 0:
                        play.car.image = play.car.cars[int((256.0*play.car.angle/2.0/math.pi)%256)].copy()
                    else:
                        play.car.image = play.car.cars2[int((256.0*play.car.angle/2.0/math.pi)%256)].copy()

                    part = pygame.Surface((play.car.sizeRect, play.car.sizeRect), HWSURFACE, 24).convert()
                    part.blit(currentTrack.trackF, (0, 0),
                              (play.car.x - play.car.sizeRect/2,
                               play.car.y - play.car.sizeRect/2,
                               play.car.sizeRect, play.car.sizeRect))
                    partArray = pygame.surfarray.array2d(part)
                    aX = 0
                    for arrayX in partArray:
                        aY = 0
                        for col in arrayX:
                            if col % 256 != 0:
                                play.car.image.set_at((aX, aY), (255, 255, 255, 0))
                            aY += 1
                        aX += 1

                    if play.car.slide in (1, 2):
                        coordN    = (play.car.x - math.cos(play.car.angle)*play.car.height*0.4,
                                     play.car.y - math.sin(play.car.angle)*play.car.height*0.4)
                        coordS    = (play.car.x + math.cos(play.car.angle)*play.car.height*0.4,
                                     play.car.y + math.sin(play.car.angle)*play.car.height*0.4)
                        coord0    = (int(coordN[0]-math.sin(play.car.angle)*play.car.width*0.3),
                                     int(coordN[1]+math.cos(play.car.angle)*play.car.width*0.3))
                        coord1    = (int(coordN[0]+math.sin(play.car.angle)*play.car.width*0.3),
                                     int(coordN[1]-math.cos(play.car.angle)*play.car.width*0.3))
                        coord2    = (int(coordS[0]-math.sin(play.car.angle)*play.car.width*0.3),
                                     int(coordS[1]+math.cos(play.car.angle)*play.car.width*0.3))
                        coord3    = (int(coordS[0]+math.sin(play.car.angle)*play.car.width*0.3),
                                     int(coordS[1]-math.cos(play.car.angle)*play.car.width*0.3))
                        oldCoordN = (play.car.ox - math.cos(play.car.oldAngle)*play.car.height*0.4,
                                     play.car.oy - math.sin(play.car.oldAngle)*play.car.height*0.4)
                        oldCoordS = (play.car.ox + math.cos(play.car.oldAngle)*play.car.height*0.4,
                                     play.car.oy + math.sin(play.car.oldAngle)*play.car.height*0.4)
                        oldCoord0 = (int(oldCoordN[0]-math.sin(play.car.oldAngle)*play.car.width*0.3),
                                     int(oldCoordN[1]+math.cos(play.car.oldAngle)*play.car.width*0.3))
                        oldCoord1 = (int(oldCoordN[0]+math.sin(play.car.oldAngle)*play.car.width*0.3),
                                     int(oldCoordN[1]-math.cos(play.car.oldAngle)*play.car.width*0.3))
                        oldCoord2 = (int(oldCoordS[0]-math.sin(play.car.oldAngle)*play.car.width*0.3),
                                     int(oldCoordS[1]+math.cos(play.car.oldAngle)*play.car.width*0.3))
                        oldCoord3 = (int(oldCoordS[0]+math.sin(play.car.oldAngle)*play.car.width*0.3),
                                     int(oldCoordS[1]-math.cos(play.car.oldAngle)*play.car.width*0.3))

                        if currentTrack.trackF.get_at(coord2)[2] != 255 and currentTrack.trackF.get_at(oldCoord2)[2] != 255:
                            pygame.draw.line(currentTrack.track, (0,0,0), coord2, oldCoord2)
                        if currentTrack.trackF.get_at(coord3)[2] != 255 and currentTrack.trackF.get_at(oldCoord3)[2] != 255:
                            pygame.draw.line(currentTrack.track, (0,0,0), coord3, oldCoord3)
                        if play.car.slide == 2:
                            if currentTrack.trackF.get_at(coord0)[2] != 255 and currentTrack.trackF.get_at(oldCoord0)[2] != 255:
                                pygame.draw.line(currentTrack.track, (0,0,0), coord0, oldCoord0)
                            if currentTrack.trackF.get_at(coord1)[2] != 255 and currentTrack.trackF.get_at(oldCoord1)[2] != 255:
                                pygame.draw.line(currentTrack.track, (0,0,0), coord1, oldCoord1)

                    if play.nbLap == self.maxLapNb and play.raceFinish != 1:
                        play.raceFinish = 1
                        play.car.blink  = 1

                    if play.nbLap != self.maxLapNb:
                        raceFinish = 0

                    if play.car.blink == 0:
                        l.append(play.car.rect.__copy__())
                        play.car.sprite.draw(misc.screen)

                    if play.car.blink == 1 and play.car.blinkCount < 10:
                        play.car.blinkCount += 1
                        l.append(play.car.rect.__copy__())
                        play.car.sprite.draw(misc.screen)
                    elif play.car.blink == 1 and play.car.blinkCount >= 10:
                        play.car.blinkCount += 1

                    if play.car.blink == 1 and play.car.blinkCount == 20:
                        play.car.blinkCount = 0

                currentTrack.track.unlock()

                if lap_flash_timer > 0:
                    lap_flash_timer -= 1

                draw_hud(misc.screen, self.listPlayer[0], masterChrono,
                         self.maxLapNb, lap_flash_timer)
                draw_minimap(misc.screen, currentTrack, self.listPlayer,
                             minimap_cache, minimap_pos)

                # Play drift sound when player car is drifting
                if _snd_drift:
                    if self.listPlayer[0].car.drifting and not _drift_playing:
                        _snd_drift.play(-1)
                        _drift_playing = True
                    elif not self.listPlayer[0].car.drifting and _drift_playing:
                        _snd_drift.stop()
                        _drift_playing = False

                if i == 1:
                    sec2 = datetime.datetime.now().second
                    if sec2 > sec or (sec == 59 and sec2 > 0):
                        fps     = nbFrame
                        nbFrame = 1
                        sec     = sec2
                        text    = misc.popUpFont.render(str(fps), 1, misc.lightColor, (0, 0, 0))
                        tRect   = text.get_rect()
                        tRect.x = 0
                        tRect.y = 0
                        misc.screen.blit(text, tRect)
                        l.append(tRect.__copy__())
                    else:
                        nbFrame += 1
                    pygame.display.flip()
                    i = 0
                    l = []
                else:
                    i += 1

                masterChrono += 1

                for play in self.listPlayer:
                    replayArray.append(int(play.car.x / misc.zoom))
                    replayArray.append(int(play.car.y / misc.zoom))
                    replayArray.append(int(play.car.angle * 1000))
                    val = play.car.blink * 100
                    if play.car.brake > 0:
                        val += 10
                    val += play.car.slide
                    replayArray.append(val)
                    if is_human_or_robot(play):
                        val = (play.keyAccelPressed*1000 + play.keyBrakePressed*100
                               + play.keyLeftPressed*10  + play.keyRightPressed)
                        replayArray.append(val)
                    else:
                        replayArray.append(0)

                clock.tick(100)

            # Race finished — stop drift sound if still playing
            if _snd_drift and _drift_playing:
                _snd_drift.stop()
                _drift_playing = False

            popUp.display()
            l.append(popUp.rect.__copy__())

            text = pygame.transform.rotozoom(
                misc.bigFont.render("Race finish, press a key to continue", 1, misc.lightColor),
                20, 1)
            textRect = text.get_rect()
            textRect.centerx = misc.screen.get_rect().centerx
            textRect.centery = misc.screen.get_rect().centery
            misc.screen.blit(text, textRect)
            pygame.display.flip()
            misc.wait4Key()

            menu1   = menu.SimpleMenu(misc.titleFont, "save Replay?", 20*misc.zoom, misc.itemFont, ["No", "Yes"])
            select1 = menu1.getInput()

            if select1 == 2:
                menu2    = menu.ChooseTextMenu(misc.titleFont, "enter a Replay Name:", 20*misc.zoom, misc.itemFont, 8)
                select2  = menu2.getInput()
                waitMenu = menu.SimpleTitleOnlyMenu(misc.titleFont, "recording Replay...")

                if select2 not in (None, ""):
                    f = open(os.path.join("replays", select2 + ".rep"), "wb")
                    header = (str(misc.VERSION) + " " + currentTrack.name + " "
                            + str(currentTrack.reverse) + " " + str(masterChrono)
                            + " " + str(len(self.listPlayer)) + " ")
                    for play in self.listPlayer:
                        header += play.name + " " + str(play.car.color) + " " + str(play.car.level) + " "
                    header += "\n"
                    f.write(header.encode())
                    f.write(zlib.compress(replayArray.tobytes()))
                    f.close()

            self.computeScores(currentTrack)
            misc.stopMusic()

        if self.gameType == "tournament":
            self.displayFinalScores()

        if self.gameType == "challenge":
            return self.listPlayer[0].bestChrono

    def computeScores(self, track):

        titleMenu = menu.SimpleTitleOnlyMenu(misc.titleFont, "raceResult")
        y = titleMenu.startY

        for play in self.listPlayer:
            if self.gameType == "tournament":
                morePoint = {1:10, 2:6, 3:4, 4:3, 5:2, 6:1}.get(play.rank, 0)

            bestChrono = 1
            for play2 in self.listPlayer:
                if play.bestChrono > play2.bestChrono:
                    bestChrono = 0
                    break

            playCar = pygame.transform.rotozoom(
                pygame.image.load(os.path.join("sprites", "cars",
                                               "car" + str(play.car.color) + ".png")).convert_alpha(),
                270, 1.2*misc.zoom)

            if self.gameType == "tournament":
                if bestChrono == 1:
                    suffix = " HiScore !" if misc.addHiScore(track, play) == 1 else ""
                    text = misc.titleFont.render(
                        str(play.rank) + "' " + play.name + " :  " + str(play.point)
                        + " + " + str(morePoint) + " + 2 = " + str(play.point+morePoint+2)
                        + "  >> " + misc.chrono2Str(play.bestChrono) + " <<" + suffix,
                        1, misc.lightColor)
                    play.point += morePoint + 2
                else:
                    text = misc.titleFont.render(
                        str(play.rank) + "' " + play.name + " :  " + str(play.point)
                        + " + " + str(morePoint) + " = " + str(play.point+morePoint)
                        + "     " + misc.chrono2Str(play.bestChrono),
                        1, misc.darkColor)
                    play.point += morePoint
            else:
                if bestChrono == 1:
                    suffix = " HiScore !" if misc.addHiScore(track, play) == 1 else ""
                    text = misc.titleFont.render(
                        str(play.rank) + "' " + play.name + " : >> "
                        + misc.chrono2Str(play.bestChrono) + " <<" + suffix,
                        1, misc.lightColor)
                else:
                    text = misc.titleFont.render(
                        str(play.rank) + "' " + play.name + " :    "
                        + misc.chrono2Str(play.bestChrono),
                        1, misc.darkColor)

            playCarRect = playCar.get_rect()
            textRect    = text.get_rect()
            textRect.centerx    = misc.screen.get_rect().centerx + (playCarRect.width + 20*misc.zoom) / 2
            textRect.y          = y + 80*misc.zoom*play.rank
            playCarRect.x       = textRect.x - (playCarRect.width + 20*misc.zoom)
            playCarRect.centery = textRect.centery
            misc.screen.blit(playCar, playCarRect)
            misc.screen.blit(text, textRect)

        pygame.display.flip()
        misc.wait4Key()

    def displayFinalScores(self):

        titleMenu = menu.SimpleTitleOnlyMenu(misc.titleFont, "finalResult")
        y = titleMenu.startY

        for play in self.listPlayer:
            self.rank = 1
            for play2 in self.listPlayer:
                if play.point < play2.point:
                    self.rank += 1

            playCar = pygame.transform.rotozoom(
                pygame.image.load(os.path.join("sprites", "cars",
                                               "car" + str(play.car.color) + ".png")).convert_alpha(),
                270, 1.2*misc.zoom)

            if self.rank == 1:
                text = misc.titleFont.render(
                    str(play.rank) + "' " + play.name + " :  >> " + str(play.point) + " <<",
                    1, misc.lightColor)
            else:
                text = misc.titleFont.render(
                    str(play.rank) + "' " + play.name + " : " + str(play.point),
                    1, misc.darkColor)

            playCarRect = playCar.get_rect()
            textRect    = text.get_rect()
            textRect.centerx    = misc.screen.get_rect().centerx + (playCarRect.width + 20*misc.zoom) / 2
            textRect.y          = y + 80*misc.zoom*play.rank
            playCarRect.x       = textRect.x - (playCarRect.width + 20*misc.zoom)
            playCarRect.centery = textRect.centery
            misc.screen.blit(playCar, playCarRect)
            misc.screen.blit(text, textRect)

        pygame.display.flip()
        misc.wait4Key()
