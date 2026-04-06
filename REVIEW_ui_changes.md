# Code Review — ui_changes branch
Reviewer: Battula Thanay Reddy
Date: 5 April 2026

## What Was Added
- Countdown lights changed to red, orange and green sequence with numbers 3, 2, 1
- Countdown sound effect for race start
- Race results screen with gold, silver and bronze positions
- Menu visual upgrades with background images and track selection grid
- Font system upgraded with system fonts and fallback

## Issues Found

### RED — Must Fix Before Merge

| # | File | Issue | Fix |
|---|------|-------|-----|
| 1 | game.py | Hardcoded personal Windows path `c:\Users\nalla\Downloads\` will crash on every other machine | Remove the entire user_sound_path block |
| 2 | misc.py | `sha1.new()` is Python 2 syntax, crashes on Python 3 | Replace with `sha1()` and add `.encode()` on all strings |
| 3 | game.py | Class name string checks `play.__class__.__name__` used multiple times | Replace with helper functions is_human() and is_robot() |
| 4 | game.py | Replay saving uses old string format | Replace with `zlib.compress(replayArray.tobytes())` |
| 5 | modules/__pycache__ | Binary cache files committed to repo | Add __pycache__ to .gitignore and remove from repo |

### YELLOW — Should Fix

| # | File | Issue | Fix |
|---|------|-------|-----|
| 6 | game.py | countdownFont created every race inside loop | Create once outside the loop |
| 7 | game.py | Four nested try/except blocks for sound loading | Simplify to one try/except |
| 8 | game.py | shutil imported only for personal Windows path copy | Remove entire shutil block |
| 9 | misc.py | confFile.readfp() is deprecated in Python 3 | Replace with read_file() |
| 10 | game.py | Magic numbers 400, 500, 630 in results screen | Replace with named constants |

## Summary
5 red issues must be fixed before merge. The UI features are solid. 
Main blockers are the hardcoded Windows path, old sha1 syntax and committed cache files.
