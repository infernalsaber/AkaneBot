import time
import subprocess
import os

check = "ps aux | grep bot.py | grep -v 'grep' | awk '{print $2}'"

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

            if os.name == "nt":
                os.system("nohup python -OO bot.py >> logs/output.log 2>&1 &")
            else:
                os.system("nohup python3 -OO bot.py >> logs/output.log 2>&1 &")

        else:
            print("Bot is already up")
            time.sleep(10)
    except Exception as e:
        print(e)
# print(type(os.system("ps aux | grep bot.py | grep -v 'grep' | awk '{print $2}'")))
# print(int(os.system("ps aux | grep bot.py | grep -v 'grep' | awk '{print $2}'")) == 0)


# print(stdout, type(stdout))
# x = int.from_bytes(stdout, byteorder='big')
# print(x, x == 0)
