# not intended to be run directly
if __name__ == "__main__":
    raise NotImplementedError("This module is not intended to be run directly. Please use the main application to load plugins.")

import os
import yaml
from time import sleep

def init():
    print("Initializing search plugin...")

def timed(data, conn, driver, placeholders):
    # data is expected like: someprefix<delay>|<signal>|... ; grab remainder and split
    rest = data[6:]
    parts = rest.split(" ")

    # parse delay from first part
    try:
        delay_str = parts[0].strip() if len(parts) > 0 else ""
        delay = int(delay_str)
    except (ValueError, IndexError):
        conn.send(b"ERROR: Invalid delay value\n")
        return

    conn.send(f"Waiting for {delay} seconds...\n".encode())
    # set implicit wait and sleep
    try:
        driver.implicitly_wait(delay)
    except Exception:
        # if driver isn't available or doesn't support implicit wait, ignore
        pass
    sleep(delay)
    conn.send(b"Done waiting.\n")

    # load actions mapping from actions.yaml: signal -> action name
    actions = {}
    with open(os.path.join(os.path.dirname(__file__), "actions.yaml"), "r", encoding="utf-8") as f:
        actions_data = yaml.safe_load(f) or {}
        for action in actions_data.get("actions", []):
            signal = action.get("signal", "")
            action_name = action.get("action", "")
            if signal:
                actions[signal] = action_name

    # get provided signal (second part)
    signal_given = parts[1].strip() if len(parts) > 1 else ""

    action_to_perform = actions.get(signal_given)
    if action_to_perform:
        action_func = globals().get(action_to_perform)
        if callable(action_func):
            try:
                action_func(data, conn, driver, placeholders)
            except Exception as e:
                conn.send(f"ERROR: Exception while running action '{action_to_perform}': {e}\n".encode())
        else:
            conn.send(f"ERROR: Action '{action_to_perform}' not found or not callable\n".encode())
    else:
        conn.send(b"ERROR: Unknown signal\n")

def screenshot(data, conn, driver, placeholders):
    screenshot_path = os.path.join(os.path.dirname(__file__), "screenshot.png")
    try:
        driver.save_screenshot(screenshot_path)
        conn.send(f"Screenshot saved to {screenshot_path}\n".encode())
    except Exception as e:
        conn.send(f"ERROR: Could not take screenshot: {e}\n".encode())

def fullscreenshot(data, conn, driver, placeholders):
    screenshot_path = os.path.join(os.path.dirname(__file__), "full_screenshot.png")
    try:
        original_size = driver.get_window_size()
        required_width = driver.execute_script('return document.body.parentNode.scrollWidth')
        required_height = driver.execute_script('return document.body.parentNode.scrollHeight')
        driver.set_window_size(required_width, required_height)
        driver.save_screenshot(screenshot_path)
        driver.set_window_size(original_size['width'], original_size['height'])
        conn.send(f"Full page screenshot saved to {screenshot_path}\n".encode())
    except Exception as e:
        conn.send(f"ERROR: Could not take full screenshot: {e}\n".encode())