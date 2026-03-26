from .ai_behavior import BehaviorSystem
from .ai_boids import BoidsEngine
from .ai_controller import AIController
from .ai_controller import CommandApplier
from .ai_debug import AIDebugOverlay
from .ai_debug import AIDecisionLogger
from .ai_perception import PerceptionSystem
from .ai_track_model import TrackModelCache
from .ai_tuning import get_profile
from .ai_types import BotRuntimeState


class BoidsAIRuntime:
  """Composition root for the new AI architecture.

  Keeps subsystems together so RobotPlayer integration is minimal.
  """

  def __init__(self, level):
    self.profile = get_profile(level)
    self.runtime_state = BotRuntimeState(boid_weights=self.profile.weights)
    self.track_cache = TrackModelCache()
    self.perception = PerceptionSystem()
    self.behavior = BehaviorSystem()
    self.boids = BoidsEngine()
    self.controller = AIController()
    self.applier = CommandApplier()
    self.debug_overlay = AIDebugOverlay()
    self.logger = AIDecisionLogger()

  def step(self, bot_player, all_players):
    track_model = self.track_cache.get_for_track(bot_player.car.track)
    snapshot = self.perception.build_snapshot(bot_player, all_players, track_model, self.profile)
    self.runtime_state.recent_progress = abs(bot_player.car.speed)

    self.behavior.update_state(self.runtime_state, snapshot, self.profile)
    forces = self.boids.compute_forces(snapshot, self.runtime_state, self.profile)
    command = self.controller.command_from_forces(bot_player, snapshot, forces, self.runtime_state, self.profile)

    self.applier.apply(bot_player, command)
    self.logger.log_frame(bot_player, snapshot, forces, command, self.runtime_state)

    return snapshot, forces, command, self.runtime_state
