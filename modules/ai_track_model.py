#Look into how checkpoints are stored and encoded as the AI in current state are messing up and getting lost and I belive this is where the mistakes are coming from.


from dataclasses import dataclass
from typing import Dict, List, Tuple
import math

from . import misc


Vector2 = Tuple[float, float]


@dataclass
class TrackSample:
  x: float
  y: float
  tangent: float
  curvature: float
  half_width: float


@dataclass
class TrackModel:
  samples: List[TrackSample]


class TrackModelCache:
  """Lazily builds and caches lightweight track samples.

  This is intentionally simple for phase 1 architecture scaffolding.
  """

  def __init__(self):
    self._cache: Dict[str, TrackModel] = {}

  def get_for_track(self, track_obj):
    key = self._track_key(track_obj)
    if key not in self._cache:
      self._cache[key] = self._build(track_obj)
    return self._cache[key]

  def _track_key(self, track_obj):
    reverse = getattr(track_obj, "reverse", 0)
    name = getattr(track_obj, "name", "unknown")
    return "%s:%s" % (name, reverse)

  def _build(self, track_obj):
    track_f = track_obj.trackF
    zoom = max(float(getattr(misc, "zoom", 1.0)), 1.0)

    start_center = (
      (float(getattr(track_obj, "startX1", 0.0)) + float(getattr(track_obj, "startX2", 0.0)) + float(getattr(track_obj, "startX3", 0.0))) / 3.0,
      (float(getattr(track_obj, "startY1", 0.0)) + float(getattr(track_obj, "startY2", 0.0)) + float(getattr(track_obj, "startY3", 0.0))) / 3.0,
    )

    checkpoints = self._extract_checkpoint_centroids(track_obj)
    control_points = [start_center]
    control_points.extend(checkpoints)

    if len(control_points) < 3:
      # Fallback when a track has malformed checkpoint data.
      control_points.append((float(getattr(track_obj, "startX2", start_center[0])), float(getattr(track_obj, "startY2", start_center[1]))))
      control_points.append((float(getattr(track_obj, "startX3", start_center[0])), float(getattr(track_obj, "startY3", start_center[1]))))

    spacing = max(20.0 * zoom, 20.0)
    dense_points = self._resample_loop(control_points, spacing)
    if len(dense_points) < 8:
      dense_points = control_points

    samples: List[TrackSample] = []
    for i in range(len(dense_points)):
      prev_p = dense_points[(i - 1) % len(dense_points)]
      cur_p = dense_points[i]
      next_p = dense_points[(i + 1) % len(dense_points)]

      tangent = math.atan2(next_p[1] - prev_p[1], next_p[0] - prev_p[0])
      curvature = self._curvature(prev_p, cur_p, next_p)
      half_width = self._estimate_half_width(track_f, cur_p, tangent, zoom)
      samples.append(TrackSample(x=cur_p[0], y=cur_p[1], tangent=tangent, curvature=curvature, half_width=half_width))

    return TrackModel(samples=samples)

  def _extract_checkpoint_centroids(self, track_obj):
    track_f = track_obj.trackF
    width = track_f.get_width()
    height = track_f.get_height()
    nb = int(getattr(track_obj, "nbCheckpoint", 0))

    order = [16 * i for i in range(1, nb + 1)]
    if getattr(track_obj, "reverse", 0) == 1:
      order.reverse()

    # Single-pass accumulation by checkpoint id value.
    sums = {}
    counts = {}
    for y in range(height):
      for x in range(width):
        r = track_f.get_at((x, y))[0]
        if r in order:
          if r not in sums:
            sums[r] = [0.0, 0.0]
            counts[r] = 0
          sums[r][0] += x
          sums[r][1] += y
          counts[r] += 1

    centroids = []
    for cp in order:
      if cp in counts and counts[cp] > 0:
        centroids.append((sums[cp][0] / counts[cp], sums[cp][1] / counts[cp]))
    return centroids

  def _resample_loop(self, points, spacing):
    if len(points) < 2:
      return points

    out = []
    for i in range(len(points)):
      a = points[i]
      b = points[(i + 1) % len(points)]
      dx = b[0] - a[0]
      dy = b[1] - a[1]
      seg_len = math.sqrt(dx * dx + dy * dy)
      steps = max(1, int(seg_len / spacing))
      for s in range(steps):
        t = float(s) / float(steps)
        out.append((a[0] + dx * t, a[1] + dy * t))
    return out

  def _curvature(self, prev_p, cur_p, next_p):
    a1 = math.atan2(cur_p[1] - prev_p[1], cur_p[0] - prev_p[0])
    a2 = math.atan2(next_p[1] - cur_p[1], next_p[0] - cur_p[0])
    da = _angle_diff(a2, a1)
    d = max(1.0, math.sqrt((next_p[0] - cur_p[0]) ** 2 + (next_p[1] - cur_p[1]) ** 2))
    return da / d

  def _estimate_half_width(self, track_f, point, tangent, zoom):
    normal = (-math.sin(tangent), math.cos(tangent))
    step = max(2.0 * zoom, 2.0)
    limit = 140.0 * max(zoom, 1.0)
    left = self._distance_until_nonroad(track_f, point, normal, step, limit)
    right = self._distance_until_nonroad(track_f, point, (-normal[0], -normal[1]), step, limit)
    half_width = max(12.0 * max(zoom, 1.0), min(left, right))
    return half_width

  def _distance_until_nonroad(self, track_f, point, direction, step, limit):
    width = track_f.get_width()
    height = track_f.get_height()
    dist = 0.0
    x = point[0]
    y = point[1]
    while dist < limit:
      x += direction[0] * step
      y += direction[1] * step
      dist += step
      ix = int(x)
      iy = int(y)
      if ix < 1 or iy < 1 or ix >= width - 1 or iy >= height - 1:
        break
      if track_f.get_at((ix, iy))[1] != 255:
        break
    return dist


def _angle_diff(a, b):
  d = a - b
  while d > math.pi:
    d -= 2.0 * math.pi
  while d < -math.pi:
    d += 2.0 * math.pi
  return d
