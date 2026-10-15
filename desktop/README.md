# Bfxr for Windows

A standalone Electron edition of Bfxr with a Windows 95 interface. All 23 sound
generators, parameter locks, musical and transition editors, collections, WAV
export, and drag-and-drop import use the existing Bfxr engines.

## Run

Install dependencies with `npm ci`, then run `npm start`.
The app works offline after installation. A recent Electron release may download
its runtime on first use; `npx install-electron --no` can complete that step ahead
of time.

## Build a standalone app

Run `npm run package:desktop` on Windows. Launch `dist/Bfxr95/Bfxr.exe`.
Keep the entire **Bfxr95** folder together; it includes the Electron runtime, so
the recipient does not need Node.js, npm, or a local web server. The path stays
the same across rebuilds and starts directly without unpacking an archive.
Close the running packaged app before rebuilding. This local build is unsigned.

Collections are saved automatically in the app's separate Windows profile,
`%APPDATA%/Bfxr95`. Use **Save collection** for a portable `.bcol` backup.
**Open** accepts `.bfxr` and `.bcol` files; WAV export uses the system Save dialog.
Browser collections can be moved into the app using `.bcol` files.

## Controls

- Select a generator from the multi-row tabs, then a preset to make a sound.
  The selected tab's row moves next to the page, as in classic Windows dialogs.
- Space plays; R randomizes; M mutates; L toggles parameter locks.
- Ctrl+O opens, Ctrl+S saves a sound, Ctrl+E exports WAV.
- Alt+F/E/S/H or F10 opens a menu. Arrows navigate; Escape closes it.
- Arrow keys navigate the generator tabs; Home/End selects the first/last tab.
  Parameter locks also support keyboard navigation.
- The built-in About dialog contains Bfxr credits and more shortcuts.

## Implementation and verification

`desktop/build.js` copies the shared application into an ignored build folder,
adds the desktop presentation, and precompiles the bundled PureData terrain
patches. The browser application is unchanged. The Electron renderer is
sandboxed with context isolation; its preload exposes only window commands and
status notifications. External links open in the default browser.

`npm test` runs the shared engine tests. `npm run test:desktop` launches actual
GPU-enabled Electron windows with an isolated temporary profile, exercises all
23 generators, save/open and WAV export, persistence, menus, keyboard controls,
window controls, narrow layout, and 100/125/150/200 percent scale factors.
Screenshots and the runtime report are written to `desktop/artifacts/`.
Set `BFXR_PACKAGED=1` to run these checks against the packaged executable.

The System95 font uses grayscale text rendering via Electron's startup switch.
The simulated scale factors are verified in Electron; this does not substitute
for testing Windows mixed-DPI monitor transitions. See `NOTICES.txt` and
`assets/` for the original font licenses and source attribution.
