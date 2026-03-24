# Sound Settings Design

Customizable sound selection and volume control for recording start/stop feedback.

## Problem

Currently vvrite plays hardcoded system sounds ("Glass" for start, "Purr" for stop) at system volume. Users cannot change which sound plays or adjust the volume independently of the system volume.

## Solution

Add a "Sound" section to the Settings window where users can:
- Choose a sound for recording start and stop independently
- Select from macOS system sounds or a custom audio file (aiff/wav/mp3)
- Adjust volume (0–100%) for each sound independently
- Hear the sound immediately when changing the slider (auto-preview on mouse-up)

## Design

### UI Layout

The Sound section goes between the "Custom Words" section and the "Permissions" section in the Settings window. Each sound (start/stop) gets one row:

```
Sound
  Start   [▾ Glass         ]  ━━━━━━━●━━━  70%
  Stop    [▾ Purr          ]  ━━━●━━━━━━━  50%
          슬라이더를 조절하면 선택된 소리가 자동으로 재생됩니다
```

Each row contains:
- Label ("Start" / "Stop") — 80px, right-aligned
- NSPopUpButton — 140px, lists system sounds + separator + "Custom..."
- NSSlider — fills remaining space, continuous, 0–100
- Volume label — 32px, shows current percentage

### Sound Dropdown Behavior

**System sounds:** Enumerate `/System/Library/Sounds/*.aiff` at window open. Display filenames without extension, sorted alphabetically.

**"Custom..." option:** Opens NSOpenPanel restricted to audio file types (aiff, wav, mp3, m4a, caf). On selection, the dropdown displays the filename. The full path is stored in preferences.

**On sound change:** Immediately play the newly selected sound at the current volume.

### Volume Slider Behavior

- Range: 0–100 (integer), mapped to NSSound volume 0.0–1.0
- Continuous slider (visual tracking while dragging)
- **Auto-preview on mouse-up:** When the user releases the slider, play the current sound at the new volume. No preview during drag (avoids rapid repeated playback).
- Volume percentage label updates in real-time during drag.

### Slider Wiring

Two concerns — live label update and sound preview — require separate mechanisms:

1. **Live label update:** The slider is set to continuous (`setContinuous_(True)`) so its action fires during drag. The action handler updates the percentage label and saves the preference on every change.
2. **Sound preview on mouse-up only:** Use `slider.cell().sendActionOn_(NSLeftMouseUpMask)` to restrict when a *second* target/action fires. However, since NSSlider only supports one target/action pair, the simpler approach is: the action handler always updates the label and saves the preference, but only plays sound when the mouse is up. Detect this by checking `NSApp.currentEvent().type() == NSEventTypeLeftMouseUp` inside the action handler. If the event is a mouse-up, play the preview; otherwise, just update the label.

## Data Model

### New Preferences

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `start_volume` | Float | 1.0 | Start sound volume (0.0–1.0) |
| `stop_volume` | Float | 1.0 | Stop sound volume (0.0–1.0) |

Existing `sound_start` and `sound_stop` string properties are reused. System sounds are stored as the sound name (e.g., "Glass"). Custom sounds are stored as the full file path (e.g., "/Users/foo/beep.wav").

### Distinguishing System vs Custom

A value is a custom file path if it contains a `/` character. Otherwise it's a system sound name. This logic lives in `sounds.is_custom_path()` — a single source of truth used by both `sounds.py` and `settings.py`.

## Implementation

### sounds.py Changes

Current API:
```python
def play(name: str):
    sound = NSSound.soundNamed_(name)
    if sound:
        sound.play()
```

New API:
```python
def play(name: str, volume: float = 1.0):
```

Logic:
1. If `name` contains `/`, treat as file path: `NSSound.alloc().initWithContentsOfFile_byReference_(name, True)`
2. Otherwise, use `NSSound.soundNamed_(name)` (system sound) — **must call `.copy()` on the result** to avoid mutating the shared cached instance
3. Set `sound.setVolume_(volume)` before `sound.play()`

Helper function:
```python
def is_custom_path(name: str) -> bool:
    return "/" in name
```
This centralizes the system-vs-custom heuristic so it isn't re-implemented in `sounds.py` and `settings.py` independently.

Also add:
```python
def list_system_sounds() -> list[str]:
```
Returns sorted list of sound names from `/System/Library/Sounds/`.

### preferences.py Changes

Add two new properties with defaults in `_DEFAULTS`:
- `start_volume`: 1.0
- `stop_volume`: 1.0

Note: `_PREFERENCE_KEYS` is derived from `_DEFAULTS.keys()`, so adding keys to `_DEFAULTS` automatically includes them in legacy migration. No manual update to `_PREFERENCE_KEYS` is needed.

### settings.py Changes

Add Sound section UI between Custom Words and Permissions. New instance variables:
- `_start_sound_popup`, `_stop_sound_popup` — NSPopUpButton
- `_start_volume_slider`, `_stop_volume_slider` — NSSlider
- `_start_volume_label`, `_stop_volume_label` — NSTextField (percentage display)

Window height increases from 586 to ~680 to accommodate the new section.

Action handlers:
- `startSoundChanged:` / `stopSoundChanged:` — save preference, play preview
- `startVolumeChanged:` / `stopVolumeChanged:` — save preference, update label, play preview on mouse-up only
- `_open_custom_sound_panel(for_start: bool)` — NSOpenPanel for custom file

`showWindow_` must call `_populate_sounds()` (similar to the existing `_populate_mics()` pattern) to refresh sound dropdowns each time the window opens. This handles custom files that were deleted/moved since last open.

### main.py Changes

Update the two `sounds.play()` calls to pass volume:
```python
sounds.play(self._prefs.sound_start, self._prefs.start_volume)
sounds.play(self._prefs.sound_stop, self._prefs.stop_volume)
```

## Files to Modify

1. **vvrite/sounds.py** — Add volume parameter, custom file support, `list_system_sounds()`
2. **vvrite/preferences.py** — Add `start_volume`, `stop_volume` properties
3. **vvrite/settings.py** — Add Sound section UI with dropdowns, sliders, auto-preview
4. **vvrite/main.py** — Pass volume to `sounds.play()` calls

## Edge Cases

- **Custom file deleted/moved:** `NSSound.initWithContentsOfFile_` returns nil. Fall back silently (no sound). The dropdown still shows the filename; user can re-select.
- **Volume 0%:** No sound plays (or plays at 0 volume). This is valid — user may want visual-only feedback.
- **System sounds directory changes across macOS versions:** Enumerate at runtime, not hardcoded list. If empty, only "Custom..." is available.
