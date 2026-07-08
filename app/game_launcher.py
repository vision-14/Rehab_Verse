"""
Game Launcher
---------------
When a Start Game button is clicked, we need to open TWO things at once:
  1. the Unity build (.exe) for that game
  2. the Python script that talks to it (sensor input, scoring, etc.)

The Unity build is started with plain subprocess.Popen - we don't need to
know when it closes. The Python controller is started with QProcess
instead, specifically so we get a finished(exit_code, exit_status) signal
when it exits, since that script is the one that saves the session to
MongoDB and quits once the person finishes/quits the game - that's the
natural "the game session is over" signal.

Fill in the real paths below once the Unity builds and Python controller
scripts are in their final locations.
"""

import subprocess
import sys
from pathlib import Path
from PyQt6.QtCore import QProcess

# TODO: point unity_exe at your actual build location once it exists.
GAME_LAUNCH_CONFIG = {
    "bloom_forest": {
        "unity_exe": r"C:\RehabVerse\Games\BloomForest\BloomForest.exe",
        "python_script": r"C:\RehabVerse\games\bloom_forest\bloom_forest_controller.py",
    },
    "cosmic_weaver": {
        "unity_exe": r"C:\RehabVerse\Games\CosmicWeaver\CosmicWeaver.exe",
        "python_script": r"C:\RehabVerse\games\cosmic_weaver\cosmic_weaver_controller.py",
    },
}

# Keeps QProcess objects alive while they run - PyQt doesn't keep a
# reference on its own, and a garbage-collected QProcess stops emitting
# signals (and can kill the child process) even while it's still running.
_active_processes = {}


def launch_game(game_id, user_id=None, on_finished=None):
    """Starts the Unity build and Python controller for game_id side by
    side. If user_id is given, it's passed as a command-line argument to
    the Python script so it can skip its own interactive login and reuse
    the account the person already signed into the app with.

    on_finished, if given, is called as on_finished(game_id, user_id,
    exit_code) once the Python controller process exits. It is NOT called
    if the controller script/config is missing (nothing was started)."""
    config = GAME_LAUNCH_CONFIG.get(game_id)
    if config is None:
        print(f"[game_launcher] No launch config for '{game_id}'.")
        return

    unity_path = Path(config["unity_exe"])
    if unity_path.exists():
        try:
            subprocess.Popen([str(unity_path)])
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
    process.setProgram(sys.executable)
    process.setArguments(args)

    def _handle_finished(exit_code, exit_status):
        _active_processes.pop(game_id, None)
        print(f"[game_launcher] '{game_id}' controller exited (code={exit_code}).")
        if on_finished:
            on_finished(game_id, user_id, exit_code)

    process.finished.connect(_handle_finished)
    process.start()
    _active_processes[game_id] = process