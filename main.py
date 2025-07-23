import socket
import subprocess
import re
import time
import os
import requests
import mimetypes
import argparse
import plugins
from colorama import init, Fore
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

# Argument parsing
parser = argparse.ArgumentParser(description="Auto Browser Controller")
group = parser.add_mutually_exclusive_group()
group.add_argument("--chrome", action="store_true", help="Use Chrome browser")
group.add_argument("--firefox", action="store_true", help="Use Firefox browser")

args = parser.parse_args()

if args.chrome:
    browser_choice = "1"
elif args.firefox:
    browser_choice = "2"
else:
    # Ask user for browser choice
    print("Which browser do you want to use?")
    print("1) Chrome")
    print("2) Firefox")
    browser_choice = input("Your Choice: ")


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
init()

driver.get("https://www.example.com")

# Start the subprocess for user interaction (SP)
# Use 'python' or 'python3' depending on your system
sp_process = subprocess.Popen(
    ['python', 'client.py'],
    creationflags=subprocess.CREATE_NEW_CONSOLE
)

original_dir = os.getcwd()
print(f"Original directory: {original_dir}")

# Set up socket server for communication with SP
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('localhost', 9000))
server.listen(1)
print("Waiting for SP to connect...")

conn, addr = server.accept()
print("SP connected.")

plugin_commands = plugins.list_plugin_commands()

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
            # Platzhalter-Ersatz
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
            # Platzhalter-Ersatz
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
        elif element_select_with == "cs ":
            css = data[9:].strip()
            if placeholders and css.startswith("{") and css.endswith("}"):
                key = css[1:-1]
                css = placeholders.get(key, css)

            # Erweiterter SPECIAL-[CONTENT=...] Support (auch mit :not(KLASSE))
            m = re.match(r'^([^\[]+)\[CONTENT=([^\]]+)\](?::not\(([^)]+)\))?$', css)
            if m:
                tag = m.group(1).strip()
                expected_content = m.group(2).strip()
                excluded_class = m.group(3).strip() if m.group(3) else None
                try:
                    elements = driver.find_elements("css selector", tag)
                    for e in elements:
                        if e.text.strip() == expected_content.strip():  # alternativ .lower(), siehe oben
                            if excluded_class and excluded_class in e.get_attribute("class").split():
                                continue
                            actions.move_to_element(e).perform()
                            e.click()
                            conn.send(b"OK\n")
                            return
                    conn.send(b"ERROR: No element with this content for selector\n")
                except Exception as e:
                    conn.send(f"ERROR: {str(e)}\n".encode())
            else:
                # Normale CSS-Selektorverwendung
                try:
                    element = driver.find_element("css selector", css)
                    actions.move_to_element(element).perform()
                    element.click()
                    conn.send(b"OK\n")
                except Exception as e:
                    conn.send(f"ERROR: {str(e)}\n".encode())

        # NEU: Content-exakt (ct)
        elif element_select_with == "ct ":
            content_text = data[9:].strip()
            # Placeholder-Ersatz
            if placeholders and content_text.startswith("{") and content_text.endswith("}"):
                key = content_text[1:-1]
                content_text = placeholders.get(key, content_text)
            try:
                # Alle sichtbaren Elemente holen und vergleichen
                elements = driver.find_elements("xpath", "//*[text()]")
                element = next(e for e in elements if e.text == content_text)
                actions.move_to_element(element).perform()
                element.click()
                conn.send(b"OK\n")
            except StopIteration:
                conn.send(b"ERROR: No element with this exact content\n")
            except Exception as e:
                conn.send(f"ERROR: {str(e)}\n".encode())
        # NEU: Regex-Text (rt)
        elif element_select_with == "rt ":
            pattern = data[9:].strip()
            # Placeholder-Ersatz
            if placeholders and pattern.startswith("{") and pattern.endswith("}"):
                key = pattern[1:-1]
                pattern = placeholders.get(key, pattern)
            try:
                # XPath: Nur sichtbare Elemente mit Text (du kannst es anpassen)
                elements = driver.find_elements("xpath", "//*[text()]")
                element = next(e for e in elements if re.search(pattern, e.text))
                actions.move_to_element(element).perform()
                element.click()
                conn.send(b"OK\n")
            except StopIteration:
                conn.send(b"ERROR: No element matching regex found\n")
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
                        time.sleep(0.3)
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
            context = {'driver': driver, 're': re, 'placeholders': placeholders}
            result = eval(condition, globals(), context)
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
            time.sleep(seconds)
            driver.implicitly_wait(seconds)
            conn.send(b"OK\n")
        except ValueError:
            conn.send(b"ERROR: Invalid WAIT command, must be an integer\n")
    
    # UNTIL command
    elif data.startswith("UNTIL "):
        # Syntax: UNTIL condition|command_if_true
        parts = data[6:].split("|")
        condition = parts[0].strip()
        command_if_true = parts[1].strip() if len(parts) > 1 else None

        # Replace placeholder if needed
        if placeholders and condition.startswith("{") and condition.endswith("}"):
            key = condition[1:-1]
            condition = placeholders.get(key, condition)

        max_wait = 180  # max wait time in seconds
        waited = 0
        while True:
            try:
                context = {'driver': driver, 're': re, 'placeholders': placeholders}
                result = eval(condition, globals(), context)
                if result:
                    if command_if_true and command_if_true.upper() != "NOTHING":
                        execute(command_if_true, placeholders, driver, conn)
                    break
                else:
                    time.sleep(0.5)
                    waited += 0.5
                    if waited >= max_wait:
                        conn.send(b"ERROR: UNTIL timeout\n")
                        return True
            except Exception as e:
                conn.send(f"ERROR: {str(e)}\n".encode())
                break

    # SET command
    elif data.startswith("SET "):
        # Syntax: SET key=value
        key_value = data[4:].strip()
        if "=" in key_value:
            key, value = key_value.split("=", 1)
            key = key.strip()
            value = value.strip()
            
            # --- NEU: []-Ausdruck auswerten! ---
            # Falls value z.B. "[driver.current_url]" ist
            if value.startswith("[") and value.endswith("]"):
                eval_expr = value[1:-1]
                context = {'driver': driver, 're': re, 'placeholders': placeholders}
                try:
                    value_evaluated = str(eval(eval_expr, globals(), context))
                except Exception as e:
                    conn.send(f"ERROR: SET-EVAL: {str(e)}\n".encode())
                    return
                value = value_evaluated
            # --- ENDE NEU ---

            placeholders[key] = value
            conn.send(b"OK\n")
        else:
            conn.send(b"ERROR: Invalid SET command, must be in the form key=value\n")

    # EXECUTE command
    elif data.startswith("EXECUTE "):
        # Syntax: EXECUTE_JS <js_code>
        js_code = data[8:].strip()
        try:
            # Execute JavaScript in the current browser tab
            result = driver.execute_script(js_code)
            # Send result (if any) back to client
            if result is not None:
                conn.send(f"{result}\n".encode())
            else:
                conn.send(b"OK\n")
        except Exception as e:
            conn.send(f"ERROR: {str(e)}\n".encode())

    # OS command
    elif data.startswith("OS "):
        # Syntax: OS <command>
        os_command = data[3:].strip()
        try:
            conn.send(f"PROCEED {os_command}".encode())
        except Exception as e:
            conn.send(f"ERROR: {str(e)}\n".encode())

    # PATH command
    elif data.startswith("PATH "):
        # Syntax: PATH <path>
        path = data[5:].strip()

        if path == "RESET":
            os.chdir(original_dir)
            conn.send(f"Changed directory to: {os.getcwd()} (RESET)\n".encode())
        else:
            # Replace placeholder if needed
            if placeholders and path.startswith("{") and path.endswith("}"):
                key = path[1:-1]
                path = placeholders.get(key, path)
            try:
                if os.path.exists(path):
                    os.chdir(path)
                    conn.send(f"Changed directory to: {os.getcwd()}\n".encode())
                else:
                    conn.send(f"PATH NOT FOUND: {path}\n".encode())
            except Exception as e:
                conn.send(f"ERROR: {str(e)}\n".encode())

    elif data.startswith("DOWNLOAD "):
        element_select_with = data[9:12]
        selector_value = data[12:].strip()
        # Platzhalter-Ersatz
        if placeholders and selector_value.startswith("{") and selector_value.endswith("}"):
            key = selector_value[1:-1]
            selector_value = placeholders.get(key, selector_value)
        element = None
        url = None

        try:
            # 1. Element finden (wie bei CLICK)
            if element_select_with == "id ":
                element = driver.find_element("id", selector_value)
            elif element_select_with == "cl ":
                class_names = selector_value.strip().split()
                css_selector = "." + ".".join(class_names)
                element = driver.find_element("css selector", css_selector)
            elif element_select_with == "cs ":
                element = driver.find_element("css selector", selector_value)
            elif element_select_with == "ct ":
                elements = driver.find_elements("xpath", "//*[text()]")
                element = next(e for e in elements if e.text.strip() == selector_value.strip())
            elif element_select_with == "rt ":
                pattern = selector_value
                elements = driver.find_elements("xpath", "//*[text()]")
                element = next(e for e in elements if re.search(pattern, e.text))
            else:
                conn.send(b"ERROR: Invalid element selector\n")
                return

            # 2. Downloadbare URL bestimmen
            tag = element.tag_name.lower()
            if tag == "a":
                url = element.get_attribute("href")
            elif tag == "img":
                url = element.get_attribute("src")
            elif tag == "video" or tag == "audio":
                url = element.get_attribute("src")
                if not url:
                    sources = element.find_elements("tag name", "source")
                    for source in sources:
                        test_url = source.get_attribute("src")
                        if test_url:
                            url = test_url
                            break
            else:
                # Generischer Versuch
                url = element.get_attribute("href") or element.get_attribute("src")

            if not url:
                conn.send(b"ERROR: No downloadable URL found in element (href/src missing)\n")
                return

            # 3. Download durchführen
            r = requests.get(url, stream=True)
            content_type = r.headers.get('Content-Type', '')
            ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
            filename = url.split("/")[-1].split("?")[0]
            if not filename or "." not in filename:
                filename = "downloaded_file"
            if ext and not filename.endswith(ext):
                filename += ext

            # Neuer Block: Prüfe auf {video_name} im Placeholder
            video_name_from_placeholder = placeholders.get("video_name") if placeholders else None
            dest_filename = video_name_from_placeholder or filename

            with open(dest_filename, "wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            conn.send(f"Downloaded: {dest_filename}\n".encode())

        except StopIteration:
            conn.send(b"ERROR: No matching element for selector\n")
        except Exception as e:
            conn.send(f"ERROR: {str(e)}\n".encode())

    elif data.startswith("SWITCHTAB "):
        which = data[10:].strip().upper()
        try:
            handles = driver.window_handles
            if which == "LAST":
                driver.switch_to.window(handles[-1])
                conn.send(b"OK\n")
            elif which == "FIRST":
                driver.switch_to.window(handles[0])
                conn.send(b"OK\n")
            elif which.isdigit():  # z.B. SWITCHTAB 1
                idx = int(which)
                driver.switch_to.window(handles[idx])
                conn.send(b"OK\n")
            else:
                conn.send(b"ERROR: Unknown SWITCHTAB argument\n")
        except Exception as e:
            conn.send(f"ERROR: {str(e)}\n".encode())

    # NEWTAB command
    elif data.startswith("NEWTAB"):
        try:
            driver.execute_script("window.open('');")
            conn.send(b"OK\nc[Fore.YELLOW]You have to switch to the new tab manually with SWITCHTAB!c[Fore.RESET]\n")
        except Exception as e:
            conn.send(f"ERROR: {str(e)}\n".encode())

    # KILLTAB command
    elif data.startswith("KILLTAB"):
        try:
            handles = driver.window_handles
            if len(handles) > 1:
                driver.close()
                time.sleep(0.3)
                driver.switch_to.window(handles[0])
                conn.send(b"OK\n")
            else:
                conn.send(b"ERROR: Cannot close the last tab\n")
        except Exception as e:
            conn.send(f"ERROR: {str(e)}\n".encode())

    # QUIT command
    elif data == "QUIT":
        return True
    
    # HELP command
    elif data == "HELP":
        help_text = """
c[Fore.CYAN]c[Style.BRIGHT]==== PY-AUTO-BROWSER - COMMAND OVERVIEW ====c[Style.NORMAL]
== Navigation ==c[Fore.RESET]
GET <url>
    Opens the specified URL (e.g. https://example.com)

BACK
    Navigates back in browser history

FORWARD
    Navigates forward in browser history

REFRESH
    Reloads the current page

c[Fore.CYAN]== Interaction ==c[Fore.RESET]
CLICK id <id>
CLICK cl <class names>
CLICK cs <CSS selector>
CLICK ct <exact visible text>
CLICK rt <regex pattern>
    Clicks the first visible element matching the specified method

FILL id <id> <text>
FILL cl <class> <text>
    Fills an input field with the provided text

SEND id <id>
SEND cl <class>
    Sends ENTER key to the element

c[Fore.CYAN]== Downloads ==c[Fore.RESET]
DOWNLOAD id <id>
DOWNLOAD cl <classes>
DOWNLOAD cs <CSS selector>
DOWNLOAD ct <text>
DOWNLOAD rt <regex>
    Downloads linked content (e.g. video href/src). If {video_name} is set, it will be used as the filename.

c[Fore.CYAN]== Scripting ==c[Fore.RESET]
AUTO <filename.auto>[|key=value|...]
    Executes each line of the script (.auto) file. Supports dynamic placeholders.

WAIT <seconds>
    Waits the given number of seconds and sets implicit wait

CONDITION <expression>|<CommandIfTrue>|<CommandIfFalse>
    Python-like IF-THEN-ELSE condition that executes depending on expression

UNTIL <expression>|<command>
    Repeats every 0.5s until condition is True (max 180s), then executes the command

NOTHING
    Used when no command should run in CONDITION or UNTIL

c[Fore.CYAN]== Placeholder Management ==c[Fore.RESET]
SET key=value
    Stores a dynamic variable (e.g. SET url=https://example.com)

    Supports evaluated expressions like:
        SET current_url=[driver.current_url]

PRINT <string with {placeholder}>
    Sends a message to the client, with placeholders replaced

c[Fore.CYAN]== Browser Tabs ==c[Fore.RESET]
SWITCHTAB LAST
SWITCHTAB FIRST
SWITCHTAB <index>
    Switches to the selected browser tab

NEWTAB
    Opens a new browser tab

KILLTAB
    Closes the current browser tab and switches to the first tab

c[Fore.CYAN]== Page Info ==c[Fore.RESET]
TITLE
    Returns the current page title

URL
    Returns the current page URL

META <meta-name>
    Returns the value of <meta name="..."> content attribute

COOKIES GET
COOKIES DEL
    Gets or deletes all website cookies

c[Fore.CYAN]== Files & Screenshots ==c[Fore.RESET]
SCREENSHOT <filename>
    Saves a screenshot of the current view
    (Default: "screenshot.png")

PATH <directory>
PATH RESET
    Changes (or resets) the current working directory

c[Fore.CYAN]== JavaScript and OS Commands ==c[Fore.RESET]
EXECUTE <js-code>
    Executes JavaScript in the webpage context

OS <command>
    Sends a system shell command (confirmation only)

c[Fore.CYAN]== System ==c[Fore.RESET]
QUIT
    Cleanly closes all connections and exits the program

HELP
    Displays this help overview

        """
        conn.send(b"HELP_START\n")
        chunk_size = 800
        chunks = [help_text[i:i+chunk_size] for i in range(0, len(help_text), chunk_size)]

        for chunk in chunks:
            conn.send(chunk.encode())
            time.sleep(0.02)

        conn.send(b"HELP_DONE\n")

    # Plugin commands
    elif data.split(" ")[0] in plugin_commands:
        splitt = data.split(" ")

        conn.send(b"MORELINE_START")
        command_ref = plugin_commands[splitt[0]]
        plugins.execute_plugin_command(data, command_ref, driver, conn, placeholders)
        conn.send(b"MORELINE_DONE")

    # Unknown command
    else:
        conn.send(b"ERROR: Unknown command\n")

placeholders = {}

while True:
    data = conn.recv(1024).decode()
    if not data:
        continue
    else:
        if execute(data, placeholders, driver, conn) == True:
            break
    
conn.close()
driver.quit()
print("HP Closed.")
