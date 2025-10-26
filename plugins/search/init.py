# not intended to be run directly
if __name__ == "__main__":
    raise NotImplementedError("This module is not intended to be run directly. Please use the main application to load plugins.")

import os

def init():
    print("Initializing search plugin...")

def nt(driver):
    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[-1])

def searchy(data, conn, driver, placeholders):
    rest = data[7:8].strip()
    if rest.startswith("g"):
        driver.get("https://www.google.com/search?q=" + data[8:])
    elif rest.startswith("b"):
        driver.get("https://www.bing.com/search?q=" + data[8:])
    elif rest.startswith("d"):
        driver.get("https://duckduckgo.com/?q=" + data[8:])
    elif rest.startswith("y"):
        driver.get("https://de.search.yahoo.com/search?p=" + data[8:])
    elif rest.startswith("m"):
        rrest = data[8:]
        srest = rrest.split("|")
        if "g" in srest[0]:
            driver.get("https://www.google.com/search?q=" + srest[1])
            nt(driver)
        if "b" in srest[0]:
            driver.get("https://www.bing.com/search?q=" + srest[1])
            nt(driver)
        if "d" in srest[0]:
            driver.get("https://duckduckgo.com/?q=" + srest[1])
            nt(driver)
        if "y" in srest[0]:
            driver.get("https://de.search.yahoo.com/search?p=" + srest[1])
            nt(driver)

        driver.get(os.path.join(os.path.dirname(__file__), "info.html"))

    else:
        conn.send(b"ERROR: Unknown parameter\n")
        return