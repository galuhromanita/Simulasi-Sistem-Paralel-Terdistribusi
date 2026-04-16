import tkinter as tk
from tkinter import ttk
import socket
import threading
import time
import uuid
import random
from dataclasses import dataclass, field
import os
from mqtt_client import MQTTClient


MSG_PREFIX = "MSG"  # MSG|<id>|<sent_epoch>|<username>|<text>

SOCKET_HOST = os.getenv("CHAT_SOCKET_HOST", "127.0.0.1")
SOCKET_PORT = int(os.getenv("CHAT_SOCKET_PORT", "5000"))


def _now_hms() -> str:
    return time.strftime("%H:%M:%S")


# Buat payload berisi id+timestamp untuk hitung delay.
def _make_payload(username: str, text: str) -> tuple[str, str, float]:
    msg_id = uuid.uuid4().hex[:8]
    sent_epoch = time.time()
    payload = f"{MSG_PREFIX}|{msg_id}|{sent_epoch}|{username}|{text}"
    return payload, msg_id, sent_epoch


# Parse payload untuk ambil id/timestamp/sender/isi pesan.
def _parse_payload(payload: str):
    # Returns (msg_id, sent_epoch, username, text) or None if unknown format
    try:
        if not payload.startswith(MSG_PREFIX + "|"):
            return None
        parts = payload.split("|", 4)
        if len(parts) != 5:
            return None
        _, msg_id, sent_epoch_s, username, text = parts
        return msg_id, float(sent_epoch_s), username, text
    except Exception:
        return None


@dataclass
class Metrics:
    sent: int = 0
    received: int = 0
    delays: list[float] = field(default_factory=list)

    def add_delay(self, delay: float) -> None:
        self.delays.append(delay)

    def summary(self) -> dict[str, str]:
        if not self.delays:
            return {
                "last": "-",
                "avg": "-",
                "min": "-",
                "max": "-",
            }

        last = self.delays[-1]
        avg = sum(self.delays) / len(self.delays)
        return {
            "last": f"{last:.2f}s",
            "avg": f"{avg:.2f}s",
            "min": f"{min(self.delays):.2f}s",
            "max": f"{max(self.delays):.2f}s",
        }

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Distributed System Simulation — Nilai 4")
        self.root.minsize(980, 720)

        self.username = "User"

        # ===== STYLE =====
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure("App.TFrame", padding=12)
        self.style.configure("Top.TFrame", padding=(12, 10, 12, 6))
        self.style.configure("Bottom.TFrame", padding=(12, 8, 12, 12))
        self.style.configure("Title.TLabel", font=("Segoe UI", 12, "bold"))
        self.style.configure("Sub.TLabel", font=("Segoe UI", 9))

        # ===== ROOT LAYOUT =====
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        top = ttk.Frame(self.root, style="Top.TFrame")
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Distributed System Simulation", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(top, text="Request-Response vs Publish-Subscribe", style="Sub.TLabel").grid(
            row=1, column=0, sticky="w", pady=(2, 0)
        )

        user_frame = ttk.Frame(top)
        user_frame.grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Label(user_frame, text="Username:").grid(row=0, column=0, sticky="e", padx=(0, 6))
        self.username_var = tk.StringVar(value=self.username)
        self.username_entry = ttk.Entry(user_frame, width=18, textvariable=self.username_var)
        self.username_entry.grid(row=0, column=1, sticky="e")
        self.status_var = tk.StringVar(value="Status: connecting...")
        ttk.Label(user_frame, textvariable=self.status_var, style="Sub.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="e", pady=(4, 0)
        )

        main = ttk.Frame(self.root, style="App.TFrame")
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)
        main.rowconfigure(1, weight=0)

        # LEFT (REQUEST-RESPONSE)
        self.req_metrics = Metrics()
        req_group = ttk.LabelFrame(main, text="Request-Response (Socket)")
        req_group.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        req_group.columnconfigure(0, weight=1)
        req_group.rowconfigure(0, weight=1)

        self.req_box = tk.Text(req_group, height=20, wrap="word")
        req_scroll = ttk.Scrollbar(req_group, orient="vertical", command=self.req_box.yview)
        self.req_box.configure(yscrollcommand=req_scroll.set)
        self.req_box.grid(row=0, column=0, sticky="nsew")
        req_scroll.grid(row=0, column=1, sticky="ns")

        self.req_stats_var = tk.StringVar(value="Sent: 0 | Recv: 0 | Last: - | Avg: - | Min: - | Max: -")
        ttk.Label(req_group, textvariable=self.req_stats_var, style="Sub.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(6, 6)
        )

        # RIGHT (PUB-SUB)
        self.pub_metrics = Metrics()
        pub_group = ttk.LabelFrame(main, text="Publish-Subscribe (MQTT)")
        pub_group.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        pub_group.columnconfigure(0, weight=1)
        pub_group.rowconfigure(0, weight=1)

        self.pub_box = tk.Text(pub_group, height=20, wrap="word")
        pub_scroll = ttk.Scrollbar(pub_group, orient="vertical", command=self.pub_box.yview)
        self.pub_box.configure(yscrollcommand=pub_scroll.set)
        self.pub_box.grid(row=0, column=0, sticky="nsew")
        pub_scroll.grid(row=0, column=1, sticky="ns")

        self.pub_stats_var = tk.StringVar(value="Sent: 0 | Recv: 0 | Last: - | Avg: - | Min: - | Max: -")
        ttk.Label(pub_group, textvariable=self.pub_stats_var, style="Sub.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(6, 6)
        )

        # FLOW (Visual)
        flow_group = ttk.LabelFrame(main, text="Flow Timeline (Visual)")
        flow_group.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        flow_group.columnconfigure(0, weight=1)
        flow_group.rowconfigure(0, weight=1)

        self.flow_box = tk.Text(flow_group, height=8, wrap="word")
        flow_scroll = ttk.Scrollbar(flow_group, orient="vertical", command=self.flow_box.yview)
        self.flow_box.configure(yscrollcommand=flow_scroll.set)
        self.flow_box.grid(row=0, column=0, sticky="nsew")
        flow_scroll.grid(row=0, column=1, sticky="ns")

        # INPUT
        bottom = ttk.Frame(self.root, style="Bottom.TFrame")
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        self.entry_var = tk.StringVar()
        self.entry = ttk.Entry(bottom, textvariable=self.entry_var)
        self.entry.grid(row=0, column=0, sticky="ew")
        self.entry.bind("<Return>", lambda _e: self.send_message())

        self.send_btn = ttk.Button(bottom, text="Send", command=self.send_message)
        self.send_btn.grid(row=0, column=1, padx=(10, 0))

        # SOCKET
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        try:
            self.sock.connect((SOCKET_HOST, SOCKET_PORT))
            self.status_var.set(f"Status: socket connected ({SOCKET_HOST}:{SOCKET_PORT})")
        except Exception as e:
            self.status_var.set(
                f"Status: socket error ({e}) — cek port {SOCKET_HOST}:{SOCKET_PORT} / set CHAT_SOCKET_PORT"
            )

        threading.Thread(target=self.receive_socket, daemon=True).start()

        # MQTT
        self.mqtt = MQTTClient(self.username, self.receive_mqtt, on_status=self._on_mqtt_status)

        # Simulated network delay ranges (seconds)
        self.req_net_delay_range = (0.05, 0.25)
        self.pub_net_delay_range = (0.05, 0.20)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.entry.focus_set()

        self._refresh_stats()

        self._socket_buffer = ""

    def _on_mqtt_status(self, status: str) -> None:
        # UI-thread safe
        self.root.after(0, lambda: self.status_var.set(status))

    def _on_close(self) -> None:
        try:
            self.mqtt.close()
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass
        self.root.destroy()

    def _ui(self, fn, *args):
        self.root.after(0, lambda: fn(*args))

    def _append_text(self, box: tk.Text, text: str) -> None:
        box.insert(tk.END, text)
        box.see(tk.END)

    def _log_req(self, text: str) -> None:
        self._append_text(self.req_box, text)

    def _log_pub(self, text: str) -> None:
        self._append_text(self.pub_box, text)

    def _log_flow(self, text: str) -> None:
        self._append_text(self.flow_box, text)

    def _refresh_stats(self) -> None:
        req = self.req_metrics.summary()
        pub = self.pub_metrics.summary()
        self.req_stats_var.set(
            f"Sent: {self.req_metrics.sent} | Recv: {self.req_metrics.received} | Last: {req['last']} | Avg: {req['avg']} | Min: {req['min']} | Max: {req['max']}"
        )
        self.pub_stats_var.set(
            f"Sent: {self.pub_metrics.sent} | Recv: {self.pub_metrics.received} | Last: {pub['last']} | Avg: {pub['avg']} | Min: {pub['min']} | Max: {pub['max']}"
        )

    # ===== SEND =====
    def send_message(self):
        # Kirim pesan lewat Socket (RR) dan MQTT (PS) untuk dibandingkan.
        msg = self.entry_var.get().strip()
        self.entry_var.set("")

        if not msg:
            return

        self.username = self.username_var.get().strip() or "User"
        self.mqtt.set_username(self.username)

        timestamp = _now_hms()

        payload, msg_id, sent_epoch = _make_payload(self.username, msg)

        # REQUEST-RESPONSE
        self.req_metrics.sent += 1
        self._ui(self._log_req, f"[{timestamp}] Client → Server\n")
        self._ui(self._log_req, f"ID: {msg_id} | Pesan: {msg}\n\n")
        self._ui(self._log_flow, f"[{timestamp}] REQ  {msg_id}  Client → Server\n")

        threading.Thread(
            target=self._send_socket_payload,
            args=(payload,),
            daemon=True,
        ).start()

        # PUB-SUB
        self.pub_metrics.sent += 1
        self._ui(self._log_pub, f"[{timestamp}] Publish ke Broker\n")
        self._ui(self._log_pub, f"ID: {msg_id} | Pesan: {msg}\n\n")
        self._ui(self._log_flow, f"[{timestamp}] PUB  {msg_id}  Client → Broker\n")

        threading.Thread(
            target=self._send_mqtt_payload,
            args=(payload,),
            daemon=True,
        ).start()

        self._ui(self._refresh_stats)

    def _send_socket_payload(self, payload: str) -> None:
        try:
            time.sleep(random.uniform(*self.req_net_delay_range))
            self.sock.sendall((payload + "\n").encode())
        except Exception as e:
            self._ui(self._log_req, f"[ERROR] Socket send gagal: {e}\n\n")

    def _send_mqtt_payload(self, payload: str) -> None:
        try:
            time.sleep(random.uniform(*self.pub_net_delay_range))
            self.mqtt.send_message(payload)
        except Exception as e:
            self._ui(self._log_pub, f"[ERROR] MQTT publish gagal: {e}\n\n")

    # ===== RECEIVE SOCKET =====
    def receive_socket(self):
        while True:
            try:
                raw = self.sock.recv(4096)
                if not raw:
                    break
                chunk = raw.decode(errors="replace")
                self._socket_buffer += chunk

                while "\n" in self._socket_buffer:
                    line, self._socket_buffer = self._socket_buffer.split("\n", 1)
                    if not line:
                        continue
                    self._ui(self._handle_socket_message, line)

            except:
                break

    def _handle_socket_message(self, payload: str) -> None:
        # Hitung delay RR dari timestamp payload dan tampilkan ke panel RR.
        end = time.time()
        timestamp = _now_hms()

        parsed = _parse_payload(payload)
        if parsed:
            msg_id, sent_epoch, username, text = parsed
            delay = round(end - sent_epoch, 2)
            self.req_metrics.received += 1
            self.req_metrics.add_delay(delay)
            self._log_req(f"[{timestamp}] Server → Client\n")
            self._log_req(f"ID: {msg_id} | Dari: {username}\n")
            self._log_req(f"Pesan: {text}\n")
            self._log_req(f"Delay: {delay}s\n\n")
            self._log_flow(f"[{timestamp}] REQ  {msg_id}  Server → Client  ({delay:.2f}s)\n")
        else:
            self.req_metrics.received += 1
            self._log_req(f"[{timestamp}] Server → Client\n")
            self._log_req(f"Pesan: {payload}\n\n")

        self._refresh_stats()

    # ===== RECEIVE MQTT =====
    def receive_mqtt(self, msg):
        # Always hop to UI thread (paho callback thread isn't Tk-safe)
        self._ui(self._handle_mqtt_message, msg)

    def _handle_mqtt_message(self, msg: str) -> None:
        # Hitung delay PS dari timestamp payload dan tampilkan ke panel PS.
        end = time.time()
        timestamp = _now_hms()

        parsed = _parse_payload(msg)
        if parsed:
            msg_id, sent_epoch, username, text = parsed
            delay = round(end - sent_epoch, 2)
            self.pub_metrics.received += 1
            self.pub_metrics.add_delay(delay)
            self._log_pub(f"[{timestamp}] Broker → Semua Client\n")
            self._log_pub(f"ID: {msg_id} | Dari: {username}\n")
            self._log_pub(f"Pesan: {text}\n")
            self._log_pub(f"Delay: {delay}s\n\n")
            self._log_flow(f"[{timestamp}] PUB  {msg_id}  Broker → Clients  ({delay:.2f}s)\n")
        else:
            self.pub_metrics.received += 1
            self._log_pub(f"[{timestamp}] Broker → Semua Client\n")
            self._log_pub(f"Pesan: {msg}\n\n")

        self._refresh_stats()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()