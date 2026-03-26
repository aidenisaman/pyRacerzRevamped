from .ai_types import BoidForces


def _v_add(a, b):
  return (a[0] + b[0], a[1] + b[1])


def _v_scale(v, s):
  return (v[0] * s, v[1] * s)


class BoidsEngine:
  def compute_forces(self, snapshot, runtime_state, profile):
    w = runtime_state.boid_weights

    sep = _v_scale(snapshot.separation_vector, w.separation)
    ali = _v_scale(snapshot.alignment_vector, w.alignment)
    coh = _v_scale(snapshot.cohesion_vector, w.cohesion)
    trk = _v_scale(snapshot.track_seek_vector, w.track_seek)
    wal = _v_scale(snapshot.wall_avoid_vector, w.wall_avoid)

    total = (0.0, 0.0)
    total = _v_add(total, sep)
    total = _v_add(total, ali)
    total = _v_add(total, coh)
    total = _v_add(total, trk)
    total = _v_add(total, wal)

    return BoidForces(
      separation=sep,
      alignment=ali,
      cohesion=coh,
      track_seek=trk,
      wall_avoid=wal,
      total=total,
    )
