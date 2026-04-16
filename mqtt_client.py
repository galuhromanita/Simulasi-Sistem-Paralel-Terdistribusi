import paho.mqtt.client as mqtt
import uuid

BROKER = "localhost"
TOPIC = "chat/general"

# MQTT client wrapper: connect, subscribe, terima pesan, dan publish.
class MQTTClient:
    def __init__(self, username, callback, on_status=None):
        client_id = f"chat-{uuid.uuid4().hex[:10]}"
        self.client = mqtt.Client(client_id=client_id, clean_session=True)
        self.username = username
        self.callback = callback
        self.on_status = on_status

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        try:
            self.client.connect(BROKER, 1883, 60)
            self._status("Status: mqtt connecting...")
        except Exception as e:
            self._status(f"Status: mqtt error ({e})")

        self.client.loop_start()

    def _status(self, text: str) -> None:
        if self.on_status:
            try:
                self.on_status(text)
            except Exception:
                pass

    def set_username(self, username: str) -> None:
        self.username = username

    def close(self) -> None:
        try:
            self.client.loop_stop()
        except Exception:
            pass
        try:
            self.client.disconnect()
        except Exception:
            pass

    def on_connect(self, client, userdata, flags, rc):
        # Saat terhubung, subscribe topik chat/general.
        if rc == 0:
            self._status("Status: mqtt connected")
            client.subscribe(TOPIC)
        else:
            self._status(f"Status: mqtt connect failed (rc={rc})")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            self._status("Status: mqtt disconnected (unexpected)")
        else:
            self._status("Status: mqtt disconnected")

    def on_message(self, client, userdata, msg):
        # Terima pesan dari broker lalu teruskan ke callback aplikasi.
        message = msg.payload.decode()
        self.callback(message)

    def send_message(self, message):
        # Publish pesan ke topik chat/general (model PS).
        self.client.publish(TOPIC, message)