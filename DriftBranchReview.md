# Drift Mechanic Branch — Code Review

-Tester/Reviewer - Aiden West
---

## car.py issues

### 1. The fast-build / slow-fade drift logic doesn't actually work

From how I understand it the idea was: drift intensity builds up fast and fades away slowly. Two lerp lines were written for this. The problem I see is both lines run one after the other every single frame no matter what. The first one nudges the value toward the target, then immediately the second one nudges the already-changed value again. From what I have seen is that they're fighting each other and the end result is just one blended rate — the fast and slow distinction is completely gone. To fix this I would suggest adding an if/else so only one runs at a time depending on whether you're building up or fading out.

### 2. The lateral speed variable is being filled with forward speed

There's Confer's formula that's supposed to blend the car's sideways (lateral) drift speed. The problem I found was it's blending in `self.speed`, which is the car's *forward* speed, not a lateral target. So every frame while drifting, 65% of the lateral slip gets replaced by the forward speed. What I found in game was that the drift slide dies way faster than it should. If you want the lateral speed to decay more naturally, the target should be `0.0`, not `self.speed`.

### 3. A debug print statement is still in the code

I found a `print("PROBLEM")` call that was clearly left in by accident during debugging. It fires every frame whenever the car's collision rectangle doesn't perfectly match the car's position — which happens all the time during normal play. So during a race this is spamming your terminal hundreds of times per second. It needs to be deleted.

### 4. Steering input can push the drift intensity above 1, causing negative acceleration

I also found that the drift calculation assumes steering input (`angleW`) stays between -1 and 1. If it ever goes above 1 for any reason (AI cars, replay playback, a bug somewhere), the math produces a `tractionMultiplier` below zero. That means pressing the gas would actually push the car backwards. Probably would rarely happen but I think it would be worth clamping the input so it can't happen at all.

---

## game.py issues

### 5. A font is being created from scratch every single frame

`pygame.font.SysFont("Arial", 14, bold=True)` is sitting inside the main game loop. After noticing this I did some reasearch and found out that loading a font is one of the most expensive things pygame does. This is being called over 60 times per second for no reason. I suggest that the font should be created once before the loop starts and reused. I also saw that the pause menu does the same thing — it creates two fonts every paused frame.

### 6. Three surfaces are being created from scratch every single frame

- The HUD background box
- The full-screen dark overlay (when paused)
- The pause menu box

All three are `pygame.Surface(...)` calls inside the loop. Creating surfaces is expensive. As mentioned before they should be made once before the loop and reused.

### 7. The minimap rescales the entire track image every frame

```python
mini_track = pygame.transform.smoothscale(currentTrack.track, (MINIMAP_SIZE, MINIMAP_SIZE))
```

Since the track image barely changes during a race (only tire marks are added). This line is doing a full smooth scale of a large surface on every single frame. It should be scaled once when the track loads and saved. The tire mark problem can be handled separatel or just not be put on the minimap at all.

### 8. The screen flickers while paused

When testing the game I found when the game is paused and it's also the frame where the display would normally refresh (`i == 1`), `pygame.display.flip()` gets called twice in the same frame causing the screen to flicker. I found that one call is at the end of the pause menu code, and another is in the normal display refresh block. Every other paused frame the screen flips twice, which causes visible flickering.

### 9. Replay data keeps recording while the game is paused

The bit of code that saves position/angle/input data to the replay runs every frame, including paused ones. So if you pause for 10 seconds mid-race the replay file has 1000 frames of the car sitting perfectly still baked into it. The replay recording should be skipped while paused.

### 10. Restarting the race with T causes a stack overflow if done enough times

So when you press T to restart, the code calls `return self.play()` — it just calls the whole race function again from inside itself. Every restart stacks another function call on top of the last one. I found that Python has a limit on how deep you can go. After doing this enough times in a long session I got the game will crash with a recursion error.

### 11. Player type is checked using the class name as a string

In a couple of places the code does `play.__class__.__name__ == "HumanPlayer"` to figure out what type of player it's dealing with. I wrote a whole refactor that was done on my branch specifically to get rid of this pattern and use proper methods instead. This branch brings it back, which means merging the two branches is going to be a headache.

### 12. The pause overlay redraws everything that was already on screen

When I pause the game, the code re-blits the track, redraws all the cars, redraws the HUD, and redraws the minimap — even though all of that was already drawn to the screen moments earlier in the same frame. Then it puts a dark overlay on top of all of it. All those redraws are completely wasted. You just need to draw the dark overlay and the pause menu box on top of whatever is already there.

### 13. Minimap position is stored in a module-level global set inside a method

`MINIMAP_POS` is a global variable at the top of the file, but it gets its actual value assigned deep inside the `play()` method. This is messy — if `play()` ever runs again with a different screen size (which it does, since the tournament loop calls it multiple times) the global could be stale or wrong. It should just be a local variable or stored on `self`.

### 14. ESC now pauses instead of exiting — inconsistent everywhere else

In the source ESC is used to exit the race. Now in this branch it toggles pause. Every single menu in the game uses ESC as "go back / cancel". The network game code I made also uses ESC as exit. This branch makes the race loop the one weird exception where ESC means something different. Players will be confused and the network code will break.

### 15. The replay file format was already replaced on another branch

One of the completed refactors I made replaced the old text-based replay format with a binary one. This branch ignores that and still uses the old format (text header + zlib-compressed string). If you try to merge these two branches there will be a direct conflict in the replay save code and the files they produce won't be compatible with each other.

---

## Quick Reference Table(Formatted by ai to make it easy to view/understand issues quickyly)

| # | File | How bad | What's wrong |
|---|------|---------|--------------|
| 1 | car.py | 🔴 Big | Fast-build / slow-fade lerps both run every frame — the distinction is lost |
| 2 | car.py | 🔴 Big | Lateral speed blended toward forward speed, not zero — kills the slide |
| 3 | car.py | 🟡 Medium | `print("PROBLEM")` debug spam firing 60+ times per second |
| 4 | car.py | 🟡 Medium | Steering above 1.0 makes traction go negative (gas reverses the car) |
| 5 | game.py | 🔴 Big | Font loaded from scratch every single frame |
| 6 | game.py | 🔴 Big | Three surfaces allocated from scratch every frame |
| 7 | game.py | 🔴 Big | Full track scaled to minimap size every frame — should be cached once |
| 8 | game.py | 🔴 Big | Two `display.flip()` calls on same frame while paused — screen flickers |
| 9 | game.py | 🟡 Medium | Paused frames get recorded into the replay |
| 10 | game.py | 🟡 Medium | T-to-restart is recursive — crashes after enough restarts |
| 11 | game.py | 🟡 Medium | Class name string checks undo the player polymorphism refactor |
| 12 | game.py | 🟡 Medium | Pause overlay redraws the whole scene that was already on screen |
| 13 | game.py | 🟡 Medium | `MINIMAP_POS` global set inside an instance method |
| 14 | game.py | 🟡 Medium | ESC changed to pause — breaks consistency with every other part of the game |
| 15 | game.py | 🟡 Medium | Old text replay format conflicts with the binary replay refactor branch |
