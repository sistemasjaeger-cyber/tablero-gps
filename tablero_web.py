import requests
import json
from flask import Flask, jsonify, render_template_string, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import os

# --- INICIALIZACIÓN Y CONFIGURACIÓN ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'cambia-esta-clave-por-algo-secreto')

# --- CONFIGURACIÓN DE LA API DE GPS ---
API_BASE_URL = 'http://5.78.94.130' 
USER_API_HASH = os.environ.get('USER_API_HASH') 
COMMAND_ENDPOINT = '/api/send_gprs_command' 
DEVICES_ENDPOINT = '/api/get_devices'

# --- CONFIGURACIÓN DE TELEGRAM ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# --- DICCIONARIO DE DISPOSITIVOS ---
VEHICULOS = {
    "Freightliner":      {"id": "472", "imei": "863719069189398"},
    "Toma de Fuerza1":   {"id": "128", "imei": "807397674"},
    "Prueba_Unidad":     {"id": "475", "imei": "863719069189364"},
    "Prueba_QuintaR":    {"id": "362", "imei": "007352724"}
}

# --- USUARIOS ---
USERS = {
    "admin": { "password_hash": generate_password_hash("admin123"), "role": "administrador" },
    "cliente": { "password_hash": generate_password_hash("cliente123"), "role": "cliente" }
}

# --- FUNCIÓN DE TELEGRAM ---
def send_telegram_notification(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Advertencia: Variables de Telegram no configuradas.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Error al enviar notificación de Telegram: {e}")

# --- RUTAS DE AUTENTICACIÓN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_data = USERS.get(username)
        if user_data and check_password_hash(user_data['password_hash'], password):
            session['username'] = username
            session['role'] = user_data['role']
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            message = f"✅ <b>Inicio de sesión exitoso</b>\n\n👤 <b>Usuario:</b> {username}\n📦 <b>Rol:</b> {user_data['role']}\n🌐 <b>IP:</b> {ip_address}"
            send_telegram_notification(message)
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- RUTA PRINCIPAL DEL TABLERO ---
@app.route('/')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template_string(HTML_TEMPLATE, username=session.get('username'))

# --- RUTAS DE LA API ---
@app.route('/api/get_devices_status')
def get_devices_status_api():
    if 'username' not in session:
        return jsonify({"error": "No autorizado"}), 401
    
    # Simulación de datos para el frontend. La API real debería devolver estos estados.
    devices_to_display = {
        "Freightliner": {"id": "472", "online": "online", "speed": 0, "lat": 25.68, "lng": -100.31, "engine_status": "desbloqueado"},
        "Prueba":       {"id": "475", "online": "online", "speed": 0, "lat": 19.43, "lng": -99.13, 
                         "unit_status": "desbloqueado",
                         "fifth_wheel_status": "bloqueado"
                        }
    }
    return jsonify(devices_to_display)

@app.route('/api/send_command', methods=['POST'])
def send_command_api():
    if 'username'
