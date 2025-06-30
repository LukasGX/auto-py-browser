import socket

# Connect to HP socket server
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('localhost', 9000))

while True:
    user_command = input("Your command (e.g. GET https://... or QUIT): ")
    client.send(user_command.encode())
    if user_command == "QUIT":
        break
    response = client.recv(1024).decode()
    print("Response:", response.strip())

client.close()
print("SP Closed.")