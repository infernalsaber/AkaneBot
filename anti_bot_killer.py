import asyncio
import os

while True:
    if os.path.exists("ded.txt"):
        os.remove("ded.txt")
        break

    if os.system("ps aux | grep bot.py | grep -v 'grep' | awk '{print $2}'") == 0:
        print("Starting bot.")

        if os.name == "nt":
            os.system("nohup python -OO bot.py &")
        else:
            os.system("nohup python3 -OO bot.py &")

    else:
        asyncio.sleep(10)
