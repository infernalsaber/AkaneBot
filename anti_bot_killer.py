import psutil
import os



while True:
    if os.path.exists("ded.txt"):
        os.remove("ded.txt")
        break
        
        if int(os.system("ps aux | grep bot.py | grep -v 'grep' | awk '{print $2}'")):
            os.system('nohup python3 -OO bot.py &')
        else:
            time.sleep(10)
    