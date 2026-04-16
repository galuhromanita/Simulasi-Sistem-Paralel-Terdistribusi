

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import random
import time
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'simulasi-simple'

# Dev-friendly: jangan cache template/static terlalu agresif
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.jinja_env.auto_reload = True

socketio = SocketIO(app, cors_allowed_origins="*")

# Simple message log
messages = []


@app.route('/')
def index():
    return render_template('index_simple.html')


@app.route('/api/send', methods=['POST'])
def send_message():
    """Kirim pesan dan hitung latency"""
    data = request.json
    model = data.get('model', 'rr')  # 'rr' atau 'ps'
    message = data.get('message', '')
    sender = data.get('sender', 'Pengguna')
    
    # Generate random latency
    if model == 'rr':
        send_delay = random.uniform(50, 150)
        process_delay = random.uniform(300, 800)
        recv_delay = random.uniform(50, 150)
        total = send_delay + process_delay + recv_delay
        
        return jsonify({
            'model': 'request-response',
            'send_delay': round(send_delay, 0),
            'process_delay': round(process_delay, 0),
            'recv_delay': round(recv_delay, 0),
            'total_delay': round(total, 0)
        })
    else:  # ps
        send_delay = random.uniform(50, 150)
        ack_delay = random.uniform(30, 70)
        broadcast_delay = random.uniform(100, 300)
        total = send_delay + ack_delay + broadcast_delay
        
        return jsonify({
            'model': 'publish-subscribe',
            'send_delay': round(send_delay, 0),
            'ack_delay': round(ack_delay, 0),
            'broadcast_delay': round(broadcast_delay, 0),
            'total_delay': round(total, 0)
        })


if __name__ == '__main__':
    print("\n" + "="*50)
    print("  SIMULASI SISTEM TERDISTRIBUSI (SIMPLE)")
    print("="*50)
    print("  Request-Response vs Publish-Subscribe")
    print("  Running: http://localhost:8080")
    print("="*50 + "\n")
    socketio.run(app, debug=False, host='127.0.0.1', port=8080, allow_unsafe_werkzeug=True)
