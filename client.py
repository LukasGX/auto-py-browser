import socket
from colorama import init, Fore, Back, Style
from tkinter import Tk, messagebox
import re
import os

# Connect to HP socket server
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('localhost', 9000))

colorama_map = {
    # Foreground colors
    "Fore.BLACK": Fore.BLACK,
    "Fore.RED": Fore.RED,
    "Fore.GREEN": Fore.GREEN,
    "Fore.YELLOW": Fore.YELLOW,
    "Fore.BLUE": Fore.BLUE,
    "Fore.MAGENTA": Fore.MAGENTA,
    "Fore.CYAN": Fore.CYAN,
    "Fore.WHITE": Fore.WHITE,
    "Fore.LIGHTBLACK_EX": Fore.LIGHTBLACK_EX,
    "Fore.LIGHTRED_EX": Fore.LIGHTRED_EX,
    "Fore.LIGHTGREEN_EX": Fore.LIGHTGREEN_EX,
    "Fore.LIGHTYELLOW_EX": Fore.LIGHTYELLOW_EX,
    "Fore.LIGHTBLUE_EX": Fore.LIGHTBLUE_EX,
    "Fore.LIGHTMAGENTA_EX": Fore.LIGHTMAGENTA_EX,
    "Fore.LIGHTCYAN_EX": Fore.LIGHTCYAN_EX,
    "Fore.LIGHTWHITE_EX": Fore.LIGHTWHITE_EX,
    "Fore.RESET": Fore.RESET,

    # Background colors
    "Back.BLACK": Back.BLACK,
    "Back.RED": Back.RED,
    "Back.GREEN": Back.GREEN,
    "Back.YELLOW": Back.YELLOW,
    "Back.BLUE": Back.BLUE,
    "Back.MAGENTA": Back.MAGENTA,
    "Back.CYAN": Back.CYAN,
    "Back.WHITE": Back.WHITE,
    "Back.LIGHTBLACK_EX": Back.LIGHTBLACK_EX,
    "Back.LIGHTRED_EX": Back.LIGHTRED_EX,
    "Back.LIGHTGREEN_EX": Back.LIGHTGREEN_EX,
    "Back.LIGHTYELLOW_EX": Back.LIGHTYELLOW_EX,
    "Back.LIGHTBLUE_EX": Back.LIGHTBLUE_EX,
    "Back.LIGHTMAGENTA_EX": Back.LIGHTMAGENTA_EX,
    "Back.LIGHTCYAN_EX": Back.LIGHTCYAN_EX,
    "Back.LIGHTWHITE_EX": Back.LIGHTWHITE_EX,
    "Back.RESET": Back.RESET,

    # Styles
    "Style.BRIGHT": Style.BRIGHT,
    "Style.NORMAL": Style.NORMAL,
    "Style.DIM": Style.DIM,
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
    elif response.strip() == "HELP_START":
        while True:
            help_chunk = client.recv(1024).decode()
            if help_chunk.strip() == "HELP_DONE":
                print("=== HELP block done ===")
                break
            print(colorama_replace(help_chunk.strip()))
    else:
        # Normal Response
        print(colorama_replace(response.strip()))

client.close()
print("SP Closed.")