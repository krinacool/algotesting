from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from engine import TradingEngine
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app)
engine = TradingEngine()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/save_config', methods=['POST'])
def save_config():
    config = request.json
    engine.config.update(config)
    return jsonify({"status": "success"})

@app.route('/start')
def start_algo():
    engine.start(engine.config)
    return jsonify({"status": "started"})

@app.route('/stop')
def stop_algo():
    engine.stop()
    return jsonify({"status": "stopped"})

def background_update():
    while True:
        state = engine.get_state()
        socketio.emit('update', state)
        time.sleep(1)

if __name__ == '__main__':
    update_thread = threading.Thread(target=background_update)
    update_thread.daemon = True
    update_thread.start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
