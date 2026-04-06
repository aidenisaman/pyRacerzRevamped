from .ai_types import AIProfile
from .ai_types import BoidWeights


_PROFILES = {
  1: AIProfile(
    name="easy",
    neighbor_radius=95.0,
    forward_cone_deg=140.0,
    lookahead_distance=75.0,
    overtake_lookahead_distance=110.0,
    crowding_brake_gain=0.0,
    reaction_smoothing=0.15,
    recover_progress_threshold=0.8,
    recover_frames_threshold=120,
    min_state_frames=16,
    collision_risk_enter=0.78,
    collision_risk_exit=0.58,
    overtake_bias_gain=0.0,
    max_steer_aggression=0.85,
    weights=BoidWeights(0.0, 0.0, 0.0, 5.0, 3.5),
  ),
  2: AIProfile(
    name="medium",
    neighbor_radius=120.0,
    forward_cone_deg=150.0,
    lookahead_distance=95.0,
    overtake_lookahead_distance=135.0,
    crowding_brake_gain=0.0,
    reaction_smoothing=0.12,
    recover_progress_threshold=1.0,
    recover_frames_threshold=110,
    min_state_frames=14,
    collision_risk_enter=0.72,
    collision_risk_exit=0.50,
    overtake_bias_gain=0.0,
    max_steer_aggression=0.90,
    weights=BoidWeights(0.0, 0.0, 0.0, 5.0, 3.5),
  ),
  3: AIProfile(
    name="hard",
    neighbor_radius=145.0,
    forward_cone_deg=160.0,
    lookahead_distance=120.0,
    overtake_lookahead_distance=170.0,
    crowding_brake_gain=0.0,
    reaction_smoothing=0.08,
    recover_progress_threshold=1.2,
    recover_frames_threshold=100,
    min_state_frames=12,
    collision_risk_enter=0.66,
    collision_risk_exit=0.45,
    overtake_bias_gain=0.0,
    max_steer_aggression=0.95,
    weights=BoidWeights(0.0, 0.0, 0.0, 5.0, 3.5),
  ),
}


def get_profile(level):
  if level not in _PROFILES:
    return _PROFILES[2]
  return _PROFILES[level]
