"""A script intended to ease the setup process"""

# TIP:
# Pass the -d or --dev flag to install developer dependencies

# So just run: "python SETUP.py -d" for with and "python SETUP.py" for without
# developer dependencies (w/o the "s) of course

import shutil
import subprocess
import sys

subprocess.call(
    [sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"]
)
# os.system("python -m pip install -q -r requirements.txt")
shutil.copy("env.template", ".env")

if "-d" in sys.argv[1:] or "--dev" in sys.argv[1:]:
    subprocess.call(
        [sys.executable, "-m", "pip", "install", "-q", "-r", "requirements_dev.txt"]
    )

    # os.system("python -m pip install -q -r requirements_dev.txt")
