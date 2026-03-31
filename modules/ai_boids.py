from .ai_types import BoidForces
from .ai_types import BehaviorState
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
  def compute_forces(self, snapshot, runtime_state, profile):
    w = runtime_state.boid_weights
    sep_w = w.separation
    ali_w = w.alignment
    coh_w = w.cohesion
    trk_w = w.track_seek
    wal_w = w.wall_avoid

    if runtime_state.state == BehaviorState.AVOID_COLLISION:
      sep_w *= 1.9
      wal_w *= 1.6
      trk_w *= 0.8
      coh_w *= 0.3
    elif runtime_state.state == BehaviorState.RECOVER:
      sep_w *= 1.2
      ali_w *= 0.2
      coh_w *= 0.0
      trk_w *= 2.4
      wal_w *= 2.2
    elif runtime_state.state == BehaviorState.OVERTAKE_BIAS:
      trk_w *= 1.25 + profile.overtake_bias_gain
      ali_w *= 1.15
      coh_w *= 0.6

    sep = _v_scale(snapshot.separation_vector, sep_w)
    ali = _v_scale(snapshot.alignment_vector, ali_w)
    coh = _v_scale(snapshot.cohesion_vector, coh_w)
    trk = _v_scale(snapshot.track_seek_vector, trk_w)
    wal = _v_scale(snapshot.wall_avoid_vector, wal_w)

    total = (0.0, 0.0)
    total = _v_add(total, sep)
    total = _v_add(total, ali)
    total = _v_add(total, coh)
    total = _v_add(total, trk)
    total = _v_add(total, wal)

    total = _v_norm(total)

    return BoidForces(
      separation=sep,
      alignment=ali,
      cohesion=coh,
      track_seek=trk,
      wall_avoid=wal,
      total=total,
    )
