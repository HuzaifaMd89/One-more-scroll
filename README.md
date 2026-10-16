# One More Scroll

A compact neon arcade game about escaping the feed. Collect focus, dodge
notifications, and survive 45 seconds. All artwork uses Pygame shapes and the
bundled default font. No images, accounts, API keys, backend, or asset packs.

## Play on Windows

The project's `.venv` is already prepared on this computer. From PowerShell in
this folder, run:

```powershell
.\.venv\Scripts\python.exe main.py
```

For a fresh installation, install 64-bit Python 3.12 or newer from
[python.org](https://www.python.org/downloads/windows/) with the Python launcher,
then open PowerShell:

```powershell
cd "C:\Users\MohammedHuzaifa\OneDrive - ALM\Desktop\OMS\One-more-scroll"
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Activation is unnecessary; these commands also avoid PowerShell execution-policy
issues. Only two packages are required: `pygame-ce==2.5.7` (imports as `pygame`)
and `pygbag==0.9.3` (browser packaging). Do not install the separate `pygame`
package alongside pygame-ce. For desktop-only use, installing
`pygame-ce==2.5.7` alone is sufficient. No additional test libraries are needed.

## Controls and rules

- Move: left/right arrows or A/D. On phones, hold either bottom direction pad.
- Green `+ FOCUS`: 10 points times the current combo. Each consecutive pickup
  increases the next pickup's multiplier, up to 5x. Damage resets it to 1x.
- Pink `!` cards: lose one of three lives. Damage grants 1.3 seconds of protection.
- Blue `~ MUTE`: three seconds of immunity, shown in the HUD. Another mute refreshes
  the duration. Hazards touched during protection disappear without damage.
- Escape or the top-right pause button pauses. Resume explicitly after switching
  tabs/windows. All movement, countdowns, spawns, particles, and effects freeze.
- Screen shake can be toggled on the menu or pause screen. It is brief and mild;
  there are no flashing invulnerability effects.
- A round ends at 45 seconds or zero lives. Play Again resets the round and keeps
  the best score. Desktop has Quit; browser has Return to menu.

## Run the browser version locally

From the project folder, generate the web build and serve its output:

```powershell
.\.venv\Scripts\python.exe build_web.py
.\.venv\Scripts\python.exe -m http.server 8000 --bind 127.0.0.1 --directory build\web-src\build\web
```

Open **http://localhost:8000** in a modern browser. Click/tap the page when pygbag
asks to start, then choose Find your focus. Keep the terminal open; Ctrl+C stops
the server. Opening `index.html` directly as a file does not work.

The build script stages only `main.py`, so virtual environments, tests, caches,
and other development files never enter the game download. Internally it runs:

```powershell
.\.venv\Scripts\python.exe -m pygbag --build --title "One More Scroll" --width 540 --height 820 build\web-src
```

Use `build_web.py` for release builds: it also adjusts the upstream loader's
portrait aspect ratio and loading-screen styling, then creates the ZIP.

## Browser release and itch.io upload

```powershell
.\.venv\Scripts\python.exe build_web.py
```

Upload **`dist\one-more-scroll-web.zip`**. Its `index.html` is at the ZIP root;
the ZIP also contains `favicon.png`, `web-src.apk`, and `web-src.tar.gz`.
The APK is pygbag's ZIP-format application payload, not an Android installer.
Do not ZIP the containing `web` folder, the source project, `.venv`, or `web-cache`.
If manually packaging, ZIP all files *inside* `build\web-src\build\web`.

1. Sign into your own itch.io account and choose **Upload new project**.
2. Give it a title and select **HTML** as the kind of project.
3. Upload `dist\one-more-scroll-web.zip` under Uploads.
4. Check **This file will be played in the browser** for the ZIP.
5. Set the embedded viewport to **540 wide by 820 high**. Enable the fullscreen
   button and mobile-friendly option; portrait is the intended phone orientation.
6. Save as Draft/Restricted first and preview. Check loading, both touch pads,
   pause/resume, a complete round, and score persistence after reloading.
7. Publish when you are satisfied; the itch.io project URL becomes the shareable
   browser link. Nothing has been uploaded or published by this project setup.

See the [official pygbag guide](https://pygame-web.github.io/wiki/pygbag/)
for runtime and hosting details.

## Storage and browser/mobile limitations

- Desktop best score: `%LOCALAPPDATA%\OneMoreScroll\best.json` on Windows;
  `~/.local/share/OneMoreScroll/best.json` if LOCALAPPDATA is absent.
- Browser best score: localStorage key `one-more-scroll-best`, scoped to the
  site's origin. Moving hosts or clearing site data clears that origin's record.
- Missing/corrupt saves and blocked storage fall back safely. If writing fails,
  the current session still keeps its best score; the result screen says so.
- The default pygbag runtime downloads Python/WebAssembly and Pygame from its
  public CDN. First load needs internet and may take a while. This is a static
  HTML game, but the ZIP is not a fully offline runtime distribution.
- Current Chrome, Edge, Firefox, and Safari with WebAssembly are intended targets.
  Mobile performance and memory vary. Use portrait or fullscreen for larger pads;
  landscape preserves the portrait play area with unused space beside it.
- Background tabs suspend/throttle animation. The game pauses on focus loss or
  page hiding, clears held input, and clamps frame deltas to 50ms on return.
  Gameplay uses delta time, with a 60 FPS desktop target and browser animation
  scheduling. Slow devices may render fewer frames.
- Multiple touch pointers are supported. Opposite held directions cancel out.
- Live browser and physical-phone play still require manual verification on
  this machine because no browser automation surface was available during setup.

## Checks and source layout

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\render_preview.py
```

The 13 deterministic checks cover movement/bounds, delta-time clamping, scoring,
combo cap/reset, collision removal, overlapping hazards, immunity expiry, complete
pause freezing, difficulty ramp, round ending, restart, focus/input clearing,
scaled pointer mapping, all screens, and save corruption/failure handling.
Preview PNGs go to `build\previews`.

- `main.py`: round simulation, storage, UI/input, drawing, asynchronous entry point.
- `requirements.txt`: the two pinned dependencies.
- `build_web.py`: clean source staging, pygbag build, root-index ZIP validation.
- `tests/test_game.py`: standard-library unittest suite with SDL's dummy display.
- `tools/render_preview.py`: menu/play/pause/result visual previews.
- `.gitignore`: excludes environments, caches, and generated output.

Setup verification: all 13 checks passed on Windows with Python 3.14.7 and
pygame-ce 2.5.7; the native window started and closed cleanly after 90 frames;
menu and gameplay PNGs were visually inspected; pygbag 0.9.3 generated the
browser release and its ZIP passed integrity/root-index checks. Browser runtime,
browser localStorage, and real-device touch have not been tested live.
