import math

from .ai_types import BehaviorState
from .ai_types import ControlCommand


def clamp(value, lo, hi):
  return max(lo, min(hi, value))


class AIController:
  """Simplified controller that ports the legacy AI's steering logic.

  The key difference from centroid targeting: steering is determined
  entirely by the raycast best direction (via heading_error), not by
  force mixing. The boids force total just carries the raycast result.
  """

  def command_from_forces(self, bot_player, snapshot, forces, runtime_state, profile):
    car = bot_player.car

    # RECOVER: reverse briefly then go forward.
    if runtime_state.state == BehaviorState.RECOVER:
      if runtime_state.recover_reverse_frames > 0:
        runtime_state.recover_reverse_frames -= 1
        # Reverse with slight random steering to unstick
        return ControlCommand(throttle=0.0, brake=0.95, steer=0.3)
      return ControlCommand(throttle=0.5, brake=0.0, steer=0.0)

    # heading_error carries the angular offset from the best raycast direction.
    # Negative = best road is to the left, positive = to the right.
    he = snapshot.heading_error

    # Determine wall distance from the best direction's score
    wall_ahead = snapshot.distance_to_wall_ahead

    # Speed-dependent wall braking (ported from legacy AI)
    speed = car.speed
    max_speed = car.maxSpeed
    speed_ratio = speed / max_speed if max_speed > 0 else 0

    # Wall limits depend on difficulty level
    level = car.level
    if level == 1:
      wall_limit_center = 300.0
      wall_limit_near = 400.0
    elif level == 2:
      wall_limit_center = 450.0
      wall_limit_near = 600.0
    else:
      wall_limit_center = 600.0
      wall_limit_near = 800.0

    # Steering based on the best ray direction
    steer = 0.0
    throttle = 0.0
    brake = 0.0

    # Which side is the best direction?
    # he < 0 = left is better, he > 0 = right is better, he ≈ 0 = straight
    abs_he = abs(he)

    if abs_he < 0.01:
      # Straight ahead is best — check if we need to center on road
      steer = 0.0
      throttle = 1.0

      # Road centering: if left and right wall distances differ a lot, steer to center
      if abs(snapshot.distance_to_wall_left - snapshot.distance_to_wall_right) > 100:
        if snapshot.distance_to_wall_left > snapshot.distance_to_wall_right:
          steer = -0.5  # Steer left (more room on left)
        else:
          steer = 0.5   # Steer right (more room on right)
    elif abs_he < math.pi / 5.0:
      # Slight turn needed
      throttle = 1.0
      steer = 0.8 if he > 0 else -0.8
    elif abs_he < 2.0 * math.pi / 5.0:
      # Moderate turn — reduce throttle
      throttle = 0.5
      steer = 0.9 if he > 0 else -0.9
    else:
      # Sharp turn — brake and steer hard
      throttle = 0.0
      steer = 1.0 if he > 0 else -1.0

    # Speed-dependent braking when approaching walls
    if speed > 0 and wall_ahead < 800:
      should_brake = False
      if abs_he < 0.01 and wall_ahead < wall_limit_center * speed_ratio:
        should_brake = True
      elif abs_he < math.pi / 5.0 and wall_ahead < wall_limit_near * speed_ratio:
        should_brake = True
      elif abs_he >= 2.0 * math.pi / 5.0:
        should_brake = True

      if should_brake:
        throttle = 0.0
        brake = 1.0

    # Never brake at very low speed (legacy behavior)
    if speed < 0.5:
      brake = 0.0

    # If moving backward outside recovery, push forward
    if speed < -0.20 and runtime_state.state != BehaviorState.RECOVER:
      throttle = 1.0
      brake = 0.0

    return ControlCommand(
      throttle=clamp(throttle, 0.0, 1.0),
      brake=clamp(brake, 0.0, 1.0),
      steer=clamp(steer, -1.0, 1.0),
    )


class CommandApplier:
  def apply(self, bot_player, command):
    if command.throttle > 0.1:
      bot_player.car.doAccel()
      bot_player.keyAccelPressed = 1
    else:
      bot_player.car.noAccel()
      bot_player.keyAccelPressed = 0

    if command.brake > 0.1:
      bot_player.car.doBrake()
      bot_player.keyBrakePressed = 1
    else:
      bot_player.car.noBrake()
      bot_player.keyBrakePressed = 0

    if command.steer < -0.28:
      bot_player.car.doLeft()
      bot_player.keyLeftPressed = 1
      bot_player.keyRightPressed = 0
    elif command.steer > 0.28:
      bot_player.car.doRight()
      bot_player.keyRightPressed = 1
      bot_player.keyLeftPressed = 0
    else:
      bot_player.car.noWheel()
      bot_player.keyLeftPressed = 0
      bot_player.keyRightPressed = 0
