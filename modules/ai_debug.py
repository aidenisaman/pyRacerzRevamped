class AIDebugOverlay:
  """Phase-1 debug hook. No rendering until debug visuals are implemented."""

  def draw(self, screen, bot_player, snapshot, forces, runtime_state):
    return


class AIDecisionLogger:
  """Phase-1 logger hook. Can be swapped for file/structured logging later."""

  def log_frame(self, bot_player, snapshot, forces, command, runtime_state):
    return
