from .ai_types import BehaviorState


class BehaviorSystem:
  """Simplified behavior: only CRUISE and RECOVER.

  No AVOID_COLLISION (was causing bots to brake/panic near each other).
  No OVERTAKE_BIAS (not needed without social forces).
  Just drive toward checkpoints, and reverse briefly if truly stuck.
  """

  def update_state(self, runtime_state, snapshot, profile):
    runtime_state.state_timer_frames += 1

    # Track if genuinely stuck (speed near zero).
    if runtime_state.recent_progress < 0.15:
      runtime_state.frames_since_progress += 1
      runtime_state.stuck_counter += 1
    else:
      runtime_state.frames_since_progress = 0
      runtime_state.stuck_counter = max(0, runtime_state.stuck_counter - 3)

    # Only recover when truly stuck (not moving for ~1 second).
    should_recover = (
      runtime_state.stuck_counter > 60
      or runtime_state.frames_since_progress > 60
    )

    if should_recover and runtime_state.state != BehaviorState.RECOVER:
      return self._switch(runtime_state, BehaviorState.RECOVER)

    # Exit RECOVER once we're moving again.
    if runtime_state.state == BehaviorState.RECOVER:
      if runtime_state.state_timer_frames > 20 and runtime_state.recent_progress > 0.3:
        return self._switch(runtime_state, BehaviorState.CRUISE)
      return runtime_state.state

    # Default: CRUISE (just drive toward checkpoint).
    if runtime_state.state != BehaviorState.CRUISE:
      return self._switch(runtime_state, BehaviorState.CRUISE)
    return runtime_state.state

  def _switch(self, runtime_state, new_state):
    if runtime_state.state != new_state:
      runtime_state.state = new_state
      runtime_state.state_timer_frames = 0
      if new_state == BehaviorState.RECOVER:
        runtime_state.recover_reverse_frames = 12
      else:
        runtime_state.recover_reverse_frames = 0
    return runtime_state.state
