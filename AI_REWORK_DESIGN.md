# AI Rework Design (Boids-Based Full Replacement)

## 1. Problem Statement
The current AI in `modules/player.py` (`RobotPlayer`) is fragile and hard to tune:
- Steering and braking are driven by a small set of ray checks and hardcoded thresholds.
- Recovery behavior is inconsistent when the bot leaves the road or gets stuck.
- Difficulty scaling is mostly threshold-based and can feel unfair or random.
- AI behavior is tightly coupled to low-level input flags (`keyAccelPressed`, `keyBrakePressed`, `keyLeftPressed`, `keyRightPressed`) rather than a clean decision model.
- There is little visibility into why an AI decision happened, making bug fixing slow.

Goal: replace the current AI with a deterministic, testable, boids-based architecture that improves race quality and player trust.

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
Introduce a boids-driven AI pipeline and keep it separate from car physics.

### 4.1 New Modules
- `modules/ai_types.py`
  - Shared lightweight data containers for AI state and outputs.
- `modules/ai_track_model.py`
  - Precomputed track graph/segments, ideal path, width estimates, curvature, and checkpoint mapping.
- `modules/ai_perception.py`
  - Fast local world queries: road occupancy, wall distance, nearby cars, heading error to target segment, and neighborhood vectors.
- `modules/ai_boids.py`
  - Computes weighted boid forces: separation, alignment, cohesion, wall-avoidance, and track-seeking.
- `modules/ai_behavior.py`
  - Lightweight behavior gating for race context: Cruise, OvertakeBias, Recover, AvoidCollision.
- `modules/ai_controller.py`
  - Converts final steering/velocity intents into control commands (throttle, brake, steer target).
- `modules/ai_tuning.py`
  - Difficulty parameter presets and per-track normalization values.
- `modules/ai_debug.py`
  - Optional overlay/debug logging for AI decisions and confidence values.

### 4.2 Integration Surface
- Keep `RobotPlayer` class but convert it into a thin adapter.
- `RobotPlayer.update_controls()` becomes:
  1. Collect perception snapshot.
  2. Compute boid force blend + behavior gates.
  3. Run controller.
  4. Apply output to car inputs.

This keeps existing game loop integration in `modules/game.py` intact and lowers migration risk.

## 5. Core Technical Decisions

## Decision A: Use boids as the local driving core
Rationale:
- The current AI reacts with hardcoded if-else logic and produces jitter.
- Boids gives smooth emergent spacing and flow between bots, reducing pileups.

Implementation:
- For each bot, compute normalized force vectors each update:
  - `F_separation`: move away from nearby cars to avoid contact.
  - `F_alignment`: align heading with nearby traffic flow.
  - `F_cohesion`: stay with local race flow to avoid isolation oscillation.
  - `F_track_seek`: pull toward track lookahead point.
  - `F_wall_avoid`: repel from boundaries and unsafe off-road zones.
- Blend with weights per difficulty/profile:
  - `F_total = ws*F_separation + wa*F_alignment + wc*F_cohesion + wt*F_track_seek + ww*F_wall_avoid`
- Convert `F_total` into target heading and target speed for the controller.

Player impact:
- Bots move as a believable pack, with fewer random swerves and fewer chain collisions.

## Decision B: Keep a small deterministic behavior gate on top of boids
Rationale:
- Pure boids can be too passive for race situations (stuck recovery/overtake commitment).
- A lightweight deterministic gate preserves debuggability and race intent.

States:
- `CRUISE`: normal boid blend.
- `OVERTAKE_BIAS`: temporarily boosts track-seek and alignment toward pass corridor.
- `AVOID_COLLISION`: temporarily boosts separation and wall-avoid forces.
- `RECOVER`: suppresses cohesion and hard-biases track rejoin + low-speed stability.

Rules:
- Explicit entry/exit conditions and cooldown timers.
- Minimum state dwell time to prevent rapid oscillation.

Player impact:
- Bots make understandable decisions and avoid erratic mode switching.

## Decision C: Difficulty = parameter sets, not hidden speed cheats
Rationale:
- Players perceive invisible cheating as unfair.

Difficulty parameters include:
- boid force weights (`ws`, `wa`, `wc`, `wt`, `ww`)
- neighborhood radius and forward vision cone
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
- Temporarily disable cohesion/alignment to prevent other bots from trapping recovery.

Player impact:
- Less race disruption and fewer broken races.

## Decision E: Performance budget with bounded perception costs
Rationale:
- AI should not create frame spikes, especially with many bots.

Constraints:
- Fixed maximum queries per bot per frame.
- Cache reusable map reads for nearby bots.
- Optional reduced update rate for boid neighborhood recomputation (for example 15 Hz) while keeping low-level controller per frame.

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
- `boid_weights`
- `neighbor_ids_cached`

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
- `neighbors_in_radius`
- `separation_vector`
- `alignment_vector`
- `cohesion_vector`

### 6.3 Controller Output (`ControlCommand`)
- `throttle` in `[0, 1]`
- `brake` in `[0, 1]`
- `steer` in `[-1, 1]`

Adapter layer maps command to existing car API (`doAccel`, `noAccel`, `doBrake`, `noBrake`, `doLeft`, `doRight`, `noWheel`).

## 7. Boids and Controller Details

### 7.1 Boid Neighborhood Model
- Use spatial hashing to find neighbors in a capped radius and forward cone.
- Ignore opponents too far behind unless collision risk is rising.
- Clamp neighbor count per bot to maintain frame-time stability.

### 7.2 Target Selection
- Project car position onto nearest path segment.
- Compute speed-based lookahead index:
  - higher speed -> farther target
  - high curvature ahead -> shorten lookahead
- Use lateral offset policy for variation/overtake behavior.

### 7.3 Steering Control
- Convert `F_total` into desired heading.
- Blend heading correction from track geometry:
  - `steer_raw = k_force * heading_error(F_total) + k_track * heading_error(track_tangent) + k_lateral * lateral_error`
- Clamp and smooth to reduce twitching.
- If imminent collision risk is high, blend in evasive steer component.

### 7.4 Throttle/Brake Control
- Determine target speed from curvature and local safety margins.
- Apply boid crowding penalty so dense packs brake slightly earlier.
- If `current_speed > target_speed + margin` then brake.
- If under target and stable, apply throttle.
- Add traction-safe throttle reduction when off-road or at high steering angle.

### 7.5 Opponent Interaction
- Let separation/alignment handle most close-range interaction naturally.
- Trigger `OVERTAKE_BIAS` when a slower opponent blocks forward progress.
- Commit to overtake side briefly to avoid indecision wobble.
- Abort overtake if wall risk or closure risk rises.

## 8. Observability and Debuggability

## Decision F: Build AI debug overlays and structured logs from day one
Rationale:
- AI bugs are easier to fix when decisions are visible.

Debug features (toggle in config):
- Draw target segment and lookahead point.
- Draw boid vectors (`separation`, `alignment`, `cohesion`, `track_seek`, `wall_avoid`).
- Render current FSM state above bot.
- Optional per-bot trace lines in log:
  - frame, state, force magnitudes, heading_error, target_speed, throttle, brake, steer, reason codes.

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
- Implement boids core (`ai_boids.py`) + controller.
- Replace old `compute()` path for bots behind a feature flag.

Exit criteria:
- Bots can complete laps on all stock tracks without major stalls.

### Phase 3: Recovery and Collision Avoidance
- Add stuck detection and recovery state.
- Add avoid-collision force boosts and safe braking refinements.

Exit criteria:
- Stuck incidents and wall spam substantially reduced.

### Phase 4: Overtake and Difficulty Tuning
- Add `OVERTAKE_BIAS` behavior and side-commit logic.
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

Risk: Boid cohesion causes traffic clumping in narrow tracks.
Mitigation: Dynamically reduce cohesion weight when track width shrinks.

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
  - `ai_boids_enabled`

If new fields are absent, defaults preserve current user experience while allowing controlled rollout.

## 13. Open Technical Questions
- Should defend behavior be enabled only on Hard to avoid frustrating casual players?
- Should overtake aggressiveness vary per track category (wide vs narrow)?
- Do we expose an "AI personality" preset for replay value (clean, aggressive, chaotic)?
- Should boid cohesion be disabled entirely on very tight maps?

## 14. Initial Defaults
- Easy:
  - conservative braking
  - lower alignment and cohesion, stronger wall-avoid
  - low overtake frequency
  - strong recovery aid
- Medium:
  - balanced boid weights and braking
  - occasional overtakes when safe
- Hard:
  - stronger alignment and track-seek, reduced safety margin
  - more consistent corner exits
  - active but bounded overtake behavior

---