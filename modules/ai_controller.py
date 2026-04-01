import math
#Slow down each command input to possibably help with strange descisions and getting lost/stuck.
from .ai_types import BehaviorState
from .ai_types import ControlCommand


def clamp(value, lo, hi):
  return max(lo, min(hi, value))


class AIController:
  def command_from_forces(self, bot_player, snapshot, forces, runtime_state, profile):
    car = bot_player.car
    total = forces.total

    desired_heading = math.atan2(total[1], total[0]) if (abs(total[0]) + abs(total[1])) > 1e-9 else car.angle
    steer_error = _angle_diff(desired_heading, car.angle)
    steer_raw = clamp(steer_error / (math.pi / 3.0), -profile.max_steer_aggression, profile.max_steer_aggression)

    # Smooth steering to avoid twitching.
    alpha = clamp(profile.reaction_smoothing, 0.0, 1.0)
    steer = runtime_state.smoothed_steer * alpha + steer_raw * (1.0 - alpha)
    runtime_state.smoothed_steer = steer

    target_speed = _target_speed(bot_player, snapshot, profile, runtime_state)
    speed_error = target_speed - car.speed

    if runtime_state.state == BehaviorState.RECOVER:
      # Reverse briefly if strongly off-road, else crawl forward while re-aligning.
      if snapshot.offroad_ratio_local > 0.55 and car.speed < 0.7:
        return ControlCommand(throttle=0.0, brake=1.0, steer=steer)
      return ControlCommand(throttle=0.35, brake=0.0, steer=steer)

    throttle = 0.0
    brake = 0.0
    if speed_error > 0.2:
      throttle = clamp(0.25 + speed_error * 0.22, 0.0, 1.0)
    elif speed_error < -0.2:
      brake = clamp(0.12 + (-speed_error) * 0.30, 0.0, 1.0)

    # Dense packs should brake slightly earlier.
    brake += clamp(snapshot.neighbors_in_radius * profile.crowding_brake_gain * 0.05, 0.0, 0.4)

    if runtime_state.state == BehaviorState.AVOID_COLLISION:
      brake = max(brake, 0.35)
      throttle *= 0.6
    elif runtime_state.state == BehaviorState.OVERTAKE_BIAS:
      throttle = min(1.0, throttle + 0.12)

    brake = clamp(brake, 0.0, 1.0)
    throttle = clamp(throttle, 0.0, 1.0)

    return ControlCommand(throttle=throttle, brake=brake, steer=steer)


class CommandApplier:
  def apply(self, bot_player, command):
    # Throttle / brake are mapped into binary legacy controls for now.
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

    if command.steer < -0.15:
      bot_player.car.doLeft()
      bot_player.keyLeftPressed = 1
      bot_player.keyRightPressed = 0
    elif command.steer > 0.15:
      bot_player.car.doRight()
      bot_player.keyRightPressed = 1
      bot_player.keyLeftPressed = 0
    else:
      bot_player.car.noWheel()
      bot_player.keyLeftPressed = 0
      bot_player.keyRightPressed = 0


def _target_speed(bot_player, snapshot, profile, runtime_state):
  speed_cap = bot_player.car.maxSpeed

  # Curvature and wall proximity reduce target speed.
  curvature_penalty = min(abs(snapshot.curvature_ahead) * 10.0, 0.55)
  wall_penalty = 0.0
  if snapshot.distance_to_wall_ahead < 100.0:
    wall_penalty = (100.0 - max(snapshot.distance_to_wall_ahead, 0.0)) / 100.0

  target = speed_cap * (1.0 - curvature_penalty * 0.7 - wall_penalty * 0.55)
  if snapshot.offroad_ratio_local > 0.0:
    target *= 0.75

  if runtime_state.state == BehaviorState.AVOID_COLLISION:
    target *= 0.75
  elif runtime_state.state == BehaviorState.RECOVER:
    target = min(target, max(0.7, speed_cap * 0.35))
  elif runtime_state.state == BehaviorState.OVERTAKE_BIAS:
    target = min(speed_cap, target * 1.08)

  return clamp(target, 0.6, speed_cap)


def _angle_diff(a, b):
  d = a - b
  while d > math.pi:
    d -= 2.0 * math.pi
  while d < -math.pi:
    d += 2.0 * math.pi
  return d
