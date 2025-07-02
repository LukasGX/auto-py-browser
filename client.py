import socket
from colorama import init, Fore, Style
from tkinter import Tk, messagebox
import re
import os

# Connect to HP socket server
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('localhost', 9000))

colorama_map = {
    "Fore.BLACK": Fore.BLACK,
    "Fore.RED": Fore.RED,
    "Fore.GREEN": Fore.GREEN,
    "Fore.YELLOW": Fore.YELLOW,
    "Fore.BLUE": Fore.BLUE,
    "Fore.MAGENTA": Fore.MAGENTA,
    "Fore.CYAN": Fore.CYAN,
    "Fore.WHITE": Fore.WHITE,
    "Fore.RESET": Fore.RESET,
    "Style.BRIGHT": Style.BRIGHT,
    "Style.NORMAL": Style.NORMAL,
    "Style.RESET_ALL": Style.RESET_ALL
}

def colorama_replace(text):
    def repl(match):
        code = match.group(1)
        return colorama_map.get(code, "")
    return re.sub(r'c\[(.*?)\]', repl, text)

def ask_proceed(cmd):
    Tk().withdraw()
    return messagebox.askyesno("Confirm", f"You are trying to execute this OS command:\n\n{cmd}\n\nProceed?")

init()
print("Welcome to Auto PY Browser!")

while True:
    user_command = input("Command: ")
    client.send(user_command.encode())
    if user_command == "QUIT":
        break
    response = client.recv(1024).decode()

    if response.strip().startswith("PROCEED"):
        cmd = response[7:]
        if ask_proceed(cmd):
            os.system(cmd)
        else:
            print("Command execution cancelled")
        continue

    if response.strip() == "AUTO_START":
        print("=== AUTO block starts ===")
        while True:
            line = client.recv(1024).decode()
            if line.strip() == "AUTO_DONE":
                print("=== AUTO block done ===")
                break
            if line.strip().startswith("PROCEED"):
                cmd = line[7:]
                if ask_proceed(cmd):
                    os.system(cmd)
                else:
                    print("Command execution cancelled")
                continue
            print(colorama_replace(line.strip()))
    else:
        # Normal Response
        print("Response: ", colorama_replace(response.strip()))

client.close()
print("SP Closed.")