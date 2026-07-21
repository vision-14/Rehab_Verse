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

PATHS: this app is distributed as a portable folder (bundled Python +
source, no PyInstaller freezing) - see the project's packaging notes.
That means the install location isn't known in advance, and .env can't
hold a working absolute path on every machine. So every path below is
computed RELATIVE to this file's own location instead - wherever
RehabVerse actually ends up installed, "games/GAMES/BloomForest/..." is
always in the same place relative to game_launcher.py itself. .env is
no longer used for paths at all - it's reserved for things that
genuinely differ per install, like the MongoDB connection string (read
by db.py, not this file).

sys.executable is safe to use as-is here (launches the bundled portable
python.exe against a .py script path) BECAUSE this app is not frozen
with PyInstaller - if that ever changes, this file's QProcess setup
below needs to change too (each controller would need to become its own
frozen .exe, launched directly instead of via a python interpreter).
"""

import subprocess
import sys
import time
from pathlib import Path
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

# Repo root - adjust the number of .parent calls if this file's location
# relative to the root ever changes (currently assumes this file lives
# at RehabVerse/app/game_launcher.py, one level under the root).
REPO_ROOT = Path(__file__).resolve().parent.parent
GAMES_ROOT = REPO_ROOT / "games"


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


# Every path here is built from GAMES_ROOT, not written out as an
# absolute string - so this whole dict is correct on ANY machine the
# app is installed on, with zero setup. Adding a new game is a new
# entry here (unlike the old .env-driven version, this needs a small
# code edit for a new game - but in exchange, path setup on a new
# machine needs NO edits anywhere, which is the more common case).
GAME_LAUNCH_CONFIG = {
    "bloom_forest": {
        "unity_exe": GAMES_ROOT / "GAMES" / "BloomForest" / "Vines_unity" / "wristrehab.exe",
        "python_script": GAMES_ROOT / "bloom_forest" / "bloom_forest_controller.py",
    },
    "cosmic_weaver": {
        "unity_exe": GAMES_ROOT / "GAMES" / "Cosmic_Weaver" / "Cosmic_weave.exe",
        "python_script": GAMES_ROOT / "cosmic_weaver" / "cosmic_weaver_controller.py",
    },
}

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

    unity_process = None
    unity_path = config["unity_exe"]
    if unity_path.exists():
        try:
            unity_process = subprocess.Popen([str(unity_path)])
            _active_unity_processes[game_id] = unity_process
        except OSError as e:
            print(f"[game_launcher] Failed to launch Unity build: {e}")
    else:
        print(f"[game_launcher] Unity build not found at: {unity_path}")

    script_path = config["python_script"]
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