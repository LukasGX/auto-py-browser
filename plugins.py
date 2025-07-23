import importlib
import os
import yaml

def folder_found(folder, dir, plugin_folders):
    full_path = os.path.join(folder, dir)
    if os.path.isdir(full_path):
        print(f"Folder found: {full_path}")
        plugin_folders.append(full_path)
    else:
        print("Skipping file:", full_path)

def file_found(full_path, file, plugin_commands):
    file_path = os.path.join(full_path, file)
    if not os.path.isfile(file_path):
        print(f"Skipping non-file: {file_path}")
        return

    if file == "init.py":
        print(f"Init File found: {file_path}")
    elif file == "plugin.yaml":
        print(f"Plugin configuration file found: {file_path}")
        process_config(file_path, plugin_commands)
    else:
        print(f"File found: {file_path}")

def process_config(file_path, plugin_commands):
    try:
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)

            commands = data.get("plugin", {}).get("commands", [])
            if isinstance(commands, list) and commands:
                for cmd in commands:
                    command_name = cmd.get("name", "Unnamed")
                    command_ref = cmd.get("ref", "undefined")
                    plugin_commands[command_name] = os.path.join(os.path.dirname(file_path), command_ref)
                output = ", ".join(plugin_commands.keys())
            else:
                output = "No commands defined"

            print(f"""
===== Plugin Configuration for {os.path.dirname(file_path)} =====
Name: {data.get('plugin', {}).get('name', 'Unknown')}
Version: {data.get('plugin', {}).get('version', 'Unknown')}
Author: {data.get('plugin', {}).get('author', 'Unknown')}
Description: {data.get('plugin', {}).get('description', 'No description available')}
Commands: {output}
===================================================
                  """)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

def main():
    folder = "plugins"

    if not os.path.exists(folder):
        print(f"Folder '{folder}' does not exist.")

    plugin_folders = []

    # Check if the folder is a directory
    for dir in os.listdir(folder):
        folder_found(folder, dir, plugin_folders)

    plugin_commands = {}

    # Check for files in the found plugin folders
    for dir in plugin_folders:
        for file in os.listdir(dir):
            file_found(dir, file, plugin_commands)

    return plugin_commands

def list_plugin_commands():
    return main()

def execute_plugin_command(data, command_ref, driver, conn, placeholders):
    command_ref_clean = os.path.dirname(command_ref)

    module_name = os.path.basename(command_ref_clean)  # → "search"
    init_path = os.path.join(command_ref_clean, "init.py")

    spec = importlib.util.spec_from_file_location(module_name, init_path)
    plugin_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plugin_module)

    if hasattr(plugin_module, module_name):
        getattr(plugin_module, module_name)(data, conn, driver, placeholders)
    else:
        print(f"Function '{module_name}()' not found in plugin.")

if __name__ == "__main__":
    main()