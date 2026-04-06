import math

from . import misc
from .ai_track_model import TrackModelCache
from .ai_types import BehaviorState
from .ai_types import BotRuntimeState


class DirectAIRuntime:
  """Direct port of the legacy AI steering logic.

  Bypasses the entire boids/perception/forces pipeline and directly
  sets the key presses using the exact same logic as compute() in
  player.py, but with improved stuck recovery.
  """

  def __init__(self, level):
    self.level = level
    self.stuck_counter = 0
    self.recover_frames = 0
    self.route_stall_frames = 0
    self.prev_checkpoint = None
    self.track_cache = TrackModelCache()

    # Tracks with underpasses / tight overlaps or dirt traps need a more conservative route lock.
    self.complex_tracks = {"city", "forest", "formula", "http", "kart", "wave"}
    
    # Checkpoint tracking: log when the bot reaches a new checkpoint.
    self.last_tracked_checkpoint = None
    self.checkpoint_hit_count = 0
    # Flow-field navigation state.
    self.current_checkpoint_index = None
    self.laps_completed = 0
    self.underpass_zones_unlocked = []
    self.flow_field_cache = {}
    self._last_track_key = None
    self._last_synced_last_checkpoint = None

  def step(self, bot_player, all_players):
    car = bot_player.car
    track_name = getattr(car.track, "name", "")
    track_model = self.track_cache.get_for_track(car.track)
    track_key = "%s:%s" % (track_model.name, track_model.reverse)
    if self._last_track_key != track_key:
      self._last_track_key = track_key
      self.current_checkpoint_index = None
      self.laps_completed = 0
      self.underpass_zones_unlocked = []
      self.flow_field_cache = {}
      self._last_synced_last_checkpoint = None
    planner = self.track_cache.get_planner_targets(
      track_model,
      bot_player.lastCheckpoint,
      (car.x, car.y),
      car.speed,
      car.maxSpeed,
    )
    # Planner steering is disabled here because it can pull the bot toward
    # the wrong branch on overlap-heavy tracks. Keep the legacy raycast as
    # the steering source and only use the recovery logic below.
    planner_ok = False

    # Keep route-target guidance disabled for now; legacy checkpoint-aware
    # rays are more reliable about lap direction on overlap-heavy tracks.
    route_targets = []

    # Progress watchdog: if checkpoint progress stalls, bias hard toward the next route target.
    if self.prev_checkpoint == bot_player.lastCheckpoint:
      self.route_stall_frames += 1
    else:
      self.route_stall_frames = 0
      self.prev_checkpoint = bot_player.lastCheckpoint
    
    # Checkpoint tracking: detect when bot reaches a new checkpoint.
    if bot_player.lastCheckpoint != self.last_tracked_checkpoint:
      if self.last_tracked_checkpoint is not None:  # Skip first assignment
        self.checkpoint_hit_count += 1
      self.last_tracked_checkpoint = bot_player.lastCheckpoint

    is_complex = track_name in self.complex_tracks

    # --- Stuck recovery ---
    if abs(car.speed) < 0.15:
      self.stuck_counter += 1
    else:
      self.stuck_counter = max(0, self.stuck_counter - 3)

    if self.recover_frames > 0:
      self.recover_frames -= 1
      bot_player.keyAccelPressed = 0
      bot_player.keyBrakePressed = 1
      car.doBrake()
      car.noAccel()
      # Steer slightly while reversing
      if route_targets:
        steer_left = self._route_turn_dir(car, route_targets[0][1]) < 0
      else:
        steer_left = True
      bot_player.keyLeftPressed = 1 if steer_left else 0
      bot_player.keyRightPressed = 0 if steer_left else 1
      if steer_left:
        car.doLeft()
      else:
        car.doRight()
      return

    if self.stuck_counter > 60:
      self.recover_frames = 20 if track_name == "forest" else 18 if track_name == "city" else 15
      self.stuck_counter = 0
      return

    if self._step_with_flow_field(bot_player, track_model):
      return

    # --- Legacy AI raycasting (exact port of compute()) ---
    angle = car.angle

    # Nose coordinates (front of car)
    cx = car.x - math.cos(angle) * car.height * 1.2 / 2
    cy = car.y - math.sin(angle) * car.height * 1.2 / 2
    # Front-left and front-right corners
    coord0 = (int(cx - math.sin(angle) * car.width * 1.2 / 2),
              int(cy + math.cos(angle) * car.width * 1.2 / 2))
    coord1 = (int(cx + math.sin(angle) * car.width * 1.2 / 2),
              int(cy - math.cos(angle) * car.width * 1.2 / 2))

    # 7 rays — exact same angles and origin points as legacy AI
    route_dir = None
    route_dir2 = None
    if route_targets:
      route_dir = self._route_direction(car, route_targets[0][1])
      if len(route_targets) > 1:
        route_dir2 = self._route_direction(car, route_targets[1][1])

    minLine = []
    minLine.append(self._findMinObstacle(bot_player, coord0[0], coord0[1], angle - math.pi / 4.0, route_dir, route_dir2, is_complex))
    minLine.append(self._findMinObstacle(bot_player, coord0[0], coord0[1], angle - 2.0 * math.pi / 5.0, route_dir, route_dir2, is_complex))
    minLine.append(self._findMinObstacle(bot_player, coord0[0], coord0[1], angle - math.pi / 5.0, route_dir, route_dir2, is_complex))
    # Center: take worst of both nose corners
    minLine.append(min(
      self._findMinObstacle(bot_player, coord0[0], coord0[1], angle, route_dir, route_dir2, is_complex),
      self._findMinObstacle(bot_player, coord1[0], coord1[1], angle, route_dir, route_dir2, is_complex),
    ))
    minLine.append(self._findMinObstacle(bot_player, coord1[0], coord1[1], angle + math.pi / 5.0, route_dir, route_dir2, is_complex))
    minLine.append(self._findMinObstacle(bot_player, coord1[0], coord1[1], angle + 2.0 * math.pi / 5.0, route_dir, route_dir2, is_complex))
    minLine.append(self._findMinObstacle(bot_player, coord1[0], coord1[1], angle + math.pi / 4.0, route_dir, route_dir2, is_complex))

    # Find best direction
    maxDist = -9999
    maxDistIndex = -1
    for i in range(7):
      if maxDist < minLine[i]:
        maxDist = minLine[i]
        maxDistIndex = i

    # Privilege straight ahead
    if maxDist == minLine[3]:
      maxDistIndex = 3

    # Wall limits depend on difficulty level
    if self.level == 1:
      wallLimit1 = 300
      wallLimit2 = 400
      wallLimit3 = 400
    elif self.level == 2:
      wallLimit1 = 450
      wallLimit2 = 600
      wallLimit3 = 600
    else:
      wallLimit1 = 600
      wallLimit2 = 800
      wallLimit3 = 800

    # Global turn caution: reduce all wall limits so bot brakes sooner on turns.
    # This prevents off-track incidents by encouraging slower turn entry.
    turn_caution = 0.65
    wallLimit1 *= turn_caution
    wallLimit2 *= turn_caution
    wallLimit3 *= turn_caution

    if is_complex:
      wallLimit1 *= 0.90
      wallLimit2 *= 0.90
      wallLimit3 *= 0.90

    if track_name == "forest":
      wallLimit1 *= 0.80
      wallLimit2 *= 0.82
      wallLimit3 *= 0.82
    elif track_name == "city":
      wallLimit1 *= 0.85
      wallLimit2 *= 0.88
      wallLimit3 *= 0.88

    # If completely surrounded by off-road, find nearest road
    if maxDist == 0:
      minLine2 = []
      minLine2.append(self._findMinRoad(bot_player, coord0[0], coord0[1], angle - math.pi / 4.0, route_dir, route_dir2, is_complex))
      minLine2.append(self._findMinRoad(bot_player, coord0[0], coord0[1], angle - 2.0 * math.pi / 5.0, route_dir, route_dir2, is_complex))
      minLine2.append(self._findMinRoad(bot_player, coord0[0], coord0[1], angle - math.pi / 5.0, route_dir, route_dir2, is_complex))
      minLine2.append(self._findMinRoad(bot_player, int(car.x), int(car.y), angle, route_dir, route_dir2, is_complex))
      minLine2.append(self._findMinRoad(bot_player, coord1[0], coord1[1], angle + math.pi / 5.0, route_dir, route_dir2, is_complex))
      minLine2.append(self._findMinRoad(bot_player, coord1[0], coord1[1], angle + 2.0 * math.pi / 5.0, route_dir, route_dir2, is_complex))
      minLine2.append(self._findMinRoad(bot_player, coord1[0], coord1[1], angle + math.pi / 4.0, route_dir, route_dir2, is_complex))

      minDist = 9999
      minDistIndex = -1
      for i in range(7):
        if minDist > minLine2[i]:
          minDist = minLine2[i]
          minDistIndex = i

      if minDist == minLine2[3]:
        minDistIndex = 3

      bot_player.keyAccelPressed = 1
      bot_player.keyBrakePressed = 0
      if minDistIndex in (0, 1, 2):
        bot_player.keyLeftPressed = 1
      else:
        bot_player.keyLeftPressed = 0
      if minDistIndex in (4, 5, 6):
        bot_player.keyRightPressed = 1
      else:
        bot_player.keyRightPressed = 0

    # Speed-dependent braking when wall is close
    elif (car.speed > 0 and
          ((maxDist < wallLimit1 * (car.speed / car.maxSpeed) and maxDistIndex == 3 and maxDist < 800) or
           (maxDist < wallLimit2 * (car.speed / car.maxSpeed) and (maxDistIndex == 2 or maxDistIndex == 4) and maxDist < 800) or
           (maxDist < wallLimit3 * (car.speed / car.maxSpeed) and (maxDistIndex == 1 or maxDistIndex == 5) and maxDist < 800) or
           (maxDistIndex == 0 or maxDistIndex == 6)
          )):
      if maxDistIndex == 3:
        bot_player.keyAccelPressed = 0
        bot_player.keyBrakePressed = 1
        bot_player.keyLeftPressed = 0
        bot_player.keyRightPressed = 0
      elif maxDistIndex in (2, 1, 0):
        bot_player.keyAccelPressed = 0
        bot_player.keyBrakePressed = 1
        bot_player.keyLeftPressed = 1
        bot_player.keyRightPressed = 0
      elif maxDistIndex in (4, 5, 6):
        bot_player.keyAccelPressed = 0
        bot_player.keyBrakePressed = 1
        bot_player.keyLeftPressed = 0
        bot_player.keyRightPressed = 1
    else:
      # Normal driving
      if maxDistIndex == 3:
        bot_player.keyAccelPressed = 1
        bot_player.keyBrakePressed = 0
        # Try to center on road (legacy behavior)
        if max(minLine[0], minLine[6]) - min(minLine[0], minLine[6]) > 100:
          if minLine[0] > minLine[6]:
            bot_player.keyLeftPressed = 1
            bot_player.keyRightPressed = 0
          else:
            bot_player.keyLeftPressed = 0
            bot_player.keyRightPressed = 1
        else:
          bot_player.keyLeftPressed = 0
          bot_player.keyRightPressed = 0
      elif maxDistIndex == 2:
        bot_player.keyAccelPressed = 1
        bot_player.keyBrakePressed = 0
        bot_player.keyLeftPressed = 1
        bot_player.keyRightPressed = 0
      elif maxDistIndex == 4:
        bot_player.keyAccelPressed = 1
        bot_player.keyBrakePressed = 0
        bot_player.keyLeftPressed = 0
        bot_player.keyRightPressed = 1
      elif maxDistIndex == 1:
        bot_player.keyAccelPressed = 0
        bot_player.keyBrakePressed = 0
        bot_player.keyLeftPressed = 1
        bot_player.keyRightPressed = 0
      elif maxDistIndex == 5:
        bot_player.keyAccelPressed = 0
        bot_player.keyBrakePressed = 0
        bot_player.keyLeftPressed = 0
        bot_player.keyRightPressed = 1

    # Never brake at very low speed
    if car.speed < 0.5:
      bot_player.keyBrakePressed = 0

    if track_name == "forest" and self._on_offroad(bot_player):
      # Forest roundabout: keep the bot from digging into dirt.
      if car.speed > 0.8:
        bot_player.keyAccelPressed = 0
        bot_player.keyBrakePressed = 1
      else:
        bot_player.keyBrakePressed = 0

    # Complex tracks need a little more patience through underpasses/overlaps.
    if is_complex and maxDistIndex == 3 and car.speed > car.maxSpeed * 0.82:
      bot_player.keyAccelPressed = 0
      bot_player.keyBrakePressed = 1

    # Planner override: keep turns smooth and speed-aware when confidence is high.
    # Legacy ray logic above remains the fallback path.
    if planner_ok:
      self._apply_planner_control(bot_player, planner)

    # Apply key presses to car
    if bot_player.keyAccelPressed == 1:
      car.doAccel()
    else:
      car.noAccel()
    if bot_player.keyBrakePressed == 1:
      car.doBrake()
    else:
      car.noBrake()
    if bot_player.keyLeftPressed == 1:
      car.doLeft()
    if bot_player.keyRightPressed == 1:
      car.doRight()
    if bot_player.keyLeftPressed == 0 and bot_player.keyRightPressed == 0:
      car.noWheel()

  def _findMinObstacle(self, bot_player, x, y, angle, route_dir=None, route_dir2=None, is_complex=False):
    """Exact port of legacy findMinObstacle with robust checkpoint matching."""
    track_f = bot_player.car.track.trackF
    reverse = bot_player.car.track.reverse
    last_cp = bot_player.lastCheckpoint
    zoom = misc.zoom

    dist = 0
    if x <= 10 or x >= 1014 * zoom or y <= 10 or y >= 758 * zoom:
      return dist

    pix = track_f.get_at((int(x), int(y)))

    while x > 10 and x < 1014 * zoom and y > 10 and y < 758 * zoom and dist < 600 * zoom and pix[1] == 255:
      if dist < 10 * zoom:
        step = 1.0
      elif dist < 40 * zoom:
        step = 5.0 * zoom
      elif dist < 100 * zoom:
        step = 10.0 * zoom
      elif dist < 200 * zoom:
        step = 30.0 * zoom
      elif dist < 600 * zoom:
        step = 60.0 * zoom

      x = x - math.cos(angle) * step
      y = y - math.sin(angle) * step
      dist = dist + step

      cp_hit = self._checkpoint_id_from_pixel(pix)
      if cp_hit is not None:
        next_cp, prev_cp = self._next_prev_checkpoint(last_cp, reverse)
        if cp_hit == next_cp:
          dist = dist + 200 * zoom
        elif cp_hit == prev_cp:
          dist = dist - 100 * zoom

      if x > 10 and x < 1014 * zoom and y > 10 and y < 758 * zoom:
        pix = track_f.get_at((int(x), int(y)))
      else:
        dist = dist - 100 * zoom
        break


    return dist

  def _clamp(self, value, lo, hi):
    return max(lo, min(hi, value))

  def _wrap_angle(self, angle):
    while angle > math.pi:
      angle -= 2.0 * math.pi
    while angle < -math.pi:
      angle += 2.0 * math.pi
    return angle

  def _next_checkpoint_index(self, track_model, last_checkpoint):
    ids = track_model.checkpoint_ids
    if not ids:
      return 0
    if last_checkpoint in ids:
      return (ids.index(last_checkpoint) + 1) % len(ids)
    return 0

  def _sync_underpass_state(self, track_model, passed_checkpoint_index):
    regions = track_model.blue_regions
    if len(self.underpass_zones_unlocked) != len(regions):
      self.underpass_zones_unlocked = [False for _ in regions]
      self.flow_field_cache = {}

    changed = False
    for region in regions:
      rid = int(region.get("id", -1))
      if rid < 0 or rid >= len(self.underpass_zones_unlocked):
        continue
      unlock_after = int(region.get("unlock_after_checkpoint", 0))
      # Unlock is monotonic within a race: once opened, keep it open.
      should_unlock = passed_checkpoint_index >= unlock_after
      if should_unlock and not self.underpass_zones_unlocked[rid]:
        self.underpass_zones_unlocked[rid] = True
        changed = True

    if changed:
      self.flow_field_cache = {}

  def _sample_flow_vector(self, flow_field, tile):
    if tile in flow_field:
      vec = flow_field[tile]
      if vec[0] != 0.0 or vec[1] != 0.0:
        return vec

    tx, ty = tile
    neighbors = (
      (tx + 1, ty),
      (tx - 1, ty),
      (tx, ty + 1),
      (tx, ty - 1),
      (tx + 1, ty + 1),
      (tx - 1, ty - 1),
      (tx + 1, ty - 1),
      (tx - 1, ty + 1),
    )
    for n in neighbors:
      if n in flow_field:
        vec = flow_field[n]
        if vec[0] != 0.0 or vec[1] != 0.0:
          return vec
    return None

  def _step_with_flow_field(self, bot_player, track_model):
    if not track_model.checkpoint_ids:
      return False

    expected_idx = self._next_checkpoint_index(track_model, bot_player.lastCheckpoint)
    if self.current_checkpoint_index is None:
      self.current_checkpoint_index = expected_idx
      self._last_synced_last_checkpoint = bot_player.lastCheckpoint
    elif self._last_synced_last_checkpoint != bot_player.lastCheckpoint:
      self.current_checkpoint_index = expected_idx
      self._last_synced_last_checkpoint = bot_player.lastCheckpoint

    ids = track_model.checkpoint_ids
    if bot_player.lastCheckpoint in ids:
      segment_idx = ids.index(bot_player.lastCheckpoint)
    else:
      segment_idx = (self.current_checkpoint_index - 1) % len(ids)

    # Strict segment rule: only use the precomputed field for the current
    # checkpoint segment (CPn -> CPn+1). No global road mask pathfinding.
    flow_field = track_model.segment_flow_fields.get(segment_idx, {})

    if not flow_field:
      return False

    car = bot_player.car
    tile_size = max(1, int(track_model.tile_size))
    tile = (int(car.x) // tile_size, int(car.y) // tile_size)
    flow_dir = self._sample_flow_vector(flow_field, tile)
    if flow_dir is None:
      return False

    desired_heading = math.atan2(-flow_dir[1], -flow_dir[0])
    heading_error = self._wrap_angle(desired_heading - car.angle)
    steer_cmd = self._clamp(heading_error / (math.pi / 3.0), -1.0, 1.0)

    vel_x = -math.cos(car.angle) * max(0.0, car.speed)
    vel_y = -math.sin(car.angle) * max(0.0, car.speed)
    vel_n = (vel_x * vel_x + vel_y * vel_y) ** 0.5
    flow_n = (flow_dir[0] * flow_dir[0] + flow_dir[1] * flow_dir[1]) ** 0.5
    dot = 1.0
    if vel_n > 1e-6 and flow_n > 1e-6:
      dot = (vel_x * flow_dir[0] + vel_y * flow_dir[1]) / (vel_n * flow_n)

    throttle = 1.0
    brake = 0.0
    abs_he = abs(heading_error)
    if abs_he > (math.pi / 3.0) or dot < 0.35:
      throttle = 0.35
    if abs_he > (math.pi / 2.0) or dot < 0.10:
      throttle = 0.0
      brake = 0.65
    if car.maxSpeed > 1e-6 and car.speed > car.maxSpeed * 0.90 and abs_he > (math.pi / 4.0):
      throttle = 0.0
      brake = max(brake, 0.40)
    if car.speed < 0.5:
      brake = 0.0

    bot_player.keyLeftPressed = 1 if steer_cmd < -0.10 else 0
    bot_player.keyRightPressed = 1 if steer_cmd > 0.10 else 0
    bot_player.keyAccelPressed = 1 if throttle > 0.30 else 0
    bot_player.keyBrakePressed = 1 if brake > 0.20 else 0

    if bot_player.keyAccelPressed == 1:
      car.doAccel()
    else:
      car.noAccel()
    if bot_player.keyBrakePressed == 1:
      car.doBrake()
    else:
      car.noBrake()
    if bot_player.keyLeftPressed == 1:
      car.doLeft()
    if bot_player.keyRightPressed == 1:
      car.doRight()
    if bot_player.keyLeftPressed == 0 and bot_player.keyRightPressed == 0:
      car.noWheel()

    target_cp = track_model.checkpoint_ids[self.current_checkpoint_index]
    target_pos = track_model.checkpoint_centroids.get(target_cp)
    if target_pos is not None:
      dx = target_pos[0] - car.x
      dy = target_pos[1] - car.y
      if dx * dx + dy * dy <= (tile_size * 2.2) * (tile_size * 2.2):
        old_idx = self.current_checkpoint_index
        self.current_checkpoint_index = (self.current_checkpoint_index + 1) % len(track_model.checkpoint_ids)
        if self.current_checkpoint_index <= old_idx:
          self.laps_completed += 1
        self._sync_underpass_state(track_model, old_idx)

    return True

  def _findMinRoad(self, bot_player, x, y, angle, route_dir=None, route_dir2=None, is_complex=False):
    """Exact port of legacy findMinRoad with robust checkpoint matching."""
    track_f = bot_player.car.track.trackF
    reverse = bot_player.car.track.reverse
    last_cp = bot_player.lastCheckpoint
    zoom = misc.zoom

    dist = 0
    if x <= 10 or x >= 1014 * zoom or y <= 10 or y >= 758 * zoom:
      return dist

    pix = track_f.get_at((int(x), int(y)))

    while x > 10 and x < 1014 * zoom and y > 10 and y < 758 * zoom and dist < 600 * zoom and pix[1] != 255:
      if dist < 10 * zoom:
        step = 1.0
      elif dist < 40 * zoom:
        step = 5.0 * zoom
      elif dist < 100 * zoom:
        step = 10.0 * zoom
      elif dist < 200 * zoom:
        step = 30.0 * zoom
      elif dist < 600 * zoom:
        step = 60.0 * zoom

      x = x - math.cos(angle) * step
      y = y - math.sin(angle) * step
      dist = dist + step

      cp_hit = self._checkpoint_id_from_pixel(pix)
      if cp_hit is not None:
        next_cp, prev_cp = self._next_prev_checkpoint(last_cp, reverse)
        if cp_hit == next_cp:
          dist = dist - 400 * zoom
        elif cp_hit == prev_cp:
          dist = dist + 100 * zoom

      if x > 10 and x < 1014 * zoom and y > 10 and y < 758 * zoom:
        pix = track_f.get_at((int(x), int(y)))
      else:
        dist = dist + 1000 * zoom
        break


    return dist

  def _route_direction(self, car, target):
    dx = target[0] - car.x
    dy = target[1] - car.y
    dist = math.sqrt(dx * dx + dy * dy)
    if dist <= 1e-6:
      return (0.0, 0.0)
    return (dx / dist, dy / dist)

  def _route_bias(self, ray_angle, route_dir, route_dir2, is_complex, track_name=""):
    if route_dir is None:
      return 0.0
    ray_dir = (-math.cos(ray_angle), -math.sin(ray_angle))
    score = max(0.0, ray_dir[0] * route_dir[0] + ray_dir[1] * route_dir[1])
    if route_dir2 is not None:
      score = max(score, max(0.0, ray_dir[0] * route_dir2[0] + ray_dir[1] * route_dir2[1]) * 0.8)
    base = 220.0 if is_complex else 160.0
    if track_name == "city":
      base = 280.0
    elif track_name == "forest":
      base = 240.0
    return score * base

  def _best_ray_for_route(self, base_angle, route_dir, route_dir2=None, track_name=""):
    angle_offsets = [
      -math.pi / 4.0,
      -2.0 * math.pi / 5.0,
      -math.pi / 5.0,
      0.0,
      math.pi / 5.0,
      2.0 * math.pi / 5.0,
      math.pi / 4.0,
    ]
    best_idx = 3
    best_score = -1.0
    for i, off in enumerate(angle_offsets):
      ray_angle = base_angle + off
      ray_dir = (-math.cos(ray_angle), -math.sin(ray_angle))
      score = max(0.0, ray_dir[0] * route_dir[0] + ray_dir[1] * route_dir[1])
      if route_dir2 is not None:
        score = max(score, max(0.0, ray_dir[0] * route_dir2[0] + ray_dir[1] * route_dir2[1]) * 0.8)
      if score > best_score:
        best_score = score
        best_idx = i
    return best_idx

  def _on_offroad(self, bot_player):
    track_f = bot_player.car.track.trackF
    ix = int(bot_player.car.x)
    iy = int(bot_player.car.y)
    width = track_f.get_width()
    height = track_f.get_height()
    if ix < 1 or iy < 1 or ix >= width - 1 or iy >= height - 1:
      return True
    return track_f.get_at((ix, iy))[1] != 255

  def _in_city_underpass_zone(self, car):
    # Broad central city zone where the map crosses itself/underpasses.
    # We only use this as an emergency override when progress is poor.
    if getattr(car.track, "name", "") != "city":
      return False
    return 320 <= car.x <= 650 and 180 <= car.y <= 460

  def _route_turn_dir(self, car, target):
    """Return signed turn direction toward target in car-local space.

    Negative means turn left, positive means turn right.
    """
    dx = target[0] - car.x
    dy = target[1] - car.y
    forward = (-math.cos(car.angle), -math.sin(car.angle))
    target_len = math.sqrt(dx * dx + dy * dy)
    if target_len <= 1e-6:
      return 0.0
    target_dir = (dx / target_len, dy / target_len)
    # 2D cross product sign indicates left/right turn relative to forward.
    return forward[0] * target_dir[1] - forward[1] * target_dir[0]

  def _drive_to_route_target(self, bot_player, target, aggressive=False, offroad=False):
    car = bot_player.car
    steer = self._route_turn_dir(car, target)

    bot_player.keyLeftPressed = 1 if steer < -0.04 else 0
    bot_player.keyRightPressed = 1 if steer > 0.04 else 0
    if bot_player.keyLeftPressed == 0 and bot_player.keyRightPressed == 0:
      bot_player.car.noWheel()
    elif bot_player.keyLeftPressed == 1:
      bot_player.car.doLeft()
    else:
      bot_player.car.doRight()

    # Keep forward motion modest so it doesn't overshoot the wrong branch.
    if offroad:
      bot_player.keyAccelPressed = 0 if car.speed > 0.75 else 1
      bot_player.keyBrakePressed = 1 if car.speed > 1.0 else 0
    else:
      if aggressive:
        bot_player.keyAccelPressed = 1 if car.speed < car.maxSpeed * 0.78 else 0
        bot_player.keyBrakePressed = 1 if car.speed > car.maxSpeed * 0.88 else 0
      else:
        bot_player.keyAccelPressed = 1 if car.speed < car.maxSpeed * 0.70 else 0
        bot_player.keyBrakePressed = 1 if car.speed > car.maxSpeed * 0.82 else 0

    if bot_player.keyAccelPressed == 1:
      car.doAccel()
    else:
      car.noAccel()
    if bot_player.keyBrakePressed == 1:
      car.doBrake()
    else:
      car.noBrake()

  def _drive_blended_route_road(self, bot_player, route_targets, aggressive=False, offroad=False, track_name=""):
    """Blend checkpoint direction with road-following rays.

    This keeps the bot from choosing a checkpoint direction that crosses
    dirt, walls, or the wrong bridge lane on self-overlapping tracks.
    """
    car = bot_player.car
    angle = car.angle

    cx = car.x - math.cos(angle) * car.height * 1.2 / 2
    cy = car.y - math.sin(angle) * car.height * 1.2 / 2
    coord0 = (int(cx - math.sin(angle) * car.width * 1.2 / 2),
              int(cy + math.cos(angle) * car.width * 1.2 / 2))
    coord1 = (int(cx + math.sin(angle) * car.width * 1.2 / 2),
              int(cy - math.cos(angle) * car.width * 1.2 / 2))

    route_dir = self._route_direction(car, route_targets[0][1]) if route_targets else None
    route_dir2 = self._route_direction(car, route_targets[1][1]) if len(route_targets) > 1 else None

    ray_offsets = [
      -math.pi / 4.0,
      -2.0 * math.pi / 5.0,
      -math.pi / 5.0,
      0.0,
      math.pi / 5.0,
      2.0 * math.pi / 5.0,
      math.pi / 4.0,
    ]

    minLine = [
      self._findMinObstacle(bot_player, coord0[0], coord0[1], angle + ray_offsets[0], route_dir, route_dir2, True),
      self._findMinObstacle(bot_player, coord0[0], coord0[1], angle + ray_offsets[1], route_dir, route_dir2, True),
      self._findMinObstacle(bot_player, coord0[0], coord0[1], angle + ray_offsets[2], route_dir, route_dir2, True),
      min(
        self._findMinObstacle(bot_player, coord0[0], coord0[1], angle + ray_offsets[3], route_dir, route_dir2, True),
        self._findMinObstacle(bot_player, coord1[0], coord1[1], angle + ray_offsets[3], route_dir, route_dir2, True),
      ),
      self._findMinObstacle(bot_player, coord1[0], coord1[1], angle + ray_offsets[4], route_dir, route_dir2, True),
      self._findMinObstacle(bot_player, coord1[0], coord1[1], angle + ray_offsets[5], route_dir, route_dir2, True),
      self._findMinObstacle(bot_player, coord1[0], coord1[1], angle + ray_offsets[6], route_dir, route_dir2, True),
    ]

    best_idx = 3
    best_score = -99999
    for i in range(7):
      # Extra road guard: keep the center ray preferred unless a turn is clearly safer.
      score = minLine[i]
      if i == 3:
        score += 80
      if route_dir is not None:
        ray_dir = (-math.cos(angle + ray_offsets[i]), -math.sin(angle + ray_offsets[i]))
        route_score = max(0.0, ray_dir[0] * route_dir[0] + ray_dir[1] * route_dir[1])
        score += route_score * (220 if track_name == "city" else 180)
      if route_dir2 is not None:
        ray_dir = (-math.cos(angle + ray_offsets[i]), -math.sin(angle + ray_offsets[i]))
        route_score2 = max(0.0, ray_dir[0] * route_dir2[0] + ray_dir[1] * route_dir2[1])
        score += route_score2 * 120
      if score > best_score:
        best_score = score
        best_idx = i

    # If we're offroad in forest, trust road recovery a bit more than route chasing.
    if offroad and track_name == "forest":
      best_idx = self._best_road_idx(minLine)

    bot_player.keyAccelPressed = 1
    bot_player.keyBrakePressed = 0
    if best_idx in (0, 1, 2):
      bot_player.keyLeftPressed = 1
      bot_player.keyRightPressed = 0
    elif best_idx in (4, 5, 6):
      bot_player.keyLeftPressed = 0
      bot_player.keyRightPressed = 1
    else:
      bot_player.keyLeftPressed = 0
      bot_player.keyRightPressed = 0

    if offroad:
      if car.speed > 0.8:
        bot_player.keyBrakePressed = 1
        bot_player.keyAccelPressed = 0
      else:
        bot_player.keyBrakePressed = 0
    else:
      if aggressive:
        if car.speed > car.maxSpeed * 0.86:
          bot_player.keyBrakePressed = 1
          bot_player.keyAccelPressed = 0
      else:
        if car.speed > car.maxSpeed * 0.78:
          bot_player.keyBrakePressed = 1
          bot_player.keyAccelPressed = 0

    if bot_player.keyAccelPressed == 1:
      car.doAccel()
    else:
      car.noAccel()
    if bot_player.keyBrakePressed == 1:
      car.doBrake()
    else:
      car.noBrake()
    if bot_player.keyLeftPressed == 1:
      car.doLeft()
    if bot_player.keyRightPressed == 1:
      car.doRight()
    if bot_player.keyLeftPressed == 0 and bot_player.keyRightPressed == 0:
      car.noWheel()

  def _best_road_idx(self, minLine):
    best_idx = 3
    best_val = minLine[3]
    for i, val in enumerate(minLine):
      if val > best_val:
        best_val = val
        best_idx = i
    return best_idx

  def _apply_planner_control(self, bot_player, planner):
    car = bot_player.car
    near = planner["near"]
    far = planner["far"]
    curvature = planner["curvature"]
    confidence = planner.get("confidence", 1.0)

    # Blend near and far targets so steering is anticipatory, not twitchy.
    target = (near[0] * 0.7 + far[0] * 0.3, near[1] * 0.7 + far[1] * 0.3)
    steer_dir = self._route_turn_dir(car, target)

    # Dynamic steering deadzone: less twitch at high speed.
    speed_ratio = 0.0
    if car.maxSpeed > 1e-6:
      speed_ratio = max(0.0, min(1.0, car.speed / car.maxSpeed))
    steer_deadzone = 0.03 + 0.07 * speed_ratio

    bot_player.keyLeftPressed = 1 if steer_dir < -steer_deadzone else 0
    bot_player.keyRightPressed = 1 if steer_dir > steer_deadzone else 0

    # Corner speed control from steering demand + curvature estimate.
    turn_factor = max(0.0, min(1.0, abs(steer_dir) * 2.0 + curvature * 1.6))
    target_speed_ratio = max(0.20, (0.68 - 0.50 * turn_factor) * (0.70 + 0.30 * confidence))
    target_speed = car.maxSpeed * target_speed_ratio

    # Progressive accel/brake decisions, biased toward slower, cleaner corner entry.
    if car.speed > target_speed + 0.14:
      bot_player.keyAccelPressed = 0
      bot_player.keyBrakePressed = 1
    elif car.speed < target_speed - 0.20:
      bot_player.keyAccelPressed = 1
      bot_player.keyBrakePressed = 0
    else:
      bot_player.keyAccelPressed = 1 if car.speed < car.maxSpeed * 0.74 else 0
      bot_player.keyBrakePressed = 0

  def _checkpoint_id_from_pixel(self, pix):
    """Return checkpoint ID for canonical checkpoint marker pixels only."""
    r = int(pix[0])
    if r <= 0 or r % 16 != 0:
      return None
    return r

  def _next_prev_checkpoint(self, last_cp, reverse):
    # Checkpoint IDs are 16..192 in steps of 16.
    if reverse == 0:
      next_cp = last_cp + 16
      prev_cp = last_cp - 16
      if next_cp > 192:
        next_cp = 16
      if prev_cp < 16:
        prev_cp = 192
    else:
      next_cp = last_cp - 16
      prev_cp = last_cp + 16
      if next_cp < 16:
        next_cp = 192
      if prev_cp > 192:
        prev_cp = 16
    return next_cp, prev_cp
