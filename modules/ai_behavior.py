from .ai_types import BehaviorState


class BehaviorSystem:
  def update_state(self, runtime_state, snapshot, profile):
    runtime_state.state_timer_frames += 1

    # Basic collision risk estimate from distance and wall proximity.
    distance_risk = 0.0
    if snapshot.nearest_opponent_distance < 50.0:
      distance_risk = 1.0
    elif snapshot.nearest_opponent_distance < 100.0:
      distance_risk = 0.5

    wall_risk = 0.0
    if snapshot.distance_to_wall_ahead < 40.0:
      wall_risk = 1.0
    elif snapshot.distance_to_wall_ahead < 80.0:
      wall_risk = 0.5

    runtime_state.collision_risk = max(distance_risk, wall_risk)

    # Stuck detection is intentionally simple in phase 1.
    if runtime_state.recent_progress < profile.recover_progress_threshold:
      runtime_state.stuck_counter += 1
    else:
      runtime_state.stuck_counter = 0

    if runtime_state.stuck_counter > profile.recover_frames_threshold:
      runtime_state.state = BehaviorState.RECOVER
      runtime_state.state_timer_frames = 0
      return runtime_state.state

    if runtime_state.collision_risk >= 1.0:
      runtime_state.state = BehaviorState.AVOID_COLLISION
      runtime_state.state_timer_frames = 0
      return runtime_state.state

    if snapshot.neighbors_in_radius > 0 and snapshot.nearest_opponent_distance < 90.0:
      runtime_state.state = BehaviorState.OVERTAKE_BIAS
      return runtime_state.state

    runtime_state.state = BehaviorState.CRUISE
    return runtime_state.state
