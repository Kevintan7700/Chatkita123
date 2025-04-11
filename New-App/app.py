from flask import Flask, render_template, redirect, url_for, request, session
from flask_socketio import SocketIO, send, emit
import json
import os

app = Flask(__name__)
app.secret_key = 'secretkey'
socketio = SocketIO(app)

users = {}  # Dictionary untuk menyimpan username berdasarkan session ID
CHAT_HISTORY_FILE = 'chat_history.json'
chat_history = []

def load_chat_history():
    global chat_history
    if os.path.exists(CHAT_HISTORY_FILE):
        try:
            with open(CHAT_HISTORY_FILE, 'r') as f:
                chat_history = json.load(f)
            print(f"Riwayat chat berhasil dimuat dari {CHAT_HISTORY_FILE}")
        except Exception as e:
            print(f"Gagal memuat riwayat chat dari {CHAT_HISTORY_FILE}: {e}")
            chat_history = []
    else:
        print(f"File {CHAT_HISTORY_FILE} tidak ditemukan, memulai riwayat chat baru.")
        chat_history = []

def save_chat_history():
    try:
        with open(CHAT_HISTORY_FILE, 'w') as f:
            json.dump(chat_history, f)
        print(f"Riwayat chat berhasil disimpan ke {CHAT_HISTORY_FILE}")
    except Exception as e:
        print(f"Gagal menyimpan riwayat chat ke {CHAT_HISTORY_FILE}: {e}")

# Muat riwayat chat saat server dimulai
load_chat_history()

@app.route('/')
def index():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        if username in ['daddy', 'mami']:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return "Username tidak valid! Hanya 'daddy' atau 'mami' yang bisa masuk.", 403
    return render_template('login.html')

@socketio.on('connect')
def handle_connect():
    if 'username' in session:
        user_username = session['username']
        users[request.sid] = user_username
        print(f"User {user_username} connected with session ID: {request.sid}")
        # Kirim riwayat chat ke pengguna yang baru terhubung
        for message_data in chat_history:
            emit('message', json.dumps(message_data), room=request.sid)
    else:
        print("Anonymous user connected.")

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in users:
        username = users.pop(request.sid)
        print(f"User {username} disconnected.")
    else:
        print("Anonymous user disconnected.")

@socketio.on('message')
def handle_message(msg):
    if request.sid in users:
        username = users[request.sid]
        try:
            payload = json.loads(msg)
            message_text = payload.get('message')
            is_image = payload.get('isImage', False)
            data = {'username': username, 'message': message_text, 'isImage': is_image}
            chat_history.append(data)
            save_chat_history() # Simpan riwayat setelah ada pesan baru
            emit('message', json.dumps(data), broadcast=True)
        except json.JSONDecodeError:
            # Handle pesan teks biasa
            data = {'username': username, 'message': msg, 'isImage': False}
            chat_history.append(data)
            save_chat_history() # Simpan riwayat setelah ada pesan baru
            emit('message', json.dumps(data), broadcast=True)
    else:
        print(f"Anonymous message: {msg}")
        try:
            payload = json.loads(msg)
            message_text = payload.get('message')
            is_image = payload.get('isImage', False)
            data = {'username': 'Guest', 'message': message_text, 'isImage': is_image}
            chat_history.append(data)
            save_chat_history() # Simpan riwayat setelah ada pesan baru
            emit('message', json.dumps(data), broadcast=True)
        except json.JSONDecodeError:
            # Handle pesan teks biasa dari pengguna anonim
            data = {'username': 'Guest', 'message': msg, 'isImage': False}
            chat_history.append(data)
            save_chat_history() # Simpan riwayat setelah ada pesan baru
            emit('message', json.dumps(data), broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)