from dataclasses import dataclass
from typing import Dict, List, Tuple


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
    # Placeholder model: uses start positions as anchor samples.
    # Later phases should replace this with sampled centerline extraction.
    p1 = (float(getattr(track_obj, "startX1", 0.0)), float(getattr(track_obj, "startY1", 0.0)))
    p2 = (float(getattr(track_obj, "startX2", p1[0])), float(getattr(track_obj, "startY2", p1[1])))
    p3 = (float(getattr(track_obj, "startX3", p2[0])), float(getattr(track_obj, "startY3", p2[1])))

    samples = [
      TrackSample(x=p1[0], y=p1[1], tangent=float(getattr(track_obj, "startAngle", 0.0)), curvature=0.0, half_width=24.0),
      TrackSample(x=p2[0], y=p2[1], tangent=float(getattr(track_obj, "startAngle", 0.0)), curvature=0.0, half_width=24.0),
      TrackSample(x=p3[0], y=p3[1], tangent=float(getattr(track_obj, "startAngle", 0.0)), curvature=0.0, half_width=24.0),
    ]
    return TrackModel(samples=samples)
