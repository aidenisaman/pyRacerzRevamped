## AI Rework Plan and Implemented Status

### 1) Objective
Replace the legacy 7-ray steering behavior with stable checkpoint-to-checkpoint routing that works on overpass tracks, avoids solids/getting stuck, and completes races no matter how many laps.

### 2) Current Architecture

#### 2.1 Track-side path planning
- A* paths are precomputed in modules/track.py between each consecutive checkpoint pair.
- Paths are stored as ai_paths[(start_cp, end_cp)] and reused by bots.
- The planner runs on a 16px grid for speed and consistency.

#### 2.2 Bot-side control
- Robot steering in modules/player.py follows the precomputed waypoint segments.
- Waypoint index progression is forward-only to prevent U-turn loops.
- Dynamic lookahead is used to keep movement smooth.
- Position-history stuck detection replaced speed-only stuck detection.
- Progressive unstuck behavior cycles reverse-left, reverse-right, then forward-right.

### 3) Pixel/Map Semantics Used by AI
- Red channel: checkpoint IDs at multiples of 16.
- Green channel: fast-road/drivable preference for A*.
- Blue channel: soft layer transition cost (bridge/underpass awareness).
- Absolute black is treated as a solid obstacle and not drivable.

### 4) Implemented Stability and Performance Fixes

#### 4.1 Checkpoint extraction robustness
- Stray red pixels are ignored by bounding IDs to nbCheckpoint * 16.
- Checkpoint centroids are snapped to nearest drivable grid node.
- Duplicate snapped nodes are resolved to next-best unique node.
- A* goal uses snapped checkpoint nodes to avoid unreachable wall-centroid goals.

#### 4.2 Startup freeze reduction
- AI precompute now uses an in-memory per-track cache keyed by:
  (track_name, reverse, zoom, nav_source).
- Checkpoint scan uses a two-pass approach:
  fast pass step=2, fallback pass step=1 only for missing checkpoints.

### 5) Track-Specific Work Completed

#### 5.1 City
- Optional nav-only mask support (name + F2) was added.
- Soft blue-layer costs prevent wrong bridge transitions while still allowing required ramp connections.

#### 5.2 Desert
- AI now uses tracks/desertFNewWithoutBridge.png as its navigation source.
- This forces correct pathing through the underpass section instead of taking the false left branch.

#### 5.3 Forest
- Forest required map-side cleanup to make checkpoint breadcrumbing reliable for the planner.
- Checkpoint breadcrumb pixels and drivable guidance in mapF were adjusted so centroids land on valid road.
- Black obstacle regions are now explicitly treated as solid/undrivable during A*.

#### 5.4 Mountain
- Mountain also required map-side breadcrumb help for checkpoints so A* could form reliable segment routes.
- Additional planner spacing penalties near black obstacles were added to reduce rock-wall wedging.
- Player lookahead was tightened on mountain to reduce diagonal corner-cutting into black walls.
- Spawn orientation was corrected in tracks/mountain.conf (startAngle set to 3.14 for right-facing spawn).

#### 5.5 Nascar and Mountain load reliability
- Map-load failures caused by non-canonical checkpoint reds were resolved by strict checkpoint ID filtering.

### 6) Remaining Risk Areas
- Very narrow lanes with anti-aliased borders can still induce occasional wall-hugging.
- Tracks with sparse or noisy checkpoint paint may still need map-side breadcrumb touchups.

### 7) Next Iteration 
- Add states of driving to make more fun for players
- Add boids for multiple players to improve fun
