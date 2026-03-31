import os


class AIDebugOverlay:
  """Hook for optional AI overlays.

  Rendering is intentionally no-op in this pass to avoid touching the current
  draw pipeline; the hook keeps the architecture stable for future overlays.
  """

  def draw(self, screen, bot_player, snapshot, forces, runtime_state):
    return


class AIDecisionLogger:
  """Optional text logger for frame-level AI decisions."""

  def __init__(self):
    self._enabled = os.environ.get("PYRACERZ_AI_LOG", "0") == "1"

  def log_frame(self, bot_player, snapshot, forces, command, runtime_state):
    if not self._enabled:
      return
    # Keep one-line log entries for easy grep while tuning.
    print(
      "AI[%s] state=%s hdg=%.3f lat=%.2f wall=%.1f n=%d thr=%.2f brk=%.2f str=%.2f"
      % (
        bot_player.name,
        runtime_state.state.value,
        snapshot.heading_error,
        snapshot.lateral_error,
        snapshot.distance_to_wall_ahead,
        snapshot.neighbors_in_radius,
        command.throttle,
        command.brake,
        command.steer,
      )
    )
    return
