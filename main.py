import asyncio
import os
import subprocess
import sys

check = "ps aux | grep bot.py | grep -v 'grep' | awk '{print $2}'"


async def main_bot_loop():
    while True:
        try:
            if os.path.exists("ded.txt"):
                os.remove("ded.txt")
                break

            process = subprocess.Popen(
                check, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            if not int.from_bytes(stdout, byteorder="big"):
                print("Starting bot.")
                if not os.path.exists("logs"):
                    os.mkdir("logs")
                os.system(
                    f"nohup {sys.executable} -OO bot.py >> logs/output.log 2>&1 &"
                )

            else:
                # Bot is already up
                await asyncio.sleep(10)
        except Exception as e:
            print(e)


if __name__ == "__main__":
    asyncio.run(main_bot_loop())
