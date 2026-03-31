from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple


Vector2 = Tuple[float, float]


class BehaviorState(Enum):
  CRUISE = "cruise"
  OVERTAKE_BIAS = "overtake_bias"
  AVOID_COLLISION = "avoid_collision"
  RECOVER = "recover"


@dataclass
class BoidWeights:
  separation: float
  alignment: float
  cohesion: float
  track_seek: float
  wall_avoid: float


@dataclass
class AIProfile:
  name: str
  neighbor_radius: float
  forward_cone_deg: float
  lookahead_distance: float
  overtake_lookahead_distance: float
  crowding_brake_gain: float
  reaction_smoothing: float
  recover_progress_threshold: float
  recover_frames_threshold: int
  min_state_frames: int
  collision_risk_enter: float
  collision_risk_exit: float
  overtake_bias_gain: float
  max_steer_aggression: float
  weights: BoidWeights


@dataclass
class BotRuntimeState:
  state: BehaviorState = BehaviorState.CRUISE
  state_timer_frames: int = 0
  target_segment_index: int = 0
  nearest_segment_index: int = 0
  stuck_counter: int = 0
  collision_risk: float = 0.0
  overtake_side: int = 0
  smoothed_throttle: float = 0.0
  smoothed_steer: float = 0.0
  boid_weights: BoidWeights = field(default_factory=lambda: BoidWeights(1.2, 0.8, 0.5, 1.8, 2.0))
  neighbor_ids_cached: List[int] = field(default_factory=list)
  recent_progress: float = 0.0
  frames_since_progress: int = 0


@dataclass
class PerceptionSnapshot:
  heading_error: float
  lateral_error: float
  curvature_ahead: float
  distance_to_wall_ahead: float
  distance_to_wall_left: float
  distance_to_wall_right: float
  offroad_ratio_local: float
  nearest_opponent_distance: float
  opponent_relative_speed: float
  nearest_opponent_ahead_distance: float
  nearest_opponent_ahead_speed_delta: float
  neighbors_in_radius: int
  separation_vector: Vector2
  alignment_vector: Vector2
  cohesion_vector: Vector2
  track_seek_vector: Vector2
  wall_avoid_vector: Vector2


@dataclass
class BoidForces:
  separation: Vector2
  alignment: Vector2
  cohesion: Vector2
  track_seek: Vector2
  wall_avoid: Vector2
  total: Vector2


@dataclass
class ControlCommand:
  throttle: float
  brake: float
  steer: float
