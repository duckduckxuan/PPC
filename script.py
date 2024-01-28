import os
import socket
import multiprocessing

def server():
    host = "localhost"
    port = 8888

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen()

        print("Server waiting for connection...")
        conn, addr = server_socket.accept()
        with conn:
            print(f"Connected by: {addr}")

            # Server receives data
            data = conn.recv(1024)
            print(f"Received data: {data.decode('utf-8')}")

def client():
    host = "localhost"
    port = 8888

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((host, port))

        # Client sends data
        message = "Hello from client"
        client_socket.sendall(message.encode('utf-8'))

if __name__ == "__main__":
    # Create a Pipe to communicate between processes
    parent_conn, child_conn = multiprocessing.Pipe()

    # Create a child process (client)
    p = multiprocessing.Process(target=client)
    p.start()

    # Parent process (server)
    server()

    # Wait for the child process to finish
    p.join()
