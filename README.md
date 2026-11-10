# Reintegrate

You are a hand. Somewhere across the city, a piano has gone quiet.

A 2.5D side-scrolling desktop game: low camera, layered parallax city, film grain,
letterbox. Four chapters from 2:14 a.m. to sunrise. Control the hand with the keyboard
or with your own hand in front of a webcam.

## Run it

- **Windows:** double-click `run.bat`. The first run installs what it needs into
  `%LOCALAPPDATA%\Reintegrate\venv` (a few minutes), later runs start straight away.
- **Linux / macOS / WSL:** `./run.sh`

Options: `--no-camera` (keyboard only), `--dev` (N skips to the next chapter).

The webcam only works where the operating system exposes one. Inside WSL there is
normally no camera, so use `run.bat` from Windows for hand control.

## Controls

| | Keyboard | Camera |
|---|---|---|
| Move | A / D or arrow keys | hold your hand left or right of the centre of the picture |
| Jump | Space (hold for a higher jump) | raise your hand above the line, or flick it upward |
| Crouch, hold on in wind, keep still | S | close your fist |

`C` camera on/off, `F11` fullscreen, `Esc` pause. The small panel in the top-right corner
shows what the camera sees: the two vertical lines are the neutral zone, the horizontal
line is the jump line.

## Chapters

1. **The Laundromat** - steam vents, a robot vacuum (its bumper catches you, its back carries you), a hanging tray.
2. **Night Market** - rain, live puddles, and cats that only see what moves.
3. **Rooftops** - gusts of wind (make a fist to hold on) and neon signs that are only solid while lit.
4. **The Room** - a quiet climb to the keyboard.

Fourteen "echoes" (things the hand remembers touching) are scattered along the way.

## Files

- `main.py` - game loop, states, HUD
- `game/hand.py` - the hand: physics and procedural finger-walking animation
- `game/world.py` - chapters, creatures and hazards, painted backdrops
- `game/tracker.py` - webcam hand tracking (MediaPipe) turned into controls
- `game/fx.py` - palette, light, grain, particles, synthesised sound

All art and sound are generated in code; there are no asset files.
