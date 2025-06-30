import socket
import subprocess
import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
# import chrome
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
# import firefox
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager

# Ask user for browser choice
browser_choice = input("Which do you want to use? (1) Chrome (2) Firefox: ")
if browser_choice == "1":
    # Start Chrome browser using WebDriver Manager
    chrome_service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=chrome_service)
if browser_choice == "2":
    # Start Firefox browser using WebDriver Manager
    firefox_service = FirefoxService(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=firefox_service)

driver.get("https://www.example.com")

# Start the subprocess for user interaction (SP)
# Use 'python' or 'python3' depending on your system
sp_process = subprocess.Popen(
    ['python', 'client.py'],
    creationflags=subprocess.CREATE_NEW_CONSOLE
)

# Set up socket server for communication with SP
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('localhost', 9000))
server.listen(1)
print("Waiting for SP to connect...")

conn, addr = server.accept()
print("SP connected.")

def execute(data, placeholders, driver, conn):
    """
    Executes browser commands received via socket.
    Supports placeholders for dynamic values (e.g. {search}).
    """
    # GET command
    if data.startswith("GET "):
        url = data[4:].strip()
        # Replace placeholder if needed
        if placeholders and url.startswith("{") and url.endswith("}"):
            key = url[1:-1]
            url = placeholders.get(key, url)
        driver.get(url)
        conn.send(b"OK\n")

    # CLICK command
    elif data.startswith("CLICK "):
        element_select_with = data[6:9]
        if element_select_with == "id ":
            element_id = data[9:].strip()
            # Replace placeholder if needed
            if placeholders and element_id.startswith("{") and element_id.endswith("}"):
                key = element_id[1:-1]
                element_id = placeholders.get(key, element_id)
            try:
                element = driver.find_element("id", element_id)
                element.click()
                conn.send(b"OK\n")
            except Exception as e:
                conn.send(f"ERROR: {str(e)}\n".encode())
        elif element_select_with == "cl ":
            class_names = data[9:].strip()
            # Replace placeholder if needed
            if placeholders and class_names.startswith("{") and class_names.endswith("}"):
                key = class_names[1:-1]
                class_names = placeholders.get(key, class_names)
            class_names_list = class_names.strip().split()
            css_selector = "." + ".".join(class_names_list)
            try:
                element = driver.find_element("css selector", css_selector)
                element.click()
                conn.send(b"OK\n")
            except Exception as e:
                conn.send(f"ERROR: {str(e)}\n".encode())
        else:
            conn.send(b"ERROR: Invalid element selector\n")

    # FILL command
    elif data.startswith("FILL "):
        element_select_with = data[5:8]
        rest = data[8:].strip()
        # Split at "|" if present, else try to split at first space
        if "|" in rest:
            class_or_id, text_to_fill = map(str.strip, rest.split("|", 1))
        else:
            split_index = rest.find(" ")
            if split_index != -1:
                class_or_id = rest[:split_index]
                text_to_fill = rest[split_index+1:]
            else:
                class_or_id = rest
                text_to_fill = ""
        # Replace placeholder in text_to_fill if needed
        if placeholders and text_to_fill.startswith("{") and text_to_fill.endswith("}"):
            key = text_to_fill[1:-1]
            text_to_fill = placeholders.get(key, text_to_fill)
        # Replace placeholder in class_or_id if needed
        if placeholders and class_or_id.startswith("{") and class_or_id.endswith("}"):
            key = class_or_id[1:-1]
            class_or_id = placeholders.get(key, class_or_id)
        if element_select_with == "id ":
            try:
                element = driver.find_element("id", class_or_id)
                element.clear()
                element.send_keys(text_to_fill)
                conn.send(b"OK\n")
            except Exception as e:
                conn.send(f"ERROR: {str(e)}\n".encode())
        elif element_select_with == "cl ":
            class_names_list = class_or_id.strip().split()
            css_selector = "." + ".".join(class_names_list)
            try:
                element = driver.find_element("css selector", css_selector)
                element.clear()
                element.send_keys(text_to_fill)
                conn.send(b"OK\n")
            except Exception as e:
                conn.send(f"ERROR: {str(e)}\n".encode())
        else:
            conn.send(b"ERROR: Invalid element selector\n")

    # SEND command (e.g. send ENTER)
    elif data.startswith("SEND "):
        element_select_with = data[5:8]
        rest = data[8:].strip()
        # Replace placeholder in rest if needed
        if placeholders and rest.startswith("{") and rest.endswith("}"):
            key = rest[1:-1]
            rest = placeholders.get(key, rest)
        if element_select_with == "id ":
            try:
                element = driver.find_element("id", rest)
                element.send_keys(Keys.ENTER)
                conn.send(b"OK\n")
            except Exception as e:
                conn.send(f"ERROR: {str(e)}\n".encode())
        elif element_select_with == "cl ":
            class_names_list = rest.strip().split()
            css_selector = "." + ".".join(class_names_list)
            try:
                element = driver.find_element("css selector", css_selector)
                element.send_keys(Keys.ENTER)
                conn.send(b"OK\n")
            except Exception as e:
                conn.send(f"ERROR: {str(e)}\n".encode())
        else:
            conn.send(b"ERROR: Invalid element selector\n")

    # Navigation commands
    elif data.startswith("BACK"):
        driver.back()
        conn.send(b"OK\n")
    elif data.startswith("FORWARD"):
        driver.forward()
        conn.send(b"OK\n")
    elif data.startswith("REFRESH"):
        driver.refresh()
        conn.send(b"OK\n")

    # AUTO command: Execute commands from file, optionally with placeholders
    elif data.startswith("AUTO "):
        file_and_options = data[5:].strip()
        # Syntax: AUTO filename.auto|key1=val1|key2=val2
        parts = [part.strip() for part in file_and_options.split("|")]
        filename = parts[0]
        # Parse additional placeholders from options
        auto_placeholders = dict(placeholders) if placeholders else {}
        for opt in parts[1:]:
            if "=" in opt:
                k, v = opt.split("=", 1)
                auto_placeholders[k.strip()] = v.strip()
        try:
            with open(filename, "r", encoding="utf-8") as file:
                commands = file.readlines()
                for cmd in commands:
                    cmd = cmd.strip()
                    if cmd:
                        should_quit = execute(cmd, auto_placeholders, driver, conn)
                        if should_quit:
                            return True
            conn.send(b"OK\n")
        except Exception as e:
            conn.send(f"ERROR: {str(e)}\n".encode())

    # QUIT command
    elif data == "QUIT":
        return True

    # Unknown command
    else:
        conn.send(b"ERROR: Unknown command\n")

while True:
    data = conn.recv(1024).decode()
    if not data:
        continue
    else:
        if execute(data, False, driver, conn):
            break
    
conn.close()
driver.quit()
print("HP Closed.")
