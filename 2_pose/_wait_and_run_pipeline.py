import time, subprocess, sys
from pathlib import Path

ROOT = Path(r"c:\projects\MOTIONTRACK\bias_evaluation_,mediapipe_unity_ieej2026")
MP_DIR = ROOT / "2_pose" / "mediapipe_processed_csv"
TARGET = 576
LOG = ROOT / "2_pose" / "pipeline_auto_run.log"

def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def count_csv():
    return len(list(MP_DIR.rglob("CapturedFrames_*.csv"))) if MP_DIR.exists() else 0

def mediapipe_running():
    # crude: look for mediapipe_video_processor in process list via tasklist
    import os
    out = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/V"], text=True, errors="ignore")
    # Also check log growth / processor via wmic
    try:
        w = subprocess.check_output(
            ["wmic", "process", "where", "name='python.exe'", "get", "ProcessId,CommandLine"],
            text=True, errors="ignore")
        return "mediapipe_video_processor" in w
    except Exception:
        return True  # assume running if check fails

log(f"waiter start: csv={count_csv()}/{TARGET}")
while True:
    n = count_csv()
    running = mediapipe_running()
    log(f"progress: {n}/{TARGET} running={running}")
    if n >= TARGET and not running:
        break
    if n >= TARGET and running:
        # finished writing, wait for process exit
        log("count reached; waiting for process exit...")
        time.sleep(10)
        if not mediapipe_running():
            break
    time.sleep(60)

log("MediaPipe done. Starting run_v2_pipeline.py")
r = subprocess.run([sys.executable, str(ROOT / "run_v2_pipeline.py")], cwd=str(ROOT))
log(f"pipeline exit code: {r.returncode}")
sys.exit(r.returncode)
