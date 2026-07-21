"""
Game Launcher
---------------
When a Start Game button is clicked, we need to open TWO things at once:
  1. the Unity build (.exe) for that game
  2. the Python script that talks to it (sensor input, scoring, etc.)

The Unity build is started with plain subprocess.Popen. The Python
controller is started with QProcess instead, specifically so we get a
finished(exit_code, exit_status) signal when it exits, since that script
is the one that saves the session to MongoDB and quits once the person
finishes/quits the game - that's the natural "the game session is over"
signal.

We also keep a handle to the Unity subprocess.Popen object per game, and
terminate it as soon as the Python controller exits - so quitting the
camera/calibration window (ESC in OpenCV) also closes the Unity window,
instead of leaving it open with a dead controller.

Unity/Python paths for each game now come from .env (see repo root),
NOT hardcoded here - so setting this up on a different machine is just
editing .env, no code changes needed. See GAME_LAUNCH_CONFIG below for
which env var names map to which game.
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from PyQt6.QtCore import QProcess

try:
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    print("[game_launcher] pywin32 not installed - the RehabVerse window "
          "won't auto-restore to front when a game closes. Run: "
          "pip install pywin32")

# Title of the main RehabVerse app window - must match exactly (this is
# whatever text shows in the window's title bar / taskbar).
REHABVERSE_WINDOW_TITLE = "RehabVerse"

# .env lives at the repo root - adjust the number of .parent calls if
# this file's location relative to the root ever changes.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


def bring_rehabverse_to_front():
    """Restores (un-minimizes) and focuses the main RehabVerse window,
    called once a game session ends - so the person lands back on the
    menu instead of an empty desktop after Unity closes."""
    if not HAS_WIN32:
        return

    hwnd = win32gui.FindWindow(None, REHABVERSE_WINDOW_TITLE)
    if not hwnd:
        print(f"[game_launcher] Couldn't find window titled "
              f"'{REHABVERSE_WINDOW_TITLE}' to restore.")
        return

    # Un-minimize if needed, then force it to the foreground.
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)


def _discover_games_from_env():
    """Builds GAME_LAUNCH_CONFIG directly from whatever's in .env, instead
    of a hardcoded per-game list of expected variable names. A pair like

        BLOOM_FOREST_UNITY_EXE=...
        BLOOM_FOREST_PYTHON_SCRIPT=...

    becomes game_id "bloom_forest" automatically. Adding a brand new game
    later is then purely a .env edit - this function never needs to know
    the game's name in advance, and this file never needs a code change
    for it. This also means there's nothing here to get wrong when
    reading a screenshot of .env - whatever's actually in the file IS
    the config, by construction."""
    configs = {}
    suffix = "_UNITY_EXE"

    for key, value in os.environ.items():
        if not key.endswith(suffix):
            continue

        prefix = key[: -len(suffix)]
        script_key = f"{prefix}_PYTHON_SCRIPT"

        if script_key not in os.environ:
            print(f"[game_launcher] Found '{key}' in .env but no matching "
                  f"'{script_key}' - skipping this game.")
            continue

        game_id = prefix.lower()
        configs[game_id] = {
            "unity_exe": value,
            "python_script": os.environ[script_key],
        }

    if not configs:
        print(f"[game_launcher] No games found in .env (checked {_ENV_PATH}) - "
              f"looked for pairs like SOMETHING_UNITY_EXE / SOMETHING_PYTHON_SCRIPT.")

    return configs


GAME_LAUNCH_CONFIG = _discover_games_from_env()

# Keeps QProcess objects alive while they run - PyQt doesn't keep a
# reference on its own, and a garbage-collected QProcess stops emitting
# signals (and can kill the child process) even while it's still running.
_active_processes = {}

# Keeps the Unity subprocess.Popen handle per game_id, so we can
# terminate it once the matching Python controller exits.
_active_unity_processes = {}


def launch_game(game_id, user_id=None, hand_pref=None, on_finished=None):
    """Starts the Unity build and Python controller for game_id side by
    side. If user_id is given, it's passed as the controller's first
    command-line argument (argv[1]) so it can skip its own interactive
    login. If hand_pref is also given (e.g. "left"/"right"/"both"), it's
    passed as the second argument (argv[2]) - cosmic_weaver_controller.py
    reads this to set ALLOWED_HAND before Unity even opens. Games that
    don't use a hand preference can just leave this as None/"".

    on_finished, if given, is called as on_finished(game_id, user_id,
    exit_code) once the Python controller process exits. It is NOT called
    if the controller script/config is missing (nothing was started)."""
    config = GAME_LAUNCH_CONFIG.get(game_id)
    if config is None:
        print(f"[game_launcher] No launch config for '{game_id}'.")
        return

    # config values can be None if .env was missing the corresponding
    # key (see _config_from_env) - catch that here with a clear message
    # instead of Path(None) throwing a confusing TypeError below.
    if not config["unity_exe"] or not config["python_script"]:
        print(f"[game_launcher] '{game_id}' has incomplete .env config - "
              f"not launching. See warnings above for which key is missing.")
        return

    unity_process = None
    unity_path = Path(config["unity_exe"])
    if unity_path.exists():
        try:
            unity_process = subprocess.Popen([str(unity_path)])
            _active_unity_processes[game_id] = unity_process
        except OSError as e:
            print(f"[game_launcher] Failed to launch Unity build: {e}")
    else:
        print(f"[game_launcher] Unity build not found at: {unity_path}")

    script_path = Path(config["python_script"])
    if not script_path.exists():
        print(f"[game_launcher] Python controller not found at: {script_path}")
        return

    process = QProcess()
    args = [str(script_path)]
    if user_id:
        args.append(user_id)
        # hand_pref can only be passed positionally after user_id, since
        # the controller reads argv[1]=user_id, argv[2]=hand_pref - it
        # can't be sent on its own without a user_id ahead of it.
        if hand_pref:
            args.append(hand_pref)
    process.setProgram(sys.executable)
    process.setArguments(args)

    # Prints whatever the python script prints/errors, live - useful for
    # seeing real tracebacks instead of just an exit code.
    def _handle_stdout():
        data = process.readAllStandardOutput().data().decode(errors="replace")
        print(f"[{game_id} stdout] {data}")

    def _handle_stderr():
        data = process.readAllStandardError().data().decode(errors="replace")
        print(f"[{game_id} STDERR] {data}")

    process.readyReadStandardOutput.connect(_handle_stdout)
    process.readyReadStandardError.connect(_handle_stderr)

    def _handle_finished(exit_code, exit_status):
        _active_processes.pop(game_id, None)
        print(f"[game_launcher] '{game_id}' controller exited (code={exit_code}).")

        # The Python controller (camera/calibration) is the "game session
        # is over" signal - close the matching Unity window too, instead
        # of leaving a dead/orphaned game window open.
        unity_proc = _active_unity_processes.pop(game_id, None)
        if unity_proc is not None and unity_proc.poll() is None:
            try:
                unity_proc.terminate()
                print(f"[game_launcher] Closed Unity window for '{game_id}'.")
            except OSError as e:
                print(f"[game_launcher] Failed to close Unity window: {e}")

        # Give Unity a brief moment to actually close its window before
        # we try to bring RehabVerse forward - otherwise Unity's own
        # close animation/handle can steal focus back right after.
        time.sleep(0.3)
        bring_rehabverse_to_front()

        if on_finished:
            on_finished(game_id, user_id, exit_code)

    process.finished.connect(_handle_finished)
    process.start()
    _active_processes[game_id] = process