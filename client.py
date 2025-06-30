import socket

# Connect to HP socket server
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('localhost', 9000))

print("Welcome to Auto PY Browser!")

while True:
    user_command = input("Command: ")
    client.send(user_command.encode())
    if user_command == "QUIT":
        break
    response = client.recv(1024).decode()
    if response.strip() == "AUTO_START":
        print("=== AUTO block starts ===")
        while True:
            line = client.recv(1024).decode()
            if line.strip() == "AUTO_DONE":
                print("=== AUTO block done ===")
                break
            print(line.strip())
    else:
        # Normal Response
        print("Response: ", response.strip())

client.close()
print("SP Closed.")