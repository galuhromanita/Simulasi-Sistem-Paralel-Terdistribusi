# Simulasi Sistem Terdistribusi (Request–Response vs Publish–Subscribe)

Repo ini berisi **2 bagian** (dua-duanya dipakai):

1) **Visualisasi Web (Flask)**
- Menampilkan animasi alur pesan untuk **Request–Response** dan **Publish–Subscribe**
- File utama: `app_simple.py`

2) **Simulasi Chat Desktop (Tkinter)**
- **Request–Response** via **Socket**: `client_gui.py` ↔ `server.py`
- **Publish–Subscribe** via **MQTT**: `client_gui.py` ↔ **Mosquitto Broker**, topik `chat/general`

## Prasyarat
- Windows + Python 3.x + pip
- (Untuk bagian MQTT) **Mosquitto** berjalan di `localhost:1883`

## Instalasi Dependensi
Di root project:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Lalu buka:
- `http://127.0.0.1:8080`

Jika tampilan CSS tidak berubah, refresh paksa:
- `Ctrl+F5` atau buka `http://127.0.0.1:8080/?v=1`

## Menjalankan (2) Simulasi Chat Desktop (Socket + MQTT)

### A. Request–Response (Socket)
1) Jalankan server socket:

```powershell
$env:CHAT_SOCKET_PORT=5000
python server.py
```

2) Jalankan GUI client (bisa lebih dari 1 instance):

```powershell
$env:CHAT_SOCKET_PORT=5000
python client_gui.py
```

Catatan: Pastikan `CHAT_SOCKET_PORT` di server dan client sama.

### B. Publish–Subscribe (MQTT)
1) Jalankan Mosquitto broker (contoh jika Mosquitto sudah terpasang):

```powershell
mosquitto -v
```

2) Jalankan GUI client (bisa lebih dari 1 instance). Pesan publish akan diterima oleh client lain yang subscribe topik `chat/general`.

## Konfigurasi (Opsional)
- Socket:
  - `CHAT_SOCKET_HOST` (default `127.0.0.1`)
  - `CHAT_SOCKET_PORT` (default `5000`)
- MQTT (lihat [mqtt_client.py](mqtt_client.py)):
  - Broker: `localhost:1883`
  - Topik: `chat/general`

