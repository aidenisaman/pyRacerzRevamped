import math

from .ai_types import PerceptionSnapshot


def _v_sub(a, b):
  return (a[0] - b[0], a[1] - b[1])


def _v_len(v):
  return math.sqrt(v[0] * v[0] + v[1] * v[1])


def _v_norm(v):
  length = _v_len(v)
  if length <= 1e-9:
    return (0.0, 0.0)
  return (v[0] / length, v[1] / length)


def _v_add(a, b):
  return (a[0] + b[0], a[1] + b[1])


def _v_scale(v, s):
  return (v[0] * s, v[1] * s)


class PerceptionSystem:
  def build_snapshot(self, bot_player, all_players, track_model, profile):
    car = bot_player.car
    pos = (float(car.x), float(car.y))
    forward = (math.cos(car.angle), math.sin(car.angle))

    neighbor_radius = max(profile.neighbor_radius, 1.0)
    nearest = 99999.0
    neighbors = []

    sum_sep = (0.0, 0.0)
    sum_align = (0.0, 0.0)
    sum_cohesion_pos = (0.0, 0.0)

    for other in all_players:
      if other is bot_player:
        continue
      ocar = other.car
      o_pos = (float(ocar.x), float(ocar.y))
      delta = _v_sub(o_pos, pos)
      dist = _v_len(delta)
      if dist < nearest:
        nearest = dist
      if dist <= neighbor_radius and dist > 1e-6:
        neighbors.append(other)

        # Separation points away from nearby cars.
        sep_dir = _v_norm(_v_scale(delta, -1.0))
        sep_gain = (neighbor_radius - dist) / neighbor_radius
        sum_sep = _v_add(sum_sep, _v_scale(sep_dir, sep_gain))

        # Alignment uses other car heading.
        sum_align = _v_add(sum_align, (math.cos(ocar.angle), math.sin(ocar.angle)))

        # Cohesion uses neighbor positions.
        sum_cohesion_pos = _v_add(sum_cohesion_pos, o_pos)

    if neighbors:
      n = float(len(neighbors))
      alignment = _v_norm(_v_scale(sum_align, 1.0 / n))
      center = _v_scale(sum_cohesion_pos, 1.0 / n)
      cohesion = _v_norm(_v_sub(center, pos))
      separation = _v_norm(sum_sep)
    else:
      alignment = forward
      cohesion = (0.0, 0.0)
      separation = (0.0, 0.0)

    target = None
    if track_model.samples:
      idx = min(bot_player.ai_runtime.target_segment_index, len(track_model.samples) - 1)
      target = track_model.samples[idx]

    if target is None:
      track_seek = forward
      heading_error = 0.0
      lateral_error = 0.0
      curvature = 0.0
    else:
      to_target = _v_sub((target.x, target.y), pos)
      track_seek = _v_norm(to_target)
      target_heading = math.atan2(track_seek[1], track_seek[0])
      heading_error = _angle_diff(target_heading, car.angle)
      lateral_error = _v_len(to_target)
      curvature = target.curvature

    wall_avoid = _estimate_wall_avoid(bot_player)
    wall_dist = _estimate_wall_distance(bot_player)
    offroad_ratio = _estimate_offroad_ratio(bot_player)

    return PerceptionSnapshot(
      heading_error=heading_error,
      lateral_error=lateral_error,
      curvature_ahead=curvature,
      distance_to_wall_ahead=wall_dist,
      offroad_ratio_local=offroad_ratio,
      nearest_opponent_distance=nearest,
      opponent_relative_speed=0.0,
      neighbors_in_radius=len(neighbors),
      separation_vector=separation,
      alignment_vector=alignment,
      cohesion_vector=cohesion,
      track_seek_vector=track_seek,
      wall_avoid_vector=wall_avoid,
    )


def _estimate_wall_distance(bot_player):
  # Stub-friendly value: later this becomes proper ray sampling.
  # Keep output bounded so controller math is stable.
  return float(bot_player.findMinObstacle(int(bot_player.car.x), int(bot_player.car.y), bot_player.car.angle))


def _estimate_wall_avoid(bot_player):
  dist_left = bot_player.findMinObstacle(int(bot_player.car.x), int(bot_player.car.y), bot_player.car.angle - math.pi / 6.0)
  dist_right = bot_player.findMinObstacle(int(bot_player.car.x), int(bot_player.car.y), bot_player.car.angle + math.pi / 6.0)
  bias = float(dist_right - dist_left)
  # Positive bias means more free space on the right, so steer right.
  return _v_norm((-math.sin(bot_player.car.angle) * bias, math.cos(bot_player.car.angle) * bias))


def _estimate_offroad_ratio(bot_player):
  x = int(bot_player.car.x)
  y = int(bot_player.car.y)
  if x < 0 or y < 0:
    return 1.0
  try:
    pix = bot_player.car.track.trackF.get_at((x, y))
    return 0.0 if pix[1] == 255 else 1.0
  except Exception:
    return 1.0


def _angle_diff(a, b):
  d = a - b
  while d > math.pi:
    d -= 2.0 * math.pi
  while d < -math.pi:
    d += 2.0 * math.pi
  return d
