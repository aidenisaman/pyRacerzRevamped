from .ai_types import AIProfile
from .ai_types import BoidWeights


_PROFILES = {
  1: AIProfile(
    name="easy",
    neighbor_radius=95.0,
    forward_cone_deg=140.0,
    lookahead_distance=75.0,
    crowding_brake_gain=0.20,
    reaction_smoothing=0.30,
    recover_progress_threshold=0.8,
    recover_frames_threshold=120,
    overtake_bias_gain=0.20,
    weights=BoidWeights(1.6, 0.5, 0.2, 1.4, 2.3),
  ),
  2: AIProfile(
    name="medium",
    neighbor_radius=120.0,
    forward_cone_deg=150.0,
    lookahead_distance=95.0,
    crowding_brake_gain=0.30,
    reaction_smoothing=0.22,
    recover_progress_threshold=1.0,
    recover_frames_threshold=110,
    overtake_bias_gain=0.35,
    weights=BoidWeights(1.4, 0.8, 0.4, 1.8, 2.0),
  ),
  3: AIProfile(
    name="hard",
    neighbor_radius=145.0,
    forward_cone_deg=160.0,
    lookahead_distance=120.0,
    crowding_brake_gain=0.35,
    reaction_smoothing=0.15,
    recover_progress_threshold=1.2,
    recover_frames_threshold=100,
    overtake_bias_gain=0.50,
    weights=BoidWeights(1.2, 1.1, 0.6, 2.1, 1.8),
  ),
}


def get_profile(level):
  if level not in _PROFILES:
    return _PROFILES[2]
  return _PROFILES[level]
