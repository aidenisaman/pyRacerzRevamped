from .ai_types import BoidForces
import math


def _v_add(a, b):
  return (a[0] + b[0], a[1] + b[1])


def _v_scale(v, s):
  return (v[0] * s, v[1] * s)


def _v_len(v):
  return math.sqrt(v[0] * v[0] + v[1] * v[1])


def _v_norm(v):
  n = _v_len(v)
  if n <= 1e-9:
    return (0.0, 0.0)
  return (v[0] / n, v[1] / n)


class BoidsEngine:
  """Simplified force computation: just track_seek + wall_avoid.

  No state-dependent weight modifications. The weights from the profile
  are used directly. With social forces zeroed out, this is effectively
  just: total = normalize(track_seek * 5.0 + wall_avoid * 3.5)
  """

  def compute_forces(self, snapshot, runtime_state, profile):
    w = runtime_state.boid_weights

    trk = _v_scale(snapshot.track_seek_vector, w.track_seek)
    wal = _v_scale(snapshot.wall_avoid_vector, w.wall_avoid)

    total = _v_add(trk, wal)
    total = _v_norm(total)

    # Social forces are kept at zero but we still return them for the dataclass.
    zero = (0.0, 0.0)

    return BoidForces(
      separation=zero,
      alignment=zero,
      cohesion=zero,
      track_seek=trk,
      wall_avoid=wal,
      total=total,
    )
