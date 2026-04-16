import socket
import threading
import time
import random
import os

clients = []
clients_lock = threading.Lock()

HOST = os.getenv("CHAT_SOCKET_HOST", "127.0.0.1")
PORT = int(os.getenv("CHAT_SOCKET_PORT", "5000"))

def handle_client(conn, addr):
    # Terima pesan client, simulasikan proses, lalu kirim balik.
    print(f"[SERVER] Connected: {addr}")
    conn.settimeout(None)
    with clients_lock:
        clients.append(conn)

    buffer = ""

    while True:
        try:
            chunk = conn.recv(4096)
            if not chunk:
                break

            buffer += chunk.decode(errors="replace")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line:
                    continue

                print(f"[SERVER] Received: {line}")

                # Simulasi proses server (delay)
                time.sleep(random.uniform(0.6, 1.2))

                dead = []
                with clients_lock:
                    current_clients = list(clients)

                for client in current_clients:
                    try:
                        client.sendall((line + "\n").encode())
                    except Exception:
                        dead.append(client)

                if dead:
                    with clients_lock:
                        for d in dead:
                            if d in clients:
                                clients.remove(d)

        except:
            break

    conn.close()
    with clients_lock:
        if conn in clients:
            clients.remove(conn)

def start_server():
    # Jalankan server socket dan terima koneksi client.
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()

    print(f"[SERVER] Running on {HOST}:{PORT}...")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    start_server()