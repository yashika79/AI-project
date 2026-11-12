import os
import sys
from pathlib import Path

pkg_dir = Path(__file__).resolve().parent
root_dir = pkg_dir.parent
venv_python = pkg_dir / "venv" / "Scripts" / "python.exe"

# 1. If executed by a system/global Python, automatically re-launch using the project venv
if venv_python.exists():
    current_exe = Path(sys.executable).resolve()
    target_exe = venv_python.resolve()
    if current_exe != target_exe and not os.environ.get("_EVENT_PLANNER_REEXEC"):
        import subprocess
        os.environ["_EVENT_PLANNER_REEXEC"] = "1"
        try:
            res = subprocess.run([str(target_exe)] + sys.argv)
            sys.exit(res.returncode)
        except Exception:
            pass

# 2. Add venv site-packages to sys.path as fallback
venv_site_packages = pkg_dir / "venv" / "Lib" / "site-packages"
if venv_site_packages.exists() and str(venv_site_packages) not in sys.path:
    sys.path.insert(0, str(venv_site_packages))

# 3. Ensure package and root dirs are on sys.path
if str(pkg_dir) not in sys.path:
    sys.path.insert(0, str(pkg_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import uvicorn

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  🎓 University Event Planner Server Starting")
    print("  🌐 Web Dashboard: http://127.0.0.1:8000")
    print("  📖 API Swagger Docs: http://127.0.0.1:8000/docs")
    print("=" * 65 + "\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
