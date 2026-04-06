import math
import os

from .ai_types import PerceptionSnapshot
from .ai_types import BehaviorState
from . import misc


class PerceptionSystem:
  """Navigation using the legacy AI's proven raycast approach.

  This is a direct port of RobotPlayer.compute() — the legacy AI that
  works on ALL tracks including city.

  Instead of aiming at checkpoint centroids (which goes through buildings
  on grid layouts), we raycast in 7 directions and score each by:
  1. Road distance (how far until hitting non-road)
  2. +200 bonus if the ray crosses the NEXT checkpoint line
  3. -100 penalty if the ray crosses the PREVIOUS checkpoint line

  The checkpoint lines are thin yellow markers embedded in the road
  surface. The raycasts detect them and naturally guide the bot to
  the correct road at intersections and over bridges/underpasses.
  """

  def build_snapshot(self, bot_player, all_players, track_model, runtime_state, profile):
    car = bot_player.car
    pos = (float(car.x), float(car.y))
    heading = float(car.angle)
    forward = (-math.cos(heading), -math.sin(heading))

    # Keep segment progress synced with game checkpoint state first.
    self._update_checkpoint(bot_player, track_model, runtime_state, pos)

    # === FLOW FIELD NAVIGATION (PRIMARY) ===
    flow_fields = getattr(track_model, "segment_flow_fields", {})
    cp_ids = getattr(track_model, "checkpoint_ids", [])
    if cp_ids:
      runtime_state.target_segment_index %= len(cp_ids)
    seg_idx = int(getattr(runtime_state, "target_segment_index", 0))
    flow = flow_fields.get(seg_idx, {})

    if flow:
      track_seek, heading_error = self._flow_field_steering(bot_player, car, pos, heading, flow, track_model)
    else:
      # Legacy fallback for tracks/runtime states without segment flow fields.
      best_idx, _ = self._legacy_raycast(bot_player)
      angle_offsets = [
        -math.pi / 4.0,
        -2.0 * math.pi / 5.0,
        -math.pi / 5.0,
        0.0,
        math.pi / 5.0,
        2.0 * math.pi / 5.0,
        math.pi / 4.0,
      ]
      heading_error = angle_offsets[best_idx]
      best_angle = heading + heading_error
      track_seek = (-math.cos(best_angle), -math.sin(best_angle))

    # Wall distance from center ray
    _, scores = self._legacy_raycast(bot_player)
    wall_center = max(scores[3], 0.0) if scores[3] > 0 else 5.0
    wall_left = max(scores[2], 0.0) if scores[2] > 0 else 5.0
    wall_right = max(scores[4], 0.0) if scores[4] > 0 else 5.0

    offroad_ratio = self._estimate_offroad_ratio(bot_player, heading)

    zero = (0.0, 0.0)

    return PerceptionSnapshot(
      heading_error=heading_error,
      lateral_error=0.0,
      curvature_ahead=abs(heading_error) * 0.01,
      distance_to_wall_ahead=wall_center,
      distance_to_wall_left=wall_left,
      distance_to_wall_right=wall_right,
      offroad_ratio_local=offroad_ratio,
      nearest_opponent_distance=99999.0,
      opponent_relative_speed=0.0,
      nearest_opponent_ahead_distance=99999.0,
      nearest_opponent_ahead_speed_delta=0.0,
      neighbors_in_radius=0,
      separation_vector=zero,
      alignment_vector=forward,
      cohesion_vector=zero,
      track_seek_vector=track_seek,
      wall_avoid_vector=zero,  # Not needed — raycast handles steering
    )

  def _flow_field_steering(self, bot_player, car, pos, heading, flow, track_model):
    """Sample per-segment flow vectors and convert to heading error."""
    tile_size = max(1, int(getattr(track_model, "tile_size", 4)))
    tx = int(pos[0]) // tile_size
    ty = int(pos[1]) // tile_size

    vec = flow.get((tx, ty))
    if vec is None or (vec[0] == 0.0 and vec[1] == 0.0):
      for r in range(1, 5):
        found = None
        for dy in range(-r, r + 1):
          for dx in range(-r, r + 1):
            v = flow.get((tx + dx, ty + dy))
            if v is not None and (v[0] != 0.0 or v[1] != 0.0):
              found = v
              break
          if found is not None:
            break
        if found is not None:
          vec = found
          break

    if vec is None or (vec[0] == 0.0 and vec[1] == 0.0):
      best_idx, _ = self._legacy_raycast(bot_player)
      angle_offsets = [
        -math.pi / 4.0,
        -2.0 * math.pi / 5.0,
        -math.pi / 5.0,
        0.0,
        math.pi / 5.0,
        2.0 * math.pi / 5.0,
        math.pi / 4.0,
      ]
      he = angle_offsets[best_idx]
      best_angle = heading + he
      return (-math.cos(best_angle), -math.sin(best_angle)), he

    desired_angle = math.atan2(vec[1], vec[0])
    car_forward_atan2 = heading + math.pi
    heading_error = desired_angle - car_forward_atan2
    while heading_error > math.pi:
      heading_error -= 2.0 * math.pi
    while heading_error < -math.pi:
      heading_error += 2.0 * math.pi
    heading_error = max(-math.pi * 0.5, min(math.pi * 0.5, heading_error))

    return (float(vec[0]), float(vec[1])), heading_error

  def _update_checkpoint(self, bot_player, track_model, runtime_state, pos):
    """Advance target segment index using checkpoint ground truth when available."""
    ids = getattr(track_model, "checkpoint_ids", [])
    if not ids:
      return

    last_cp = int(getattr(bot_player, "lastCheckpoint", 0))

    # Temporary debug trace to verify checkpoint->segment mapping at runtime.
    if os.environ.get("PYRACERZ_AI_LOG") == "1":
      print(
        "last_cp=%s ids0=%s seg_idx=%s in_ids=%s"
        % (
          last_cp,
          ids[0] if ids else None,
          int(getattr(runtime_state, "target_segment_index", 0)),
          (last_cp in ids),
        )
      )

    if last_cp in ids:
      runtime_state.target_segment_index = ids.index(last_cp)
      return

    seg_idx = int(getattr(runtime_state, "target_segment_index", 0)) % len(ids)
    next_seg = (seg_idx + 1) % len(ids)
    next_cp_id = ids[next_seg]

    cp_tiles = track_model.checkpoint_tiles.get(next_cp_id, set())
    if not cp_tiles:
      return

    tile_size = max(1, int(getattr(track_model, "tile_size", 4)))
    tx = int(pos[0]) // tile_size
    ty = int(pos[1]) // tile_size
    if (tx, ty) in cp_tiles:
      runtime_state.target_segment_index = next_seg

  def _legacy_raycast(self, bot_player):
    """Direct port of legacy compute() raycast + scoring logic."""
    car = bot_player.car
    angle = car.angle

    # Compute car nose coordinates (exact same as legacy AI)
    cx = car.x - math.cos(angle) * car.height * 1.2 / 2
    cy = car.y - math.sin(angle) * car.height * 1.2 / 2
    coord0 = (int(cx - math.sin(angle) * car.width * 1.2 / 2),
              int(cy + math.cos(angle) * car.width * 1.2 / 2))
    coord1 = (int(cx + math.sin(angle) * car.width * 1.2 / 2),
              int(cy - math.cos(angle) * car.width * 1.2 / 2))

    track_f = car.track.trackF
    reverse = car.track.reverse
    last_cp = bot_player.lastCheckpoint

    # 7 rays — exact same angles and origin points as legacy AI
    scores = [
      self._score_ray(track_f, coord0[0], coord0[1], angle - math.pi / 4.0, reverse, last_cp),
      self._score_ray(track_f, coord0[0], coord0[1], angle - 2.0 * math.pi / 5.0, reverse, last_cp),
      self._score_ray(track_f, coord0[0], coord0[1], angle - math.pi / 5.0, reverse, last_cp),
      min(  # Center: take worst of both nose corners (legacy behavior)
        self._score_ray(track_f, coord0[0], coord0[1], angle, reverse, last_cp),
        self._score_ray(track_f, coord1[0], coord1[1], angle, reverse, last_cp),
      ),
      self._score_ray(track_f, coord1[0], coord1[1], angle + math.pi / 5.0, reverse, last_cp),
      self._score_ray(track_f, coord1[0], coord1[1], angle + 2.0 * math.pi / 5.0, reverse, last_cp),
      self._score_ray(track_f, coord1[0], coord1[1], angle + math.pi / 4.0, reverse, last_cp),
    ]

    # Find best direction
    best_idx = 3
    best_score = scores[3]
    for i in range(7):
      if scores[i] > best_score:
        best_score = scores[i]
        best_idx = i
    # Privilege straight ahead (legacy behavior)
    if best_score == scores[3]:
      best_idx = 3

    # If completely surrounded (all scores <= 0), find nearest road
    if best_score <= 0:
      road_scores = [
        self._score_find_road(track_f, coord0[0], coord0[1], angle - math.pi / 4.0, reverse, last_cp),
        self._score_find_road(track_f, coord0[0], coord0[1], angle - 2.0 * math.pi / 5.0, reverse, last_cp),
        self._score_find_road(track_f, coord0[0], coord0[1], angle - math.pi / 5.0, reverse, last_cp),
        self._score_find_road(track_f, int(car.x), int(car.y), angle, reverse, last_cp),
        self._score_find_road(track_f, coord1[0], coord1[1], angle + math.pi / 5.0, reverse, last_cp),
        self._score_find_road(track_f, coord1[0], coord1[1], angle + 2.0 * math.pi / 5.0, reverse, last_cp),
        self._score_find_road(track_f, coord1[0], coord1[1], angle + math.pi / 4.0, reverse, last_cp),
      ]
      min_road = 9999.0
      best_idx = 3
      for i in range(7):
        if road_scores[i] < min_road:
          min_road = road_scores[i]
          best_idx = i
      if min_road == road_scores[3]:
        best_idx = 3

    return best_idx, scores

  def _score_ray(self, track_f, x, y, angle, reverse, last_cp):
    """Direct port of legacy findMinObstacle."""
    dist = 0.0
    zoom = misc.zoom

    if x <= 10 or x >= 1014 * zoom or y <= 10 or y >= 758 * zoom:
      return dist

    pix = track_f.get_at((int(x), int(y)))

    while dist < 600.0 * zoom and pix[1] == 255:
      if dist < 10.0 * zoom:
        step = 1.0
      elif dist < 40.0 * zoom:
        step = 5.0 * zoom
      elif dist < 100.0 * zoom:
        step = 10.0 * zoom
      elif dist < 200.0 * zoom:
        step = 30.0 * zoom
      else:
        step = 60.0 * zoom

      x = x - math.cos(angle) * step
      y = y - math.sin(angle) * step
      dist = dist + step

      cp_hit = self._checkpoint_id_from_pixel(pix)
      if cp_hit is not None:
        next_cp, prev_cp = self._next_prev_checkpoint(last_cp, reverse)
        if cp_hit == next_cp:
          dist = dist + 200.0 * zoom
        elif cp_hit == prev_cp:
          dist = dist - 100.0 * zoom

      if x > 10 and x < 1014 * zoom and y > 10 and y < 758 * zoom:
        pix = track_f.get_at((int(x), int(y)))
      else:
        dist = dist - 100.0 * zoom
        break

    return dist

  def _score_find_road(self, track_f, x, y, angle, reverse, last_cp):
    """Direct port of legacy findMinRoad."""
    dist = 0.0
    zoom = misc.zoom

    if x <= 10 or x >= 1014 * zoom or y <= 10 or y >= 758 * zoom:
      return 9999.0

    pix = track_f.get_at((int(x), int(y)))

    while dist < 600.0 * zoom and pix[1] != 255:
      if dist < 10.0 * zoom:
        step = 1.0
      elif dist < 40.0 * zoom:
        step = 5.0 * zoom
      elif dist < 100.0 * zoom:
        step = 10.0 * zoom
      elif dist < 200.0 * zoom:
        step = 30.0 * zoom
      else:
        step = 60.0 * zoom

      x = x - math.cos(angle) * step
      y = y - math.sin(angle) * step
      dist = dist + step

      cp_hit = self._checkpoint_id_from_pixel(pix)
      if cp_hit is not None:
        next_cp, prev_cp = self._next_prev_checkpoint(last_cp, reverse)
        if cp_hit == next_cp:
          dist = dist - 400.0 * zoom
        elif cp_hit == prev_cp:
          dist = dist + 100.0 * zoom

      if x > 10 and x < 1014 * zoom and y > 10 and y < 758 * zoom:
        pix = track_f.get_at((int(x), int(y)))
      else:
        dist = dist + 1000.0 * zoom
        break

    return dist

  def _estimate_offroad_ratio(self, bot_player, heading):
    track_f = bot_player.car.track.trackF
    width = track_f.get_width()
    height = track_f.get_height()
    ix = int(bot_player.car.x)
    iy = int(bot_player.car.y)
    if ix < 1 or iy < 1 or ix >= width - 1 or iy >= height - 1:
      return 1.0
    if track_f.get_at((ix, iy))[1] != 255:
      return 1.0
    return 0.0

  def _checkpoint_id_from_pixel(self, pix):
    """Return checkpoint ID only for canonical checkpoint marker pixels.

    City track uses many non-checkpoint red shades on-road, so rounding
    red values to the nearest checkpoint ID creates false positives.
    """
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
