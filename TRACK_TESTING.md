# Track Testing Checklist
---

## Track name: ___________________   Tester: ___________________   
---

## 1. File Completeness

- [ ] `tracks/<name>.png` exists (visible track image, 1024×768)
- [ ] `tracks/<name>F.png` exists (feature/checkpoint map, 1024×768)
- [ ] `tracks/<name>.conf` exists and is valid INI format
- [ ] `.conf` contains `[track]` section with `author` and `nbCheckpoint`
- [ ] `.conf` contains `[normal]` section with all 6 start coords + `startAngle`
- [ ] `.conf` contains `[reverse]` section with all 6 start coords + `startAngle`
- [ ] Track appears in the **Choose Track** menu without errors

---

## 2. Config Values — Normal Direction

- [ ] `startX1 / startY1` places car 1 on the road (not clipping a wall)
- [ ] `startX2 / startY2` places car 2 on the road (not overlapping car 1)
- [ ] `startX3 / startY3` places car 3 on the road (not overlapping car 2)
- [ ] `startAngle` points cars in the correct direction of travel
- [ ] `nbCheckpoint` matches the actual number of coloured checkpoint bands in `<name>F.png`

## 2b. Config Values — Reverse Direction

- [ ] `startX1 / startY1` places car 1 on the road facing reverse
- [ ] `startX2 / startY2` places car 2 on the road (not overlapping car 1)
- [ ] `startX3 / startY3` places car 3 on the road (not overlapping car 2)
- [ ] `startAngle` points cars in the correct reverse direction
- [ ] Checkpoint order is traversable in reverse (checkpoint colours decrement correctly)

---

## 3. Checkpoint Map (`<name>F.png`) Validation

- [ ] Checkpoint bands are distinct solid colours spaced evenly around the full circuit
- [ ] Each band colour value is a multiple of 16 (16, 32, 48 … up to `nbCheckpoint × 16`)
- [ ] No gap exists where a car could cross the finish line without hitting a checkpoint
- [ ] No two separate sections of track share the same checkpoint colour
- [ ] The finish/start line pixel colour is exactly `16` (RGB red channel)
- [ ] Off-track / wall areas are colour `0` (black) so car detection works correctly
- [ ] Tunnel sections (if any) use the correct mask colour so the tunnel overlay triggers

---

## 4. Single Race — Normal Direction

- [ ] Race loads without Python errors or tracebacks
- [ ] All 3 start positions spawn without cars inside walls
- [ ] Traffic lights display and count down correctly
- [ ] Lap counter increments when crossing the finish line in the correct direction
- [ ] "MISSED checkpoint" popup appears when a checkpoint is skipped
- [ ] Best-lap (B) tag appears correctly on a lap that beats the previous best
- [ ] Race ends after the configured number of laps
- [ ] "Race finish!" screen appears and waits for key press
- [ ] ESC during race exits cleanly with no crash

## 4b. Single Race — Reverse Direction

- [ ] Reverse race loads without errors
- [ ] Lap counter increments in reverse direction only
- [ ] Checkpoints decrement correctly (no false lap or missed-checkpoint triggers)
- [ ] Start positions face the reverse direction of travel

---

## 5. Multi-Car Behaviour (2–4 players / bots)

- [ ] Cars do not spawn overlapping each other at race start
- [ ] Collision detection fires when two cars touch (no pass-through)
- [ ] Bot cars navigate the track without getting permanently stuck
- [ ] Lap/checkpoint tracking is independent per car (one car finishing does not end race)

---

## 6. Resolution Scaling

- [ ] Track renders correctly at **1024×768** (zoom 1.0)
- [ ] Track renders correctly at **640×480** (zoom 0.625)
- [ ] Track renders correctly at **320×240** (zoom 0.3125)
- [ ] Start positions remain on the road at all three resolutions

---

## 7. Tournament Inclusion

- [ ] Track appears in the tournament track list
- [ ] Both normal and reverse variants appear in the full tournament sequence
- [ ] Track name displays cleanly in the hi-scores table (no truncation)

---

## 8. Bonus / Locked Track (if applicable)

- [ ] Track file is named `bonus<N>.png/.conf` where N is the required unlock level
- [ ] Track does **not** appear in menus when unlock level is below N
- [ ] Track **does** appear after reaching unlock level N
- [ ] Compressed `.png` files load without zlib errors

---

## 9. Multiplayer

- [ ] Host can select and start the track in a network lobby
- [ ] `track` field in the `start` message matches the conf filename (no extension)
- [ ] Client `NetworkWatchRace` loads the track without file-not-found errors
- [ ] Car positions appear correctly on client screen during the race

---

## 10. Replay

- [ ] A race on this track can be saved as a `.rep` file
- [ ] The saved replay loads and plays back without errors
- [ ] Replay car follows the correct path around the track

---

## Sign-off

| Direction | Tester | Pass / Fail | Notes |
|-----------|--------|-------------|-------|
| Normal    |        |             |       |
| Reverse   |        |             |       |

**Overall status:** `[ ] Ready to merge   [ ] Needs fixes — see notes above`
