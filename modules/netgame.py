"""Network race module for pyRacerz.

NetworkHostRace   -- host plays a local race; broadcasts car state (pid=0)
                     each frame to all clients via a NetworkServer.
                     Also relays incoming client state (pid>0) back out so
                     all clients can render each other (phase 2 ready).
NetworkWatchRace  -- spectator receives live state packets keyed by pid and
                     renders each car; participates in chat via a NetworkClient.
NetworkClientRace -- active client racer: runs local physics/input, sends
                     state to host, and renders host-authoritative updates.
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
from . import collision

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


def _is_upper_layer(track_name, last_cp):
  if track_name.startswith("desert"):
    return last_cp == 80
  if track_name.startswith("city"):
    return last_cp == 48
  return False


def _apply_tunnel_mask(ct, car, last_cp):
  if _is_upper_layer(ct.name, last_cp):
    return

  part = pygame.Surface((car.sizeRect, car.sizeRect), HWSURFACE, 24).convert()
  part.blit(ct.trackF, (0, 0),
    (car.x - car.sizeRect / 2,
     car.y - car.sizeRect / 2,
     car.sizeRect, car.sizeRect))
  partArray = pygame.surfarray.array2d(part)
  aX = 0
  for arrayX in partArray:
    aY = 0
    for col in arrayX:
      if col % 256 != 0:
        car.image.set_at((aX, aY), (255, 255, 255, 0))
      aY += 1
    aX += 1


def _advance_progress(play, ct, popUp=None, place=None):
  """Advance checkpoint/lap for one player using host-authoritative trackF."""
  if play.raceFinish == 1:
    return

  color = ct.trackF.get_at((int(play.car.x), int(play.car.y)))
  r = color[0]

  if ct.reverse == 0:
    if r == play.lastCheckpoint + 16:
      play.lastCheckpoint = r
    elif r == 16:
      if play.lastCheckpoint == 16 * ct.nbCheckpoint:
        play.lastCheckpoint = r
        play.nbLap += 1
        if play.chrono < play.bestChrono:
          play.bestChrono = play.chrono
          tag = "B"
        else:
          tag = ""
        if popUp:
          rank_tag = "P" + str(place) if place is not None else ""
          popUp.addElement(
            play.car,
            play.name + " L" + str(play.nbLap) + " " + rank_tag + " " + misc.chrono2Str(play.chrono) + tag,
          )
        play.chrono = 0
      elif play.lastCheckpoint > 16:
        play.lastCheckpoint = r
        if popUp:
          popUp.addElement(play.car, play.name + " L" + str(play.nbLap + 1) + " MISSED")
        play.chrono = 0

  else:
    if r != 0 and r == play.lastCheckpoint - 16:
      play.lastCheckpoint = r
    elif r == 16 * ct.nbCheckpoint:
      if play.lastCheckpoint == 16:
        play.lastCheckpoint = r
        play.nbLap += 1
        if play.chrono < play.bestChrono:
          play.bestChrono = play.chrono
          tag = "B"
        else:
          tag = ""
        if popUp:
          rank_tag = "P" + str(place) if place is not None else ""
          popUp.addElement(
            play.car,
            play.name + " L" + str(play.nbLap) + " " + rank_tag + " " + misc.chrono2Str(play.chrono) + tag,
          )
        play.chrono = 0
      elif play.lastCheckpoint < 16 * ct.nbCheckpoint:
        play.lastCheckpoint = r
        if popUp:
          popUp.addElement(play.car, play.name + " L" + str(play.nbLap + 1) + " MISSED")
        play.chrono = 0


def _same_collision_layer(track_name, cp_a, cp_b):
  if track_name.startswith("desert"):
    return (cp_a == 80) == (cp_b == 80)
  if track_name.startswith("city"):
    return (cp_a == 48) == (cp_b == 48)
  return True


def _apply_singleplayer_collision(play, play2):
  """Mirror the directional collision response used by single-player mode."""
  playCollisionRects = []
  play2CollisionRects = []

  listIndex = pygame.Rect(play.car.listCarRect[0]).collidelistall(play2.car.listCarRect)
  if listIndex != []:
    playCollisionRects.append(0)
    for idx in listIndex:
      if idx not in play2CollisionRects:
        play2CollisionRects.append(idx)

  listIndex = pygame.Rect(play.car.listCarRect[1]).collidelistall(play2.car.listCarRect)
  if listIndex != []:
    playCollisionRects.append(1)
    for idx in listIndex:
      if idx not in play2CollisionRects:
        play2CollisionRects.append(idx)

  listIndex = pygame.Rect(play.car.listCarRect[2]).collidelistall(play2.car.listCarRect)
  if listIndex != []:
    playCollisionRects.append(2)
    for idx in listIndex:
      if idx not in play2CollisionRects:
        play2CollisionRects.append(idx)

  listIndex = pygame.Rect(play.car.listCarRect[3]).collidelistall(play2.car.listCarRect)
  if listIndex != []:
    playCollisionRects.append(3)
    for idx in listIndex:
      if idx not in play2CollisionRects:
        play2CollisionRects.append(idx)

  playCollisionRects.sort()

  if playCollisionRects == [0]:
    play.car.newSpeed = play.car.speed / 2 - abs(play2.car.speed / 2)
  elif playCollisionRects == [1]:
    play.car.newSpeed = play.car.speed / 2 + abs(play2.car.speed / 2)
  elif playCollisionRects == [2] or playCollisionRects == [0, 1, 2] or playCollisionRects == [0, 2] or playCollisionRects == [1, 2]:
    play.car.speedL = play.car.speedL + abs(play2.car.speed / 2) * 10
    play.car.newSpeed = 0
  elif playCollisionRects == [3] or playCollisionRects == [0, 1, 3] or playCollisionRects == [0, 3] or playCollisionRects == [1, 3]:
    play.car.speedL = play.car.speedL - abs(play2.car.speed / 2) * 10
    play.car.newSpeed = 0
  elif playCollisionRects != []:
    play.car.newSpeed = 0

  return playCollisionRects != []


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

  def __init__(self, server, human_player, current_track, laps=3, remote_player_infos=None):
    self.server       = server
    self._play        = human_player
    self.currentTrack = current_track
    self.laps         = laps
    self._remote_player_infos = remote_player_infos or []

  # ------------------------------------------------------------------
  def run(self):
    play         = self._play
    ct           = self.currentTrack

    play.play(ct, 1)

    # pid -> player object (host is pid 0; remote racers are ReplayPlayer)
    remote_players = {}
    for info in self._remote_player_infos:
      pid = int(info.get("pid", -1))
      if pid <= 0:
        continue
      rp = player_mod.ReplayPlayer(info.get("name", "P" + str(pid)), info.get("color", 1), info.get("level", 1))
      rp.play(ct)
      rank = max(1, pid + 1)
      rp.car.reInit(ct, rank)
      remote_players[pid] = rp

    players_by_pid = {0: play}
    players_by_pid.update(remote_players)
    dnf_by_pid = {}
    for pid in players_by_pid:
      dnf_by_pid[pid] = False
    finish_order = []
    host_tick = 0

    clock    = pygame.time.Clock()
    chat_log = []
    popUp    = misc.PopUp(ct)
    collision_grid = collision.SpatialGrid(int(64 * misc.zoom))

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
    running = True
    aborted = False
    while running:

      # Events
      for event in pygame.event.get():
        if event.type == QUIT:
          self.server.broadcast({"type": "finish", "standings": []})
          aborted = True
          running = False
          break
        elif event.type == KEYDOWN:
          if event.key == K_ESCAPE:
            self.server.broadcast({"type": "finish", "standings": []})
            aborted = True
            running = False
            break
          play.handle_keydown(event.key)
        elif event.type == KEYUP:
          play.handle_keyup(event.key)

      if not running:
        break

      play.update_controls()

      # Physics
      play.car.update()
      play.chrono += 1
      _advance_progress(play, ct, popUp, 1)

      if play.nbLap >= self.laps and play.raceFinish != 1:
        play.raceFinish = 1
        play.car.blink = 1
        finish_order.append(0)

      # Receive messages from clients
      for msg in self.server.recv_all():
        mtype = msg.get("type")
        if mtype == "chat":
          self.server.broadcast(msg)
          chat_log.append(msg.get("sender", "?") + ": " + msg.get("text", ""))
        elif mtype == "state":
          pid = int(msg.get("pid", -1))
          if pid <= 0:
            continue

          if pid not in players_by_pid:
            rp = player_mod.ReplayPlayer("P" + str(pid), 1, 1)
            rp.play(ct)
            rp.car.reInit(ct, max(1, pid + 1))
            players_by_pid[pid] = rp
            dnf_by_pid[pid] = False

          rp = players_by_pid[pid]
          car = rp.car
          car.ox = car.x
          car.oy = car.y
          car.x = int(msg.get("x", int(car.x / misc.zoom))) * misc.zoom
          car.y = int(msg.get("y", int(car.y / misc.zoom))) * misc.zoom
          car.oldAngle = car.angle
          car.angle = int(msg.get("a", int(car.angle * 1000))) / 1000.0
          car.brake = msg.get("br", 0)
          car.slide = msg.get("sl", 0)
          car.blink = msg.get("bl", 0)
          car.speed = float(msg.get("sp", getattr(car, "speed", 0.0)))
          car.movepos[0] = int(car.x) - int(car.ox)
          car.movepos[1] = int(car.y) - int(car.oy)
          car.rect.move_ip(car.movepos)

          if rp.raceFinish == 0:
            rp.chrono += 1
          _advance_progress(rp, ct, popUp)

          if rp.nbLap >= self.laps and rp.raceFinish != 1:
            rp.raceFinish = 1
            rp.car.blink = 1
            finish_order.append(pid)

        elif mtype == "bye":
          pid = int(msg.get("pid", -1))
          if pid < 0:
            pid = self.server.get_pid(msg.get("_client_idx", -1))
          if pid in players_by_pid and dnf_by_pid.get(pid, False) is False and players_by_pid[pid].raceFinish == 0:
            dnf_by_pid[pid] = True
            chat_log.append("*** " + players_by_pid[pid].name + " DNF (disconnect) ***")

      # Host authoritative online collisions
      active_players = []
      for pid, rp in players_by_pid.items():
        if dnf_by_pid.get(pid, False):
          continue
        if rp.raceFinish == 1:
          continue
        active_players.append(rp)

      collision_grid.rebuild(active_players, get_rect=lambda p: p.car.rect)
      for pa, pb in collision_grid.candidate_pairs():
        if not _same_collision_layer(ct.name, pa.lastCheckpoint, pb.lastCheckpoint):
          continue
        _apply_singleplayer_collision(pa, pb)
        _apply_singleplayer_collision(pb, pa)

      for rp in active_players:
        if rp.car.newSpeed != 0:
          rp.car.speed = rp.car.newSpeed
          rp.car.newSpeed = 0

      # Broadcast authoritative state for every non-DNF racer
      host_tick += 1
      for pid, rp in players_by_pid.items():
        if dnf_by_pid.get(pid, False):
          continue
        self.server.broadcast({
          "type": "state",
          "pid":  pid,
          "x":  int(rp.car.x / misc.zoom),
          "y":  int(rp.car.y / misc.zoom),
          "a":  int(rp.car.angle * 1000),
          "br": 1 if rp.car.brake > 0 else 0,
          "sl": rp.car.slide,
          "bl": rp.car.blink,
          "cp": rp.lastCheckpoint,
          "lap": rp.nbLap,
          "rf": rp.raceFinish,
          "sp": float(getattr(rp.car, "speed", 0.0)),
          "tick": host_tick,
        })

      # Full redraw to avoid dirty-rect artifacts with remote interpolation.
      misc.screen.blit(ct.track, (0, 0))

      ct.track.lock()
      for pid, rp in players_by_pid.items():
        if dnf_by_pid.get(pid, False):
          continue
        car = rp.car
        if car.brake == 0:
          car.image = car.cars[int((256.0 * car.angle / 2.0 / math.pi) % 256)].copy()
        else:
          car.image = car.cars2[int((256.0 * car.angle / 2.0 / math.pi) % 256)].copy()

        _apply_tunnel_mask(ct, car, rp.lastCheckpoint)
        car.sprite.draw(misc.screen)

      ct.track.unlock()

      # PopUp + chat overlay
      popUp.display()
      _draw_chat_overlay(chat_log)
      pygame.display.flip()

      # End race when every racer is finished or DNF
      race_done = True
      for pid, rp in players_by_pid.items():
        if dnf_by_pid.get(pid, False):
          continue
        if rp.raceFinish != 1:
          race_done = False
          break
      if race_done:
        running = False

      clock.tick(100)

    if aborted:
      return

    # Race finished
    standings = []
    finish_rank = 1
    for pid in finish_order:
      rp = players_by_pid.get(pid)
      if rp is None or dnf_by_pid.get(pid, False):
        continue
      standings.append({
        "pid": pid,
        "name": rp.name,
        "lap": rp.nbLap,
        "cp": rp.lastCheckpoint,
        "status": "FIN",
        "place": finish_rank,
      })
      finish_rank += 1

    for pid, rp in players_by_pid.items():
      if dnf_by_pid.get(pid, False):
        standings.append({
          "pid": pid,
          "name": rp.name,
          "lap": rp.nbLap,
          "cp": rp.lastCheckpoint,
          "status": "DNF",
          "place": None,
        })

    self.server.broadcast({"type": "finish", "standings": standings})

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
    # pid → lastCheckpoint, used for tunnel-mask logic (e.g. desert overpass)
    car_checkpoints = {}
    clock      = pygame.time.Clock()
    chat_log   = []
    chat_input = misc.TextInput(50, allow_space=True)
    is_typing  = False

    misc.screen.blit(ct.track, (0, 0))
    hint_surf = misc.popUpFont.render("[T] Chat   [ESC] Leave", 1, misc.darkColor, (0, 0, 0))
    misc.screen.blit(hint_surf, (misc.screen.get_width() - hint_surf.get_width() - 4, 4))
    pygame.display.flip()

    running = True
    aborted = False

    while running:

      # Events
      for event in pygame.event.get():
        if event.type == QUIT:
          self.client.send({
            "type": "bye",
            "name": self.spectator_name,
            "pid":  getattr(self.client, "player_id", -1),
          })
          aborted = True
          running = False
          break
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
              self.client.send({
                "type": "bye",
                "name": self.spectator_name,
                "pid":  getattr(self.client, "player_id", -1),
              })
              aborted = True
              running = False
            elif event.key == K_t:
              is_typing = True

      if not running:
        break

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
          car_checkpoints[pid] = msg.get("cp", car_checkpoints.get(pid, 0))
        elif mtype == "chat":
          chat_log.append(msg.get("sender", "?") + ": " + msg.get("text", ""))
        elif mtype == "finish":
          running = False

      # Erase old car positions, then draw all cars at current positions
      for rp in remote_cars.values():
        car = rp.car
        if car.ox != 0 or car.oy != 0:
          old_r = pygame.Rect(
            int(car.ox - car.sizeRect / 2),
            int(car.oy - car.sizeRect / 2),
            car.sizeRect, car.sizeRect)
          misc.screen.blit(ct.track, old_r, old_r)

      ct.track.lock()
      for pid, rp in remote_cars.items():
        car = rp.car
        if car.brake == 0:
          car.image = car.cars[int((256.0 * car.angle / 2.0 / math.pi) % 256)].copy()
        else:
          car.image = car.cars2[int((256.0 * car.angle / 2.0 / math.pi) % 256)].copy()

        # Apply tunnel/underpass mask from trackF so underpasses render correctly
        # Skip masking for desert overpass zone (checkpoint 80) where car is on top
        last_cp = car_checkpoints.get(pid, 0)
        if not (ct.name.startswith("desert") and last_cp == 80):
          part = pygame.Surface((car.sizeRect, car.sizeRect), HWSURFACE, 24).convert()
          part.blit(ct.trackF, (0, 0),
            (car.x - car.sizeRect / 2,
             car.y - car.sizeRect / 2,
             car.sizeRect, car.sizeRect))
          partArray = pygame.surfarray.array2d(part)
          aX = 0
          for arrayX in partArray:
            aY = 0
            for col in arrayX:
              if col % 256 != 0:
                car.image.set_at((aX, aY), (255, 255, 255, 0))
              aY += 1
            aX += 1

        car.sprite.draw(misc.screen)
      ct.track.unlock()

      # Chat overlay + hint — drawn last so they appear on top of everything
      _draw_chat_overlay(chat_log, chat_input.render_text() if is_typing else None)
      misc.screen.blit(hint_surf, (misc.screen.get_width() - hint_surf.get_width() - 4, 4))

      pygame.display.flip()
      clock.tick(60)

    if aborted:
      self.client.disconnect()
      return

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
  """Active network racer: a connected client races locally and exchanges
  car state bidirectionally with the host.

  Architecture (phase 2)
  ----------------------
  * The client runs their own ``HumanPlayer`` physics locally (same as a
    single-player race) and calls ``client.send_state()`` every frame.
  * The host re-broadcasts all state packets so every participant renders
    everyone else as a ``ReplayPlayer`` (via ``NetworkWatchRace``-style logic).
  * ``remote_player_infos`` is the ``roster`` list received in the ``start``
    message: [{pid, name, color, level}, ...].  The client's own pid comes
    from ``client.player_id`` (set by the host's ``assigned`` message).

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
    ct   = track_mod.Track(self.track_name, self.track_reverse)
    play = self._play

    if self.client.player_id < 0:
      # Last-chance fallback if assigned packet arrived late in lobby.
      for info in self.remote_player_infos:
        if info.get("color") == play.car.color and info.get("level") == play.car.level:
          self.client.player_id = int(info.get("pid", -1))
          break

    my_pid  = self.client.player_id if self.client.player_id >= 0 else 1
    my_rank = max(1, my_pid + 1)
    play.play(ct, my_rank)

    remote_cars = {}
    remote_targets = {}
    for info in self.remote_player_infos:
      pid = int(info.get("pid", -1))
      if pid < 0 or pid == my_pid:
        continue
      rp = player_mod.ReplayPlayer(info.get("name", "P" + str(pid)), info.get("color", 1), info.get("level", 1))
      rp.play(ct)
      rp.car.reInit(ct, max(1, pid + 1))
      remote_cars[pid] = rp

    clock      = pygame.time.Clock()
    chat_log   = []
    chat_input = misc.TextInput(50, allow_space=True)
    is_typing  = False
    tick       = 0
    running    = True
    aborted    = False
    finish_msg = None

    misc.screen.blit(ct.track, (0, 0))
    hint_surf = misc.popUpFont.render("[T] Chat   [ESC] Leave", 1, misc.darkColor, (0, 0, 0))
    misc.screen.blit(hint_surf, (misc.screen.get_width() - hint_surf.get_width() - 4, 4))
    pygame.display.flip()

    while running:

      # Events
      for event in pygame.event.get():
        if event.type == QUIT:
          self.client.send({"type": "bye", "name": play.name, "pid": my_pid})
          aborted = True
          running = False
          break

        elif event.type == KEYDOWN:
          if is_typing:
            if event.key == K_RETURN:
              text = chat_input.text.strip()
              if text:
                self.client.send({"type": "chat", "sender": play.name, "text": text})
              chat_input = misc.TextInput(50, allow_space=True)
              is_typing = False
            elif event.key == K_ESCAPE:
              chat_input = misc.TextInput(50, allow_space=True)
              is_typing = False
            else:
              chat_input.feed_key(event.key)
          else:
            if event.key == K_ESCAPE:
              self.client.send({"type": "bye", "name": play.name, "pid": my_pid})
              aborted = True
              running = False
            elif event.key == K_t:
              is_typing = True
            else:
              play.handle_keydown(event.key)

        elif event.type == KEYUP and not is_typing:
          play.handle_keyup(event.key)

      if not running:
        break

      if not is_typing:
        play.update_controls()
        play.car.update()
        play.chrono += 1
        _advance_progress(play, ct)

        if play.nbLap >= self.laps and play.raceFinish != 1:
          play.raceFinish = 1
          play.car.blink = 1

      tick += 1
      self.client.send_state(
        x=play.car.x / misc.zoom,
        y=play.car.y / misc.zoom,
        a=play.car.angle * 1000,
        br=1 if play.car.brake > 0 else 0,
        sl=play.car.slide,
        bl=play.car.blink,
        cp=play.lastCheckpoint,
        lap=play.nbLap,
        race_finish=play.raceFinish,
        sp=float(getattr(play.car, "speed", 0.0)),
        tick=tick,
      )

      # Network messages
      for msg in self.client.recv_all():
        mtype = msg.get("type")

        if mtype == "state":
          pid = int(msg.get("pid", -1))
          if pid < 0:
            continue

          if pid == my_pid:
            # Host-authoritative correction for local racer.
            tx = int(msg.get("x", int(play.car.x / misc.zoom))) * misc.zoom
            ty = int(msg.get("y", int(play.car.y / misc.zoom))) * misc.zoom
            ta = int(msg.get("a", int(play.car.angle * 1000))) / 1000.0

            dx = tx - play.car.x
            dy = ty - play.car.y
            dist = math.hypot(dx, dy)
            play.car.ox = play.car.x
            play.car.oy = play.car.y
            # Keep client feel responsive: only correct substantial divergence.
            if dist > 160:
              play.car.x = tx
              play.car.y = ty
            elif dist > 28:
              play.car.x += dx * 0.08
              play.car.y += dy * 0.08

            d_ang = (ta - play.car.angle + math.pi) % (2 * math.pi) - math.pi
            if abs(d_ang) > 2.2:
              play.car.angle = ta
            elif abs(d_ang) > 0.35:
              play.car.angle += d_ang * 0.10

            play.car.rect.center = (int(play.car.x), int(play.car.y))
            # Do not overwrite local transient physics (speed/brake/slide)
            # with delayed echoed states; that creates a "high friction" feel.
            play.car.blink = msg.get("bl", play.car.blink)

            play.lastCheckpoint = msg.get("cp", play.lastCheckpoint)
            play.nbLap = msg.get("lap", play.nbLap)
            play.raceFinish = msg.get("rf", play.raceFinish)

          else:
            if pid not in remote_cars:
              rp = player_mod.ReplayPlayer("P" + str(pid), 1, 1)
              rp.play(ct)
              rp.car.reInit(ct, max(1, pid + 1))
              remote_cars[pid] = rp

            remote_targets[pid] = {
              "x": int(msg.get("x", int(remote_cars[pid].car.x / misc.zoom))) * misc.zoom,
              "y": int(msg.get("y", int(remote_cars[pid].car.y / misc.zoom))) * misc.zoom,
              "a": int(msg.get("a", int(remote_cars[pid].car.angle * 1000))) / 1000.0,
              "br": msg.get("br", 0),
              "sl": msg.get("sl", 0),
              "bl": msg.get("bl", 0),
              "cp": msg.get("cp", remote_cars[pid].lastCheckpoint),
              "lap": msg.get("lap", remote_cars[pid].nbLap),
              "rf": msg.get("rf", remote_cars[pid].raceFinish),
            }

        elif mtype == "chat":
          chat_log.append(msg.get("sender", "?") + ": " + msg.get("text", ""))

        elif mtype == "finish":
          finish_msg = msg
          running = False

      # Interpolate remote racers toward authoritative host state
      for pid, rp in remote_cars.items():
        tgt = remote_targets.get(pid)
        if not tgt:
          continue

        car = rp.car
        car.ox = car.x
        car.oy = car.y
        car.x += (tgt["x"] - car.x) * 0.45
        car.y += (tgt["y"] - car.y) * 0.45
        d_ang = (tgt["a"] - car.angle + math.pi) % (2 * math.pi) - math.pi
        car.angle += d_ang * 0.40
        car.rect.center = (int(car.x), int(car.y))

        car.brake = tgt.get("br", car.brake)
        car.slide = tgt.get("sl", car.slide)
        car.blink = tgt.get("bl", car.blink)
        rp.lastCheckpoint = tgt.get("cp", rp.lastCheckpoint)
        rp.nbLap = tgt.get("lap", rp.nbLap)
        rp.raceFinish = tgt.get("rf", rp.raceFinish)

      # Draw cars on a full redraw to eliminate lingering artifacts.
      all_players = [play] + list(remote_cars.values())
      misc.screen.blit(ct.track, (0, 0))
      ct.track.lock()
      for rp in all_players:
        car = rp.car
        if car.brake == 0:
          car.image = car.cars[int((256.0 * car.angle / 2.0 / math.pi) % 256)].copy()
        else:
          car.image = car.cars2[int((256.0 * car.angle / 2.0 / math.pi) % 256)].copy()

        _apply_tunnel_mask(ct, car, rp.lastCheckpoint)
        car.sprite.draw(misc.screen)
      ct.track.unlock()

      _draw_chat_overlay(chat_log, chat_input.render_text() if is_typing else None)
      misc.screen.blit(hint_surf, (misc.screen.get_width() - hint_surf.get_width() - 4, 4))

      pygame.display.flip()
      clock.tick(100)

    if aborted:
      self.client.disconnect()
      return

    # End-of-race banner + compact standings if provided by host
    misc.screen.blit(ct.track, (0, 0))
    title = pygame.transform.rotozoom(misc.bigFont.render("Race over!", 1, misc.lightColor), 0, 1)
    tr = title.get_rect()
    tr.centerx = misc.screen.get_rect().centerx
    tr.centery = int(misc.screen.get_rect().centery * 0.7)
    misc.screen.blit(title, tr)

    standings = finish_msg.get("standings", []) if isinstance(finish_msg, dict) else []
    y = tr.bottom + int(8 * misc.zoom)
    for row in standings[:6]:
      if row.get("status") == "DNF":
        text = row.get("name", "?") + "  DNF"
      else:
        text = str(row.get("place", "?")) + ". " + row.get("name", "?")
      surf = misc.popUpFont.render(text[:48], 1, misc.lightColor, (0, 0, 0))
      rr = surf.get_rect()
      rr.centerx = misc.screen.get_rect().centerx
      rr.y = y
      misc.screen.blit(surf, rr)
      y += rr.height + int(2 * misc.zoom)

    pygame.display.flip()
    misc.wait4Key()