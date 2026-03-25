# AI Rework Design (Full Replacement)

## 1. Problem Statement
The current AI in `modules/player.py` (`RobotPlayer`) is fragile and hard to tune:
- Steering and braking are driven by a small set of ray checks and hardcoded thresholds.
- Recovery behavior is inconsistent when the bot leaves the road or gets stuck.
- Difficulty scaling is mostly threshold-based and can feel unfair or random.
- AI behavior is tightly coupled to low-level input flags (`keyAccelPressed`, `keyBrakePressed`, `keyLeftPressed`, `keyRightPressed`) rather than a clean decision model.
- There is little visibility into why an AI decision happened, making bug fixing slow.

Goal: replace the current AI with a deterministic, testable, data-driven architecture that improves race quality and player trust.

## 2. Player-Centered Design Goals
These goals drive every technical choice.

1. Fairness over "perfect" bots.
- Bots should make believable mistakes.
- Higher difficulty should increase consistency and pace, not cheating behavior.

2. Readable behavior.
- Players should be able to predict what a bot is trying to do (follow line, avoid crash, overtake).
- Sudden unexplained swerves should be minimized.

3. Stable challenge.
- Difficulty should feel consistent across all tracks.
- A "Medium" bot on one track should feel close to "Medium" elsewhere.

4. Respect player progression.
- Easy mode should help new players finish races.
- Hard mode should reward mastery without obvious rubber-banding abuse.

5. Fewer frustrating collisions.
- Bots should avoid reckless side-contact and pileups when possible.
- Recovery after collisions should be fast and believable.

## 3. Possible Cycle 3 Goals
- Replacing car physics in `modules/car.py`.
- Implementing machine learning or online training.
- Rewriting netcode for this phase.

## 4. High-Level Architecture
Introduce a layered AI pipeline and keep it separate from car physics.

### 4.1 New Modules
- `modules/ai_types.py`
  - Shared lightweight data containers for AI state and outputs.
- `modules/ai_track_model.py`
  - Precomputed track graph/segments, ideal path, width estimates, curvature, and checkpoint mapping.
- `modules/ai_perception.py`
  - Fast local world queries: road occupancy, wall distance, nearby cars, heading error to target segment.
- `modules/ai_planner.py`
  - Tactical intent state machine: FollowLine, Defend, Overtake, Recover, AvoidCollision.
- `modules/ai_controller.py`
  - Converts intent + perception into control commands (throttle, brake, steer target).
- `modules/ai_tuning.py`
  - Difficulty parameter presets and per-track normalization values.
- `modules/ai_debug.py`
  - Optional overlay/debug logging for AI decisions and confidence values.

### 4.2 Integration Surface
- Keep `RobotPlayer` class but convert it into a thin adapter.
- `RobotPlayer.update_controls()` becomes:
  1. Collect perception snapshot.
  2. Update planner state.
  3. Run controller.
  4. Apply output to car inputs.

This keeps existing game loop integration in `modules/game.py` intact and lowers migration risk.

## 5. Core Technical Decisions

## Decision A: Move from hardcoded ray heuristic to track-segment targeting
Rationale:
- The current AI mostly reacts to immediate obstacles and lacks a medium-horizon goal.
- Segment targeting provides smooth steering and fewer sudden corrections.

Implementation:
- Build a centerline path for each track from checkpoints + sampled road mask.
- Store path as ordered segments with:
  - position `(x, y)`
  - tangent angle
  - curvature estimate
  - local half-width estimate
- Each bot tracks `target_segment_index` and lookahead distance based on speed.

Player impact:
- Bots look intentional and race-like instead of jittery.

## Decision B: Deterministic finite state machine for tactical behavior
Rationale:
- State machines are debuggable and stable for arcade racing AI.

States:
- `FOLLOW_LINE`: default behavior.
- `OVERTAKE`: when slower car blocks and alternate line is safe.
- `DEFEND`: optional for high difficulty when player attempts pass.
- `AVOID_COLLISION`: temporary evasive state for imminent contact.
- `RECOVER`: rejoin track when off-road/stuck/spinning.

Rules:
- Explicit entry/exit conditions and cooldown timers.
- Minimum state dwell time to prevent rapid oscillation.

Player impact:
- Bots make understandable decisions and avoid erratic mode switching.

## Decision C: Difficulty = parameter sets, not hidden speed cheats
Rationale:
- Players perceive invisible cheating as unfair.

Difficulty parameters include:
- racing line offset variance
- lookahead distance
- brake aggressiveness
- overtake willingness
- reaction smoothing time
- recovery competency
- max tactical risk

Allowed/limited assists (if needed):
- Very small speed normalization on Easy only, capped and transparent in docs.

Player impact:
- Harder bots feel smarter, not magically faster.

## Decision D: Explicit stuck detection and recovery protocol
Rationale:
- Getting stuck is currently one of the most visible AI failures.

Triggers:
- Low forward progress over time window.
- Repeated wall contacts.
- Heading error too large for sustained duration.

Recovery actions:
- Reverse-and-turn routine with timeout.
- Reacquire nearest valid segment by projection.
- Temporary reduced throttle until stable heading regained.

Player impact:
- Less race disruption and fewer broken races.

## Decision E: Performance budget with bounded perception costs
Rationale:
- AI should not create frame spikes, especially with many bots.

Constraints:
- Fixed maximum queries per bot per frame.
- Cache reusable map reads for nearby bots.
- Optional reduced update rate for tactical planner (for example 15 Hz) while keeping low-level controller per frame.

Player impact:
- Smoother frame pacing during full-grid races.

## 6. Data Model

### 6.1 Per-Bot Runtime State (`BotRuntimeState`)
- `state`: tactical FSM state
- `state_timer_frames`
- `target_segment_index`
- `stuck_counter`
- `collision_risk`
- `overtake_side` (left/right/none)
- `smoothed_throttle`
- `smoothed_steer`

### 6.2 Perception Snapshot (`PerceptionSnapshot`)
- `distance_to_left_boundary`
- `distance_to_right_boundary`
- `distance_to_wall_ahead`
- `heading_error`
- `lateral_error`
- `curvature_ahead`
- `nearest_opponent_distance`
- `opponent_relative_speed`
- `offroad_ratio_local`

### 6.3 Controller Output (`ControlCommand`)
- `throttle` in `[0, 1]`
- `brake` in `[0, 1]`
- `steer` in `[-1, 1]`

Adapter layer maps command to existing car API (`doAccel`, `noAccel`, `doBrake`, `noBrake`, `doLeft`, `doRight`, `noWheel`).

## 7. Planner and Controller Details

### 7.1 Target Selection
- Project car position onto nearest path segment.
- Compute speed-based lookahead index:
  - higher speed -> farther target
  - high curvature ahead -> shorten lookahead
- Use lateral offset policy for variation/overtake behavior.

### 7.2 Steering Control
- Use combined heading + lateral error control with damping:
  - `steer_raw = k_heading * heading_error + k_lateral * lateral_error`
- Clamp and smooth to reduce twitching.
- If imminent collision risk is high, blend in evasive steer component.

### 7.3 Throttle/Brake Control
- Determine target speed from curvature and local safety margins.
- If `current_speed > target_speed + margin` then brake.
- If under target and stable, apply throttle.
- Add traction-safe throttle reduction when off-road or at high steering angle.

### 7.4 Opponent Interaction
- Detect slower car ahead in lane corridor.
- Evaluate side corridors for overtake safety and wall risk.
- Commit to overtake side briefly to avoid indecision wobble.
- Abort overtake if corridor closes.

## 8. Observability and Debuggability

## Decision F: Build AI debug overlays and structured logs from day one
Rationale:
- AI bugs are easier to fix when decisions are visible.

Debug features (toggle in config):
- Draw target segment and lookahead point.
- Draw lane corridors and wall risk rays.
- Render current FSM state above bot.
- Optional per-bot trace lines in log:
  - frame, state, heading_error, target_speed, throttle, brake, steer, reason codes.

Player impact:
- Faster fixes means fewer long-lived AI frustration points.
-Can be removed easily once testing is done

## 9. Rollout Plan

### Phase 1: Foundation
- Add new AI modules and type definitions.
- Build track model loader and caches.
- Add adapter in `RobotPlayer` without behavior switch.

Exit criteria:
- No gameplay changes yet; all modules import cleanly.

### Phase 2: Baseline Driving
- Implement FollowLine planner + controller.
- Replace old `compute()` path for bots behind a feature flag.

Exit criteria:
- Bots can complete laps on all stock tracks without major stalls.

### Phase 3: Recovery and Collision Avoidance
- Add stuck detection and recovery state.
- Add avoid-collision behavior and safe braking refinements.

Exit criteria:
- Stuck incidents and wall spam substantially reduced.

### Phase 4: Overtake and Difficulty Tuning
- Add overtake state and side-commit logic.
- Finalize difficulty presets with per-track normalization.

Exit criteria:
- Difficulty progression feels fair and consistent in playtests.

### Phase 5: Polish and Defaults
- Enable debug toggles for dev builds.
- Make new AI default; keep fallback flag for one release cycle.

Exit criteria:
- New AI is stable enough to ship by default.

## 10. Success Metrics
The rework is successful if we achieve:
- 99%+ lap completion for bots in standard races.
- Significant reduction in stuck events compared to current AI baseline.
- Lower collision spam at race start and in tight corners.

## 11. Risks and Mitigations

Risk: Track model generation fails on unusual track masks.
Mitigation: Fallback to simplified centerline extraction and warn in log.

Risk: Overtake logic causes weaving.
Mitigation: Add side-commit timer and overtake cooldown.

Risk: Performance drops with many bots.
Mitigation: Perception query budgets and planner decimation.

Risk: Behavior regressions during migration.
Mitigation: Feature flag (`use_new_ai`) and one-cycle fallback path.

## 12. Backward Compatibility and Config
- Keep `RobotPlayer` public surface unchanged.
- Add optional config fields with sane defaults:
  - `use_new_ai`
  - `ai_debug_overlay`
  - `ai_log_decisions`
  - `ai_difficulty_profile`

If new fields are absent, defaults preserve current user experience while allowing controlled rollout.

## 13. Open Technical Questions
- Should defend behavior be enabled only on Hard to avoid frustrating casual players?
- Should overtake aggressiveness vary per track category (wide vs narrow)?
- Do we expose an "AI personality" preset for replay value (clean, aggressive, chaotic)?

## 14. Initial Defaults
- Easy:
  - conservative braking
  - low overtake frequency
  - strong recovery aid
- Medium:
  - balanced braking and line variance
  - occasional overtakes when safe
- Hard:
  - tighter line following
  - more consistent corner exits
  - active but bounded overtake behavior

---