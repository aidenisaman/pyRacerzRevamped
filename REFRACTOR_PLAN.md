# Refactor Plan

## Feature name: Menu Event Loop Refactor
- Technical Description: Extract a shared menu event/render loop (navigation callbacks, select handler) to replace duplicated while-key processing blocks across SimpleMenu/ChooseTrackMenu/etc.; remove per-class polling code and reuse a single navigation state + render function.
- Customer Description: Menus feel snappier and consistent; adding new menus becomes easier, reducing bugs when navigating options. -Done

## Feature name: Menu Rendering Helpers
- Technical Description: Centralize common drawing routines (title, selectable list rows, row clearing) and replace magic geometry numbers with helpers derived from `misc.screen`; layouts auto-scale with resolution/zoom.
- Customer Description: Cleaner, more consistent screens across resolutions; fewer visual glitches when changing display settings. -Done

## Feature name: Shared Resource Discovery
- Technical Description: Create cached utilities for discovering cars/tracks and loading their icons instead of scanning the filesystem in each menu; reuse loaded surfaces.
- Customer Description: Faster menu entry and smoother scrolling when choosing cars or tracks, especially on slower machines.

## Feature name: Reusable Text Entry
- Technical Description: Replace ad-hoc name entry/backspace logic with a reusable text-input helper that handles insert/delete, max length, and ESC/ENTER without blocking the main loop.
- Customer Description: Name/replay entry behaves predictably; no stuck screens while editing text.

## Feature name: Player Input Polymorphism
- Technical Description: Move input handling into Player subclasses (e.g., `handle_event`/`update_controls`) instead of class-name conditionals inside the game loop; bots/humans manage their own state.
- Customer Description: Better responsiveness and easier support for new control types (pads/network) without regressions. -Done

## Feature name: Broad-Phase Collisions
- Technical Description: Add a coarse spatial grid/AABB pass before detailed rect collisions to cut O(n²) checks between distant cars; only test likely pairs.
- Customer Description: Higher frame rates and smoother races with more cars on screen. -Done

## Feature name: Sprite Rotation Cache
- Technical Description: Cache per-color rotated car sprites at module level and share them across Car instances; avoid regenerating 256 rotations per car creation.
- Customer Description: Faster loading and less stutter when adding players or bots; lower memory use.

## Feature name: Car Update Math Simplification
- Technical Description: Hoist repeated `sin/cos/sqrt/acos` computations inside `Car.update` and reuse values; minimize per-frame heavy math.
- Customer Description: More stable FPS and smoother motion, especially on lower-end hardware.

## Feature name: Binary Replay Serialization
- Technical Description: Serialize replay frames as binary blocks (array/struct) and read via indexed access instead of string concat + `pop(0)`; reduces I/O and CPU overhead.
- Customer Description: Replays save/load faster and play back more smoothly.

## Feature name: Safer Config/Hi-Score I/O
- Technical Description: Modernize config handling with context managers and `hashlib.sha1()`, caching reads/writes to avoid corruption; encapsulate persistence behind a small helper.
- Customer Description: Hi-scores and unlocks are more reliable; less chance of losing progress.

## Feature name: CLI Parsing Modernization
- Technical Description: Replace manual argument parsing in `pyRacerz.py` with `argparse`, defining flags, defaults, and help; centralize option handling.
- Customer Description: Clearer command-line options and fewer startup errors when launching with custom settings. -Done
