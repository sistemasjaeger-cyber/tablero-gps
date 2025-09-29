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

# --- LISTA DE VEHÍCULOS ---
VEHICULOS = {
    "Freightliner":    {"id": "472", "imei": "863719069189398"},
    "Toma de Fuerza1": {"id": "128", "imei": "807397674"}
}

# --- USUARIOS (VERSIÓN SIMPLE SIN BASE DE DATOS) ---
USERS = {
    "admin": {
        "password_hash": generate_password_hash("admin123"),
        "role": "administrador"
    },
    "cliente": {
        "password_hash": generate_password_hash("cliente123"),
        "role": "cliente"
    }
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

# --- RUTAS DE AUTENTicación ---
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
    
    # Esta función ahora solo devolverá el estado del Freightliner al frontend
    # ... (Aquí va tu lógica completa para obtener el estado real de la API) ...
    
    # Simulación de datos para el ejemplo
    # En tu versión real, aquí procesarías la respuesta de la API para determinar el 'engine_status'
    # Por ejemplo, si la velocidad es > 0, engine_status podría ser 'en_uso'
    all_devices_from_api = {
        "Freightliner": {"id": "472", "online": "online", "speed": 0, "lat": 25.6866, "lng": -100.3161, "engine_status": "bloqueado"} 
    }
    devices_to_display = {"Freightliner": all_devices_from_api.get("Freightliner")}
    return jsonify(devices_to_display)

@app.route('/api/send_command', methods=['POST'])
def send_command_api():
    if 'username' not in session:
        return jsonify({"status": 0, "message": "No autorizado"}), 401
    if session.get('role') == 'cliente':
        return jsonify({"status": 0, "message": "Acción no permitida"}), 403

    data = request.get_json()
    command_type = data.get('type')
    
    if command_type == 'pto_off':
        target_device_info = VEHICULOS.get("Toma de Fuerza1")
        target_device_id = target_device_info['id']
        command_message = "  setdigout 1" # <-- EJEMPLO, USA TU COMANDO REAL PARA PTO
    else:
        target_device_id = data.get('device_id')
        if command_type == 'stop':
            command_message = '  setdigout 1'
        elif command_type == 'resume':
            command_message = '  setdigout 0'
        else:
            return jsonify({"status": 0, "message": "Tipo de comando no válido."}), 400

    url = f"{API_BASE_URL}{COMMAND_ENDPOINT}"
    payload = {'user_api_hash': USER_API_HASH, 'device_id': target_device_id, 'type': 'custom', 'data': command_message}
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"status": 0, "message": f"Error al enviar comando: {e}"}), 500

# --- PLANTILLAS HTML ---
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>Iniciar Sesión</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-900 flex items-center justify-center h-screen">
    <div class="bg-gray-800 p-8 rounded-lg shadow-lg w-full max-w-sm">
        <h2 class="text-2xl font-bold text-center text-white mb-6">Acceso al Tablero</h2>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}{% for category, message in messages %}
            <div class="bg-red-500 text-white p-3 rounded mb-4">{{ message }}</div>
            {% endfor %}{% endif %}
        {% endwith %}
        <form method="POST">
            <div class="mb-4"><label for="username" class="block text-gray-300 mb-2">Usuario</label><input type="text" name="username" class="w-full bg-gray-700 border border-gray-600 p-2 rounded text-white focus:outline-none focus:border-indigo-500" required></div>
            <div class="mb-6"><label for="password" class="block text-gray-300 mb-2">Contraseña</label><input type="password" name="password" class="w-full bg-gray-700 border border-gray-600 p-2 rounded text-white focus:outline-none focus:border-indigo-500" required></div>
            <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded">Entrar</button>
        </form>
    </div>
</body></html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Tablero de Control GPS</title><script src="https://cdn.tailwindcss.com"></script><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"><style>body{font-family:'Inter',sans-serif}</style></head>
<body class="bg-gray-900 text-white">
    <div class="container mx-auto p-4 md:p-8">
        <header class="text-center mb-12">
             <div class="flex justify-between items-center">
                <span></span><h1 class="text-4xl md:text-5xl font-bold text-indigo-400">Tablero de Control de Flota</h1>
                <a href="/logout" class="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg">Cerrar Sesión</a>
            </div>
            <p class="text-gray-400 mt-2">Bienvenido, <strong>{{ username }}</strong>.</p>
        </header>
        <main id="device-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"></main>
    </div>
    <footer class="text-center p-4 mt-8">
        <p class="text-sm text-gray-500">Desarrollado por Gerardo De La Torre</p>
    </footer>
    <script>
    function showOnMap(lat, lng) {
        if (lat && lng && lat !== 'None' && lng !== 'None') {
            const url = `http://googleusercontent.com/maps.google.com/2{lat},${lng}`;
            window.open(url, '_blank');
        } else {
            alert('Ubicación no disponible para este vehículo.');
        }
    }

    async function sendCommand(deviceId, commandType, buttonElement) {
        const statusDiv = document.getElementById(`status-${deviceId}`);
        statusDiv.innerHTML = '<span class="text-blue-400">Enviando...</span>';
        const parentCard = buttonElement.closest('.device-card');
        const buttons = parentCard.querySelectorAll('button');
        buttons.forEach(b => b.disabled = true);
        try {
            const response = await fetch('/api/send_command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_id: deviceId, type: commandType })
            });
            const result = await response.json();
            if (response.ok && (result.status === 1 || response.status === 200) ) {
                statusDiv.innerHTML = '<span class="text-green-400">¡Comando enviado!</span>';
                setTimeout(fetchDevices, 2000); 
            } else {
                statusDiv.innerHTML = `<span class="text-red-400">Error: ${result.message || 'Fallo inesperado.'}</span>`;
            }
        } catch (err) {
            statusDiv.innerHTML = '<span class="text-red-400">Error de Conexión.</span>';
        } finally {
            setTimeout(() => { statusDiv.innerHTML = ''; }, 4000);
        }
    }

    async function fetchDevices() {
        const grid = document.getElementById('device-grid');
        try {
            const response = await fetch('/api/get_devices_status');
            const data = await response.json();
            grid.innerHTML = '';
            for (const deviceName in data) {
                const device = data[deviceName];
                
                // --- LÓGICA PARA TODOS LOS INDICADORES Y BOTONES ---

                // 1. Botón Inteligente de Encendido/Apagado
                let toggleButtonHTML = '';
                let lockStatusText = '';
                let lockStatusColor = '';

                if (device.engine_status === 'bloqueado') {
                    toggleButtonHTML = `<button onclick="sendCommand('${device.id}', 'resume', this)" class="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg">Encender Motor</button>`;
                    lockStatusText = 'Motor Bloqueado';
                    lockStatusColor = 'bg-red-600';
                } else {
                    toggleButtonHTML = `<button onclick="sendCommand('${device.id}', 'stop', this)" class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg">Apagar Motor</button>`;
                    lockStatusText = 'Motor Desbloqueado';
                    lockStatusColor = 'bg-cyan-600';
                }

                // 2. Indicador de Movimiento
                let motionStatusText = '';
                let motionStatusColor = '';
                if (device.speed > 0) {
                    motionStatusText = 'En Movimiento';
                    motionStatusColor = 'bg-green-600';
                } else {
                    motionStatusText = 'Parado';
                    motionStatusColor = 'bg-gray-500';
                }
                
                // --- CONSTRUCCIÓN DE LA TARJETA HTML ---
                const card = `
                    <div class="device-card bg-gray-800 p-6 rounded-2xl shadow-lg border border-gray-700">
                        <div class="flex justify-between items-start">
                            <h2 class="text-xl font-bold text-white">${deviceName}</h2>
                            <span class="text-xs text-gray-400">ID: ${device.id}</span>
                        </div>
                        
                        <div class="space-y-3 my-4">
                            <div class="flex justify-center items-center p-2 rounded-lg ${lockStatusColor}">
                                <span class="font-semibold text-sm">${lockStatusText}</span>
                            </div>
                            <div class="flex justify-center items-center p-2 rounded-lg ${motionStatusColor}">
                                <span class="font-semibold text-sm">${motionStatusText}</span>
                            </div>
                        </div>

                        <div class="flex items-center text-lg my-4">
                            <svg class="w-6 h-6 mr-2 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                            <span class="font-semibold">${device.speed}</span>
                            <span class="text-sm text-gray-400 ml-1">km/h</span>
                        </div>
                        
                        <div class="mt-6 space-y-3">
                            <button onclick="showOnMap(${device.lat}, ${device.lng})" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg">Ver en Mapa</button>
                            ${toggleButtonHTML}
                            <button onclick="sendCommand('${device.id}', 'pto_off', this)" class="w-full bg-yellow-600 hover:bg-yellow-700 text-white font-semibold py-2 px-4 rounded-lg">Apagar Toma de Fuerza</button>
                        </div>
                        <div id="status-${device.id}" class="text-center text-xs mt-3 h-4"></div>
                    </div>
                `;
                grid.innerHTML += card;
            }
        } catch (err) {
            console.error("Error fetching devices:", err);
            grid.innerHTML = '<p class="text-red-400">Error al cargar el vehículo.</p>';
        }
    }
    document.addEventListener('DOMContentLoaded', fetchDevices);
    </script>
</body></html>
"""
