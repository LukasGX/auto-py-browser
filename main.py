import socket
import subprocess
import re
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
# import chrome
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options as ChromeOptions
# import firefox
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options as FirefoxOptions

# Ask user for browser choice
browser_choice = input("Which do you want to use? (1) Chrome (2) Firefox: ")
if browser_choice == "1":
    # Start Chrome browser using WebDriver Manager
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

    chrome_service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
if browser_choice == "2":
    # Start Firefox browser using WebDriver Manager
    firefox_service = FirefoxService(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=firefox_service)

actions = ActionChains(driver)

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
                actions.move_to_element(element).perform()
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
                actions.move_to_element(element).perform()
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
                actions.move_to_element(element).perform()
                element.click()
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
                actions.move_to_element(element).perform()
                element.click()
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
            # Signal start of AUTO block
            conn.send(b"AUTO_START\n")
            with open(filename, "r", encoding="utf-8") as file:
                commands = file.readlines()
                for cmd in commands:
                    cmd = cmd.strip()
                    if cmd:
                        # conn.send(f"Executing: {cmd}\n".encode())
                        should_quit = execute(cmd, auto_placeholders, driver, conn)
                        if should_quit:
                            conn.send(b"AUTO_DONE\n")
                            return True
                        sleep(0.3)
            # Signal end of AUTO block
            conn.send(b"AUTO_DONE\n")
        except Exception as e:
            conn.send(f"ERROR: {str(e)}\n".encode())

    # PRINT command
    elif data.startswith("PRINT "):
        message = data[6:].strip()
        # Replace all placeholders in the message
        def replace_placeholder(match):
            key = match.group(1)
            return str(placeholders.get(key, f"{{{key}}}"))
        # Replace every {key} by its value in placeholders
        message = re.sub(r"\{(\w+)\}", replace_placeholder, message)
        conn.send(f"{message}\n".encode())

    # CONDITION command
    elif data.startswith("CONDITION "):
        # Remove "CONDITION " and split by '|'
        parts = data[10:].split("|")
        # Strip whitespace from all parts
        parts = [part.strip() for part in parts]
        condition = parts[0]
        command_if_true = parts[1] if len(parts) > 1 else None
        command_if_false = parts[2] if len(parts) > 2 else None

        # Replace placeholder if needed
        if placeholders and condition.startswith("{") and condition.endswith("}"):
            key = condition[1:-1]
            condition = placeholders.get(key, condition)
        # Evaluate the condition
        try:
            result = eval(condition)
            if result:
                # conn.send(b"CONDITION is TRUE\n")
                if command_if_true and command_if_true.upper() != "NOTHING":
                    # Execute the command for True
                    execute(command_if_true, placeholders, driver, conn)
            else:
                # conn.send(b"CONDITION is FALSE\n")
                if command_if_false and command_if_false.upper() != "NOTHING":
                    # Execute the command for False
                    execute(command_if_false, placeholders, driver, conn)
        except Exception as e:
            conn.send(f"ERROR: {str(e)}\n".encode())

    # NOTHING command
    elif data.startswith("NOTHING"):
        conn.send(b"OK\n")

    # COOKIES command
    elif data.startswith("COOKIES "):
        action = data[8:].strip().upper()
        if action == "GET":
            cookies = driver.get_cookies()
            conn.send(f"COOKIES: {cookies}\n".encode())
        elif action == "DEL":
            driver.delete_all_cookies()
            conn.send(b"OK\n")
        else:
            conn.send(b"ERROR: Invalid COOKIES command\n")
    
    # URL command
    elif data.startswith("URL"):
        url = driver.current_url
        conn.send(f"URL: {url}\n".encode())

    # TITLE command
    elif data.startswith("TITLE"):
        title = driver.title
        conn.send(f"TITLE: {title}\n".encode())

    # SCREENSHOT command
    elif data.startswith("SCREENSHOT"):
        filename = data[10:].strip()
        if not filename:
            filename = "screenshot.png"
        try:
            driver.save_screenshot(filename)
            conn.send(f"Screenshot saved as {filename}\n".encode())
        except Exception as e:
            conn.send(f"ERROR: {str(e)}\n".encode())

    # META command
    elif data.startswith("META"):
        meta_name = data[4:].strip()
        try:
            meta_element = driver.find_element("xpath", f"//meta[@name='{meta_name}']")
            content = meta_element.get_attribute("content")
            conn.send(f"META {meta_name}: {content}\n".encode())
        except Exception as e:
            conn.send(f"ERROR: {str(e)}\n".encode())

    # WAIT command
    elif data.startswith("WAIT "):
        try:
            seconds = int(data[5:].strip())
            sleep(seconds)
            driver.implicitly_wait(seconds)
            conn.send(b"OK\n")
        except ValueError:
            conn.send(b"ERROR: Invalid WAIT command, must be an integer\n")

    # SET command
    elif data.startswith("SET "):
        # Syntax: SET key=value
        key_value = data[4:].strip()
        if "=" in key_value:
            key, value = key_value.split("=", 1)
            key = key.strip()
            value = value.strip()
            
            placeholders[key] = value
            conn.send(b"OK\n")
        else:
            conn.send(b"ERROR: Invalid SET command, must be in the form key=value\n")

    # QUIT command
    elif data == "QUIT":
        return True

    # Unknown command
    else:
        conn.send(b"ERROR: Unknown command\n")

placeholders = {}

while True:
    data = conn.recv(1024).decode()
    if not data:
        continue
    else:
        if execute(data, placeholders, driver, conn):
            break
    
conn.close()
driver.quit()
print("HP Closed.")
