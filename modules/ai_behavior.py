from .ai_types import BehaviorState


class BehaviorSystem:
  def update_state(self, runtime_state, snapshot, profile):
    runtime_state.state_timer_frames += 1

    distance_risk = 0.0
    if snapshot.nearest_opponent_ahead_distance < 30.0:
      distance_risk = 1.0
    elif snapshot.nearest_opponent_ahead_distance < 55.0:
      distance_risk = 0.75
    elif snapshot.nearest_opponent_ahead_distance < 95.0:
      distance_risk = 0.45

    wall_risk = 0.0
    if snapshot.distance_to_wall_ahead < 24.0:
      wall_risk = 1.0
    elif snapshot.distance_to_wall_ahead < 45.0:
      wall_risk = 0.8
    elif snapshot.distance_to_wall_ahead < 80.0:
      wall_risk = 0.45

    offroad_risk = min(1.0, snapshot.offroad_ratio_local * 1.2)
    runtime_state.collision_risk = max(distance_risk, wall_risk, offroad_risk)

    if runtime_state.recent_progress < profile.recover_progress_threshold:
      runtime_state.frames_since_progress += 1
      runtime_state.stuck_counter += 1
    else:
      runtime_state.frames_since_progress = 0
      runtime_state.stuck_counter = max(0, runtime_state.stuck_counter - 2)

    should_recover = (
      snapshot.offroad_ratio_local > 0.45
      or runtime_state.stuck_counter > profile.recover_frames_threshold
      or runtime_state.frames_since_progress > profile.recover_frames_threshold
    )

    if should_recover:
      return self._switch(runtime_state, BehaviorState.RECOVER)

    min_frames = profile.min_state_frames
    if runtime_state.state == BehaviorState.RECOVER:
      if runtime_state.state_timer_frames < min_frames:
        return runtime_state.state
      if snapshot.offroad_ratio_local < 0.15 and runtime_state.collision_risk < profile.collision_risk_exit:
        return self._switch(runtime_state, BehaviorState.CRUISE)
      return runtime_state.state

    if runtime_state.collision_risk >= profile.collision_risk_enter:
      return self._switch(runtime_state, BehaviorState.AVOID_COLLISION)

    if runtime_state.state == BehaviorState.AVOID_COLLISION:
      if runtime_state.state_timer_frames < min_frames:
        return runtime_state.state
      if runtime_state.collision_risk <= profile.collision_risk_exit:
        return self._switch(runtime_state, BehaviorState.CRUISE)
      return runtime_state.state

    slower_ahead = snapshot.nearest_opponent_ahead_speed_delta < -0.2
    close_ahead = snapshot.nearest_opponent_ahead_distance < profile.overtake_lookahead_distance
    if slower_ahead and close_ahead:
      return self._switch(runtime_state, BehaviorState.OVERTAKE_BIAS)

    if runtime_state.state == BehaviorState.OVERTAKE_BIAS:
      if runtime_state.state_timer_frames < min_frames:
        return runtime_state.state
      if (not close_ahead) or runtime_state.collision_risk > profile.collision_risk_enter:
        return self._switch(runtime_state, BehaviorState.CRUISE)
      return runtime_state.state

    return self._switch(runtime_state, BehaviorState.CRUISE)

  def _switch(self, runtime_state, new_state):
    if runtime_state.state != new_state:
      runtime_state.state = new_state
      runtime_state.state_timer_frames = 0
    return runtime_state.state
