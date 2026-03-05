"""Network race module for pyRacerz.

NetworkHostRace   -- host plays a local race; broadcasts car state (pid=0)
                     each frame to all clients via a NetworkServer.
                     Also relays incoming client state (pid>0) back out so
                     all clients can render each other (phase 2 ready).
NetworkWatchRace  -- spectator receives live state packets keyed by pid and
                     renders each car; participates in chat via a NetworkClient.
NetworkClientRace -- (phase 2 skeleton) client races locally and exchanges
                     state bidirectionally with the host.
"""

import math
import os
import sys

import pygame
from pygame.locals import *
import pygame.surfarray

from . import misc
from . import track as track_mod
from . import player as player_mod

# ---------------------------------------------------------------------------
# Chat overlay constants
# ---------------------------------------------------------------------------
_CHAT_MAX_LINES  = 8          # most recent lines visible on screen
_CHAT_LINE_H     = 24         # pixels per line (at zoom == 1 baseline)
_CHAT_START_FRAC = 0.68       # fraction of screen height where log starts


def _chat_y():
  return int(misc.screen.get_height() * _CHAT_START_FRAC)


def _draw_chat_overlay(chat_log, input_line=None):
  """Blit the chat log (and optional live input line) onto misc.screen."""
  y = _chat_y()
  for line in chat_log[-_CHAT_MAX_LINES:]:
    surf = misc.popUpFont.render(line[:64], 1, misc.lightColor, (0, 0, 0))
    misc.screen.blit(surf, (4, y))
    y += _CHAT_LINE_H
  if input_line is not None:
    surf = misc.popUpFont.render(("> " + input_line)[:66], 1, (255, 255, 180), (0, 0, 0))
    misc.screen.blit(surf, (4, y))


# ===========================================================================
class NetworkHostRace:
  """Run a single-player race locally and broadcast every car-state frame.

  Parameters
  ----------
  server        : NetworkServer  (already started)
  human_player  : HumanPlayer    (not yet play()'d on the track)
  current_track : Track
  laps          : int
  """

  def __init__(self, server, human_player, current_track, laps=3):
    self.server       = server
    self._play        = human_player
    self.currentTrack = current_track
    self.laps         = laps

  # ------------------------------------------------------------------
  def run(self):
    play         = self._play
    ct           = self.currentTrack

    play.play(ct, 1)

    clock    = pygame.time.Clock()
    chat_log = []
    l        = []   # dirty rects
    i        = 0
    popUp    = misc.PopUp(ct)

    # ── car name blink (same as single race) ────────────────────────
    for _ in range(4):
      misc.screen.blit(ct.track, (0, 0))
      play.car.image = play.car.cars[int((256.0 * play.car.angle / 2.0 / math.pi) % 256)]
      play.car.sprite.draw(misc.screen)
      name_surf = misc.popUpFont.render(play.name, 1, misc.lightColor, (0, 0, 0))
      nr = name_surf.get_rect()
      nr.centerx = int(play.car.x)
      nr.centery  = int(play.car.y)
      misc.screen.blit(name_surf, nr)
      pygame.display.flip()
      pygame.time.delay(400)

    # ── traffic lights ───────────────────────────────────────────────
    img_grey = pygame.transform.rotozoom(
      pygame.image.load(os.path.join("sprites", "grey.png")).convert_alpha(), 0, misc.zoom)
    img_red  = pygame.transform.rotozoom(
      pygame.image.load(os.path.join("sprites", "red.png")).convert_alpha(),  0, misc.zoom)

    misc.screen.blit(ct.track, (0, 0))
    misc.screen.blit(img_grey, (int(10  * misc.zoom), int(10 * misc.zoom)))
    misc.screen.blit(img_grey, (int(90  * misc.zoom), int(10 * misc.zoom)))
    misc.screen.blit(img_grey, (int(170 * misc.zoom), int(10 * misc.zoom)))
    pygame.display.flip()
    pygame.time.delay(1000)
    for k in range(3):
      misc.screen.blit(ct.track, (0, 0))
      for j in range(k + 1):
        misc.screen.blit(img_red, (int((10 + 80 * j) * misc.zoom), int(10 * misc.zoom)))
      pygame.display.flip()
      pygame.time.delay(1000)

    pygame.event.clear()
    misc.screen.blit(ct.track, (0, 0))
    pygame.display.flip()

    # ── main race loop ───────────────────────────────────────────────
    while play.nbLap < self.laps:

      # Events
      for event in pygame.event.get():
        if event.type == QUIT:
          self.server.broadcast({"type": "finish"})
          misc.stopMusic()
          sys.exit(0)
        elif event.type == KEYDOWN:
          if event.key == K_ESCAPE:
            self.server.broadcast({"type": "finish"})
            return
          play.handle_keydown(event.key)
        elif event.type == KEYUP:
          play.handle_keyup(event.key)

      play.update_controls()

      # Clear old position
      l.append(play.car.rect.__copy__())
      misc.screen.blit(ct.track, play.car.rect, play.car.rect)

      # Physics
      play.car.update()
      play.chrono += 1

      # Checkpoint / lap tracking
      color = ct.trackF.get_at((int(play.car.x), int(play.car.y)))
      r = color[0]

      if ct.reverse == 0 and play.raceFinish == 0:
        if r == play.lastCheckpoint + 16:
          play.lastCheckpoint = r
        elif r == 16:
          if play.lastCheckpoint == 16 * ct.nbCheckpoint:
            play.lastCheckpoint = r
            play.nbLap += 1
            tag = "B" if play.chrono < play.bestChrono else ""
            if play.chrono < play.bestChrono:
              play.bestChrono = play.chrono
            popUp.addElement(play.car,
              play.name + " L" + str(play.nbLap) + " P1 " + misc.chrono2Str(play.chrono) + tag)
            play.chrono = 0
          elif play.lastCheckpoint > 16:
            play.lastCheckpoint = r
            popUp.addElement(play.car, play.name + " L" + str(play.nbLap + 1) + " MISSED")
            play.chrono = 0

      elif ct.reverse == 1 and play.raceFinish == 0:
        if r != 0 and r == play.lastCheckpoint - 16:
          play.lastCheckpoint = r
        elif r == 16 * ct.nbCheckpoint:
          if play.lastCheckpoint == 16:
            play.lastCheckpoint = r
            play.nbLap += 1
            tag = "B" if play.chrono < play.bestChrono else ""
            if play.chrono < play.bestChrono:
              play.bestChrono = play.chrono
            popUp.addElement(play.car,
              play.name + " L" + str(play.nbLap) + " P1 " + misc.chrono2Str(play.chrono) + tag)
            play.chrono = 0
          elif play.lastCheckpoint < 16 * ct.nbCheckpoint:
            play.lastCheckpoint = r
            popUp.addElement(play.car, play.name + " L" + str(play.nbLap + 1) + " MISSED")
            play.chrono = 0

      # Broadcast host state (pid 0)
      self.server.broadcast({
        "type": "state",
        "pid":  0,
        "x":  int(play.car.x / misc.zoom),
        "y":  int(play.car.y / misc.zoom),
        "a":  int(play.car.angle * 1000),
        "br": 1 if play.car.brake > 0 else 0,
        "sl": play.car.slide,
        "bl": play.car.blink,
      })

      # Receive messages from clients
      for msg in self.server.recv_all():
        mtype = msg.get("type")
        if mtype == "chat":
          self.server.broadcast(msg)
          chat_log.append(msg.get("sender", "?") + ": " + msg.get("text", ""))
        elif mtype == "state":
          # Phase 2: client sent their own car state — relay to all other clients
          # so every spectator/racer can render it.  In phase 1 no clients send
          # state so this branch is simply never reached.
          self.server.broadcast(msg)

      # Draw car sprite
      ct.track.lock()
      if play.car.brake == 0:
        play.car.image = play.car.cars[int((256.0 * play.car.angle / 2.0 / math.pi) % 256)].copy()
      else:
        play.car.image = play.car.cars2[int((256.0 * play.car.angle / 2.0 / math.pi) % 256)].copy()

      # Tunnel mask
      if not ct.name.startswith("desert") or play.lastCheckpoint != 80:
        part = pygame.Surface((play.car.sizeRect, play.car.sizeRect), HWSURFACE, 24).convert()
        part.blit(ct.trackF, (0, 0),
          (play.car.x - play.car.sizeRect / 2,
           play.car.y - play.car.sizeRect / 2,
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

      newRect = play.car.rect
      l.append(newRect.__copy__())
      play.car.sprite.draw(misc.screen)
      ct.track.unlock()

      # PopUp + chat overlay
      popUp.display()
      l.append(popUp.rect.__copy__())
      _draw_chat_overlay(chat_log)

      if i == 1:
        pygame.display.update(l)
        i = 0
        l = []
      else:
        i += 1

      clock.tick(100)

    # Race finished
    self.server.broadcast({"type": "finish"})

    finish_surf = pygame.transform.rotozoom(
      misc.bigFont.render("Race finish!", 1, misc.lightColor), 0, 1)
    fr = finish_surf.get_rect()
    fr.center = misc.screen.get_rect().center
    misc.screen.blit(finish_surf, fr)
    pygame.display.flip()
    misc.wait4Key()


# ===========================================================================
class NetworkWatchRace:
  """Spectator screen: renders all cars by pid plus lobby chat.

  In phase 1 only the host car (pid=0) sends state, so only one car
  is visible.  When phase 2 clients start sending state packets the
  additional cars will appear automatically via ``_remote_cars``.

  Parameters
  ----------
  client             : NetworkClient  (already connected)
  spectator_name     : str            (this player's name, used as chat sender)
  host_name          : str
  host_color         : int
  host_level         : int
  track_name         : str
  track_reverse      : int
  laps               : int
  remote_player_infos: list of {pid, name, color, level} dicts (phase 2)
  """

  def __init__(self, client, spectator_name,
               host_name, host_color, host_level,
               track_name, track_reverse, laps=3,
               remote_player_infos=None):
    self.client              = client
    self.spectator_name      = spectator_name
    self.host_name           = host_name
    self.host_color          = host_color
    self.host_level          = host_level
    self.track_name          = track_name
    self.track_reverse       = track_reverse
    self.laps                = laps
    # pid → ReplayPlayer; pid=0 is host, populated below.
    # Phase 2: pre-populate from remote_player_infos for client cars.
    self._remote_player_infos = remote_player_infos or []

  # ------------------------------------------------------------------
  def run(self):
    ct          = track_mod.Track(self.track_name, self.track_reverse)
    host_player = player_mod.ReplayPlayer(self.host_name, self.host_color, self.host_level)
    host_player.play(ct)

    # pid → ReplayPlayer mapping; pid=0 is always the host.
    # Phase 2: additional entries are created on first state packet from that pid.
    remote_cars = {0: host_player}
    for info in self._remote_player_infos:
      rp = player_mod.ReplayPlayer(info["name"], info["color"], info["level"])
      rp.play(ct)
      remote_cars[info["pid"]] = rp
    clock      = pygame.time.Clock()
    chat_log   = []
    chat_input = misc.TextInput(50, allow_space=True)
    is_typing  = False

    misc.screen.blit(ct.track, (0, 0))
    hint_surf = misc.popUpFont.render("[T] Chat   [ESC] Leave", 1, misc.darkColor, (0, 0, 0))
    misc.screen.blit(hint_surf, (misc.screen.get_width() - hint_surf.get_width() - 4, 4))
    pygame.display.flip()

    l       = []
    i       = 0
    running = True

    while running:

      # Events
      for event in pygame.event.get():
        if event.type == QUIT:
          self.client.send({"type": "bye"})
          self.client.disconnect()
          sys.exit(0)
        elif event.type == KEYDOWN:
          if is_typing:
            if event.key == K_RETURN:
              text = chat_input.text.strip()
              if text:
                self.client.send({"type": "chat",
                                  "sender": self.spectator_name,
                                  "text": text})
              chat_input = misc.TextInput(50, allow_space=True)
              is_typing  = False
            elif event.key == K_ESCAPE:
              chat_input = misc.TextInput(50, allow_space=True)
              is_typing  = False
            else:
              chat_input.feed_key(event.key)
          else:
            if event.key == K_ESCAPE:
              self.client.send({"type": "bye"})
              running = False
            elif event.key == K_t:
              is_typing = True

      # Network messages
      for msg in self.client.recv_all():
        mtype = msg.get("type")
        if mtype == "state":
          pid = msg.get("pid", 0)   # default to host pid for phase-1 packets
          if pid not in remote_cars:
            # Phase 2: new client we haven't seen yet — create a placeholder car
            rp = player_mod.ReplayPlayer("P" + str(pid), 1, 1)
            rp.play(ct)
            remote_cars[pid] = rp
          car = remote_cars[pid].car
          car.ox       = car.x
          car.oy       = car.y
          car.x        = msg["x"] * misc.zoom
          car.y        = msg["y"] * misc.zoom
          car.oldAngle = car.angle
          car.angle    = msg["a"] / 1000.0
          car.blink    = msg.get("bl", 0)
          car.brake    = msg.get("br", 0)
          car.slide    = msg.get("sl", 0)
          car.movepos[0] = int(car.x) - int(car.ox)
          car.movepos[1] = int(car.y) - int(car.oy)
          car.rect.move_ip(car.movepos)
        elif mtype == "chat":
          chat_log.append(msg.get("sender", "?") + ": " + msg.get("text", ""))
        elif mtype == "finish":
          running = False

      # Clear old position rects and draw all remote cars
      for rp in remote_cars.values():
        car = rp.car
        if car.ox != 0:
          old_r = pygame.Rect(
            int(car.ox - car.sizeRect / 2),
            int(car.oy - car.sizeRect / 2),
            car.sizeRect, car.sizeRect)
          misc.screen.blit(ct.track, old_r, old_r)
          l.append(old_r)

      for rp in remote_cars.values():
        car = rp.car
        if car.brake == 0:
          car.image = car.cars[int((256.0 * car.angle / 2.0 / math.pi) % 256)]
        else:
          car.image = car.cars2[int((256.0 * car.angle / 2.0 / math.pi) % 256)]
        l.append(car.rect.__copy__())
        car.sprite.draw(misc.screen)

      # Chat overlay + hint
      _draw_chat_overlay(chat_log, chat_input.render_text() if is_typing else None)
      misc.screen.blit(hint_surf, (misc.screen.get_width() - hint_surf.get_width() - 4, 4))

      if i == 1:
        pygame.display.update(l)
        i = 0
        l = []
      else:
        i += 1

      clock.tick(100)

    # Race over banner
    misc.screen.blit(ct.track, (0, 0))
    over_surf = pygame.transform.rotozoom(
      misc.bigFont.render("Race over!", 1, misc.lightColor), 0, 1)
    orect = over_surf.get_rect()
    orect.center = misc.screen.get_rect().center
    misc.screen.blit(over_surf, orect)
    pygame.display.flip()
    misc.wait4Key()


# ===========================================================================
class NetworkClientRace:
  """Phase-2 entry point: a connected client races locally and exchanges
  car-state bidirectionally with the host.

  Architecture (phase 2)
  ----------------------
  * The client runs their own ``HumanPlayer`` physics locally (same as a
    single-player race) and calls ``client.send_state()`` every frame.
  * The host re-broadcasts all state packets so every participant renders
    everyone else as a ``ReplayPlayer`` (via ``NetworkWatchRace``-style logic).
  * ``remote_player_infos`` is the ``roster`` list received in the ``start``
    message: [{pid, name, color, level}, ...].  The client's own pid comes
    from ``client.player_id`` (set by the host's ``assigned`` message).

  This class is intentionally not yet implemented; it exists as a
  placeholder so the phase-2 wiring in ``pyRacerz.py`` can import and call
  it without structural changes to the rest of the codebase.

  Parameters
  ----------
  client              : NetworkClient  (connected, player_id assigned)
  human_player        : HumanPlayer    (not yet play()'d on the track)
  track_name          : str
  track_reverse       : int
  remote_player_infos : list of {pid, name, color, level} dicts
  laps                : int
  """

  def __init__(self, client, human_player,
               track_name, track_reverse,
               remote_player_infos=None, laps=3):
    self.client              = client
    self._play               = human_player
    self.track_name          = track_name
    self.track_reverse       = track_reverse
    self.remote_player_infos = remote_player_infos or []
    self.laps                = laps

  def run(self):
    raise NotImplementedError(
      "NetworkClientRace.run() is the phase-2 implementation target.\n"
      "Implement local physics + send_state() + multi-car rendering here."
    )