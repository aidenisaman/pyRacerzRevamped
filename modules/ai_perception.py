import math

from .ai_types import PerceptionSnapshot
from .ai_types import BehaviorState


def _v_add(a, b):
  return (a[0] + b[0], a[1] + b[1])


def _v_sub(a, b):
  return (a[0] - b[0], a[1] - b[1])


def _v_scale(v, s):
  return (v[0] * s, v[1] * s)


def _v_dot(a, b):
  return a[0] * b[0] + a[1] * b[1]


def _v_len(v):
  return math.sqrt(v[0] * v[0] + v[1] * v[1])


def _v_norm(v):
  length = _v_len(v)
  if length <= 1e-9:
    return (0.0, 0.0)
  return (v[0] / length, v[1] / length)


def _angle_diff(a, b):
  d = a - b
  while d > math.pi:
    d -= 2.0 * math.pi
  while d < -math.pi:
    d += 2.0 * math.pi
  return d


class PerceptionSystem:
  def build_snapshot(self, bot_player, all_players, track_model, runtime_state, profile):
    car = bot_player.car
    pos = (float(car.x), float(car.y))
    heading = float(car.angle)
    forward = (math.cos(heading), math.sin(heading))

    nearest_idx = self._find_nearest_segment(track_model, pos)
    runtime_state.nearest_segment_index = nearest_idx

    lookahead = profile.lookahead_distance
    if runtime_state.state == BehaviorState.OVERTAKE_BIAS:
      lookahead = profile.overtake_lookahead_distance
    target_idx = self._advance_by_distance(track_model, nearest_idx, lookahead)
    runtime_state.target_segment_index = target_idx

    target = track_model.samples[target_idx]
    nearest_sample = track_model.samples[nearest_idx]

    to_target = _v_sub((target.x, target.y), pos)
    track_seek = _v_norm(to_target)
    target_heading = target.tangent

    tangent_vec = (math.cos(nearest_sample.tangent), math.sin(nearest_sample.tangent))
    normal_vec = (-tangent_vec[1], tangent_vec[0])
    offset_vec = _v_sub(pos, (nearest_sample.x, nearest_sample.y))

    heading_error = _angle_diff(target_heading, heading)
    lateral_error = _v_dot(offset_vec, normal_vec)

    neighborhood = self._gather_neighbors(bot_player, all_players, pos, forward, profile)

    wall_center = self._raycast_road_distance(bot_player, heading)
    wall_left = self._raycast_road_distance(bot_player, heading - math.pi / 5.0)
    wall_right = self._raycast_road_distance(bot_player, heading + math.pi / 5.0)

    wall_avoid = self._build_wall_avoid(forward, wall_left, wall_right, wall_center)
    offroad_ratio = self._estimate_offroad_ratio(bot_player, heading)

    return PerceptionSnapshot(
      heading_error=heading_error,
      lateral_error=lateral_error,
      curvature_ahead=target.curvature,
      distance_to_wall_ahead=wall_center,
      distance_to_wall_left=wall_left,
      distance_to_wall_right=wall_right,
      offroad_ratio_local=offroad_ratio,
      nearest_opponent_distance=neighborhood["nearest_any"],
      opponent_relative_speed=neighborhood["nearest_rel_speed"],
      nearest_opponent_ahead_distance=neighborhood["nearest_ahead"],
      nearest_opponent_ahead_speed_delta=neighborhood["ahead_rel_speed"],
      neighbors_in_radius=neighborhood["count"],
      separation_vector=neighborhood["separation"],
      alignment_vector=neighborhood["alignment"],
      cohesion_vector=neighborhood["cohesion"],
      track_seek_vector=track_seek,
      wall_avoid_vector=wall_avoid,
    )

  def _find_nearest_segment(self, track_model, pos):
    best_idx = 0
    best_d2 = 10e12
    for i, sample in enumerate(track_model.samples):
      dx = sample.x - pos[0]
      dy = sample.y - pos[1]
      d2 = dx * dx + dy * dy
      if d2 < best_d2:
        best_d2 = d2
        best_idx = i
    return best_idx

  def _advance_by_distance(self, track_model, start_idx, lookahead):
    samples = track_model.samples
    if not samples:
      return 0
    idx = start_idx
    dist = 0.0
    while dist < lookahead:
      nxt = (idx + 1) % len(samples)
      sx = samples[nxt].x - samples[idx].x
      sy = samples[nxt].y - samples[idx].y
      step = math.sqrt(sx * sx + sy * sy)
      dist += step
      idx = nxt
      if idx == start_idx:
        break
    return idx

  def _gather_neighbors(self, bot_player, all_players, pos, forward, profile):
    radius = max(profile.neighbor_radius, 1.0)
    cos_limit = math.cos(math.radians(profile.forward_cone_deg * 0.5))

    nearest_any = 99999.0
    nearest_rel_speed = 0.0
    nearest_ahead = 99999.0
    ahead_rel_speed = 0.0

    sum_sep = (0.0, 0.0)
    sum_align = (0.0, 0.0)
    sum_cohesion_pos = (0.0, 0.0)
    count = 0

    for other in all_players:
      if other is bot_player:
        continue
      ocar = other.car
      o_pos = (float(ocar.x), float(ocar.y))
      delta = _v_sub(o_pos, pos)
      dist = _v_len(delta)
      if dist <= 1e-6:
        continue
      if dist < nearest_any:
        nearest_any = dist
        nearest_rel_speed = float(ocar.speed - bot_player.car.speed)

      if dist > radius:
        continue

      dir_to_other = _v_scale(delta, 1.0 / dist)
      in_front = _v_dot(forward, dir_to_other) >= cos_limit
      if not in_front:
        continue

      count += 1

      if dist < nearest_ahead:
        nearest_ahead = dist
        ahead_rel_speed = float(ocar.speed - bot_player.car.speed)

      sep_gain = (radius - dist) / radius
      sum_sep = _v_add(sum_sep, _v_scale(dir_to_other, -sep_gain))
      sum_align = _v_add(sum_align, (math.cos(ocar.angle), math.sin(ocar.angle)))
      sum_cohesion_pos = _v_add(sum_cohesion_pos, o_pos)

    if count > 0:
      inv = 1.0 / float(count)
      alignment = _v_norm(_v_scale(sum_align, inv))
      center = _v_scale(sum_cohesion_pos, inv)
      cohesion = _v_norm(_v_sub(center, pos))
      separation = _v_norm(sum_sep)
    else:
      alignment = forward
      cohesion = (0.0, 0.0)
      separation = (0.0, 0.0)

    return {
      "count": count,
      "separation": separation,
      "alignment": alignment,
      "cohesion": cohesion,
      "nearest_any": nearest_any,
      "nearest_rel_speed": nearest_rel_speed,
      "nearest_ahead": nearest_ahead,
      "ahead_rel_speed": ahead_rel_speed,
    }

  def _raycast_road_distance(self, bot_player, angle):
    x = float(bot_player.car.x)
    y = float(bot_player.car.y)
    track_f = bot_player.car.track.trackF
    width = track_f.get_width()
    height = track_f.get_height()
    dist = 0.0

    while dist < 600.0:
      step = 2.0 if dist < 40.0 else 6.0
      x -= math.cos(angle) * step
      y -= math.sin(angle) * step
      dist += step
      ix = int(x)
      iy = int(y)
      if ix < 1 or iy < 1 or ix >= width - 1 or iy >= height - 1:
        return dist
      if track_f.get_at((ix, iy))[1] != 255:
        return dist
    return dist

  def _build_wall_avoid(self, forward, left_dist, right_dist, center_dist):
    side_bias = (right_dist - left_dist)
    side_vec = (-forward[1], forward[0])
    side_term = _v_scale(side_vec, side_bias / max(left_dist + right_dist, 1.0))

    center_penalty = 0.0
    if center_dist < 110.0:
      center_penalty = (110.0 - center_dist) / 110.0

    back_term = _v_scale(forward, -center_penalty)
    return _v_norm(_v_add(side_term, back_term))

  def _estimate_offroad_ratio(self, bot_player, heading):
    track_f = bot_player.car.track.trackF
    width = track_f.get_width()
    height = track_f.get_height()

    pos = (float(bot_player.car.x), float(bot_player.car.y))
    fwd = (math.cos(heading), math.sin(heading))
    side = (-fwd[1], fwd[0])

    probes = [
      pos,
      _v_add(pos, _v_scale(fwd, 12.0)),
      _v_add(pos, _v_scale(fwd, -12.0)),
      _v_add(pos, _v_scale(side, 8.0)),
      _v_add(pos, _v_scale(side, -8.0)),
    ]

    bad = 0
    for p in probes:
      ix = int(p[0])
      iy = int(p[1])
      if ix < 1 or iy < 1 or ix >= width - 1 or iy >= height - 1:
        bad += 1
      elif track_f.get_at((ix, iy))[1] != 255:
        bad += 1

    return float(bad) / float(len(probes))
