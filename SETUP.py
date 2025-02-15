"""A script intended to ease the setup process"""

# TIP:
# Pass the -d or --dev flag to install developer dependencies

# So just run: "python SETUP.py -d" for with and "python SETUP.py" for without
# developer dependencies (w/o the "s) of course

import os
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    # Get python executable path
    py = sys.executable

    # Install uv package manager
    subprocess.run([py, "-m", "pip", "install", "-q", "uv"], check=True)

    # Create virtual environment
    venv_path = Path(".venv")
    if not venv_path.exists():
        os.system([py, "-m", "uv", "venv", str(venv_path)])

    if os.name == "nt":
        activate_script = venv_path / "Scripts" / "activate"
    else:
        activate_script = venv_path / "bin" / "activate"

    activate_cmd = (
        f"source {activate_script}" if sys.platform != "win32" else str(activate_script)
    )
    os.system(activate_cmd)

    subprocess.run(
        [py, "-m", "uv", "pip", "install", "-r", "requirements.txt"], check=True
    )

    if not Path(".env").exists():
        shutil.copy("env.template", ".env")
    if not Path("config.json").exists():
        shutil.copy("config.template", "config.json")

    if any(flag in sys.argv[1:] for flag in ["-d", "--dev"]):
        subprocess.run(
            [py, "-m", "pip", "install", "-q", "-r", "requirements_dev.txt"], check=True
        )


if __name__ == "__main__":
    main()
