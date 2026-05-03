# pyRacerzRevamped

### Full feature set delivered on main

#### 1. Gameplay architecture and technical cleanup

- Reusable menu event-loop and render helpers replaced duplicated per-screen menu logic.
- Player input handling was refactored into player classes (human/bot behavior separated cleanly).
- Collision pipeline was improved with broad-phase checks to avoid unnecessary pair tests.
- Car update math was optimized by hoisting repeated trig-heavy calculations.
- CLI startup handling was modernized with argparse.
- Replay format moved to binary + zlib compression for improved save/load speed and lower overhead.
- Config/high-score persistence code was modernized for Python 3 reliability.
- Shared text-entry behavior was unified with reusable text input helpers (including IP entry for networking flows).

#### 2. Track and race-content expansion

We have significantly expanded and upgraded the available race content in main:

- New and reworked tracks:
	- Desert: major custom rebuild with layered bridge/underpass behavior.
	- City: redesigned and retuned.
	- Forest: introduced and integrated into race flow.
	- Formula: fully refreshed map/feature-map pass with updated `formula.png` + `formulaF.png` and config updates.
	- Beach: new additional track.
	- Mountain and Nascar: added and then iteratively fixed/tuned.
- Legacy tracks retained in the refreshed roster:
	- Bonus, Wave, and existing core circuits.
- Track-system improvements:
	- Multi-layer track masking and layer-aware collision/checkpoint behavior.
	- Reverse and normal direction support consistency.
	- Track testing checklist/process introduced to enforce repeatable quality gates.

#### 3. Drift and handling improvements

- Automatic drift mechanic integrated and tuned across several passes.
- Drift balance updates reduced overskid and improved control feel.
- Tire mark and smoke behavior added and adjusted for feedback/readability.
- Follow-up fixes corrected lateral-speed blend behavior, removed debug spam, and clamped steering edge cases.

#### 4. AI rework and race-completion reliability

- Legacy steering-only bot behavior was replaced with checkpoint-to-checkpoint path routing.
- A* path precompute between checkpoint segments was introduced with reusable path storage.
- Checkpoint extraction and snapping were hardened to prevent invalid/unreachable goals.
- Per-track navigation stabilization completed for complex maps (including Desert, City, Forest, Mountain, and Nascar follow-ups).
- Stuck handling was expanded with progressive recovery patterns.
- Precompute/scan work was optimized to reduce startup stalls on heavy tracks.

#### 5. Checkpoint system expansion (PR #26)

- The `Checkpoint_System` merge on main introduced dedicated race-flow updates centered on checkpoint progression and lap validation logic.
- Checkpoint behavior was expanded in core race code (`modules/game.py`) so progression handling is more explicit and easier to extend for future race rules.
- Formula track data was updated as part of this work to align map visuals and checkpoint semantics:
	- `tracks/formula.png` (updated visual map),
	- `tracks/formulaF.png` (feature/checkpoint map),
	- `tracks/formula.conf` (track configuration updates).
- Additional follow-up config tuning (including `tracks/nascar.conf`) shipped with the same merge to keep checkpoint-driven race flow consistent across tracks.
- Net result: race progression/checkpoint systems are now in a cleaner, branch-merged state on main and no longer isolated to side-branch logic.

#### 6. Online multiplayer expansion (MultiplayerPhase2 branch, pending merge)

The multiplayer description below is based on `MultiplayerPhase2`, which is the next merge target for main.

- Phase 1 baseline remains intact: host/join flow, threaded TCP networking, lobby roster, and in-lobby chat.
- `NetworkClientRace` is fully implemented as an active racer flow (not just spectator/watch mode).
- Clients now run local driving/input while exchanging per-frame state with the host.
- Host now sends explicit race-control `go` messages so race start authority is synchronized.
- Host broadcasts authoritative state for every racer, including checkpoint, lap, finish flag, speed, and tick metadata.
- Host-side collision resolution was expanded so online car-to-car collisions are resolved centrally and pushed to clients.
- Client-side reconciliation/interpolation was added to blend host-authoritative corrections while keeping local controls responsive.
- Finish handling now supports structured standings payloads (`FIN`/`DNF`) instead of only a simple race-end signal.
- Disconnect/leave behavior is more explicit with `bye` and host-driven `lobby_close` protocol support.
- Lobby-to-race loop supports repeated sessions with roster-aware metadata (player id, name, color, level) and track/lap updates from host decisions.
- Multiplayer integration now spans `modules/menu.py`, `modules/netgame.py`, `modules/network.py`, and `pyRacerz.py` so menu flow, protocol, and race simulation stay aligned.

#### 7. UI and presentation upgrades

- Countdown start presentation refreshed with clearer visual sequence and race-start audio cues.
- Race-finish result presentation upgraded with podium-style placement emphasis.
- Menus updated with stronger visual theming and improved track-selection presentation.
- Font fallback behavior improved for broader machine compatibility.

### Download prebuilt executables from GitHub Releases

If you don't want to build from source, you can download prebuilt executables for Windows, macOS, and Linux.

#### 1. Get the release

1. Go to the [Releases](https://github.com/aidenisaman/pyRacerzRevamped/releases) page on GitHub.
2. Click on the latest release (or a specific version you want).
3. Scroll down to **Assets** to see available downloads.

#### 2. Download and launch for your OS

**Windows:**
- Download `pyRacerz-Windows-x86_64.zip`
- Extract the zip file to any folder
- Open the extracted `pyRacerz` folder
- Double-click `pyRacerz.exe` to launch

**macOS:**
- Download `pyRacerz-macOS-x86_64.zip`
- Extract the zip file to any folder (or right-click and select "Open")
- Open the extracted `pyRacerz` folder
- Double-click `pyRacerz` (or right-click and select "Open" if OS X asks for permission)
- You may need to grant executable permission: `chmod +x pyRacerz/pyRacerz` in Terminal first

**Linux:**
- Download `pyRacerz-Linux-x86_64.tar.gz`
- Extract with: `tar -xzf pyRacerz-Linux-x86_64.tar.gz`
- Navigate to the folder: `cd pyRacerz`
- Make the executable: `chmod +x pyRacerz`
- Run the game: `./pyRacerz`

---


# ------------------------------------------------------------
# Audio Credits
# ------------------------------------------------------------
# Some sound effects and music used in this project are sourced from:
#
# Pixabay: https://pixabay.com/
# Freesound: https://freesound.org/
# Mixkit: https://mixkit.co/
#
# All assets are used under their respective licenses.
# ----------------------------------------------------------
