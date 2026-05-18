"""各層 Y=0.5,1.0,1.5,2.0 の heatmap.py を順に実行する。"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
for layer in ["Y=0.5", "Y=1.0", "Y=1.5", "Y=2.0"]:
    script = HERE / layer / "heatmap.py"
    if not script.is_file():
        print(f"skip missing: {script}")
        continue
    r = subprocess.run([sys.executable, str(script)], cwd=str(HERE / layer))
    if r.returncode != 0:
        sys.exit(r.returncode)
sys.exit(0)
