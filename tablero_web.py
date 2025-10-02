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
    url = f"https.api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
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

# --- RUTA DE LA API PARA ENVIAR COMANDOS ---
@app.route('/api/send_command', methods=['POST'])
def send_command_api():
    if 'username' not in session: return jsonify({"status": 0, "message": "No autorizado"}), 401
    if session.get('role') == 'cliente': return jsonify({"status": 0, "message": "Acción no permitida"}), 403

    data = request.get_json()
    command_type = data.get('type')
    
    target_device = None
    command_message = None

    if command_type in ['stop', 'resume']:
        target_device = VEHICULOS.get("Freightliner")
        command_message = '  setdigout 1' if command_type == 'stop' else '  setdigout 0'
    elif command_type in ['block_unit', 'unblock_unit']:
        target_device = VEHICULOS.get("Prueba_Unidad")
        command_message = '  setdigout 1' if command_type == 'block_unit' else '  setdigout 0'
    elif command_type in ['block_fifth_wheel', 'unblock_fifth_wheel']:
        target_device = VEHICULOS.get("Prueba_QuintaR")
        imei = target_device['imei']
        command_message = f'ST300CMD;{imei};02;Disable1' if command_type == 'block_fifth_wheel' else f'ST300CMD;{imei};02;Enable1'
    else:
        return jsonify({"status": 0, "message": "Tipo de comando no válido."}), 400

    if not target_device: return jsonify({"status": 0, "message": "Dispositivo objetivo no encontrado."}), 404

    url = f"{API_BASE_URL}{COMMAND_ENDPOINT}"
    payload = {'user_api_hash': USER_API_HASH, 'device_id': target_device['id'], 'type': 'custom', 'data': command_message}
    
    print("--- ENVIANDO COMANDO ---")
    print(f"Payload: {payload}")
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        print("--- RESPUESTA DEL SERVIDOR GPS ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        print("--- ERROR EN LA COMUNICACIÓN ---")
        print(f"Error: {e}")
        return jsonify({"status": 0, "message": f"Error al enviar comando: {e}"}), 500

# --- PLANTILLAS HTML ---
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>Iniciar Sesión</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-900 flex items-center justify-center h-screen">
    <div class="bg-gray-800 p-8 rounded-lg shadow-lg w-full max-w-sm">
        <h2 class="text-2xl font-bold text-center text-white mb-6">Acceso al Tablero</h2>
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
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Tablero de Diagnóstico GPS</title><script src="https://cdn.tailwindcss.com"></script><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"><style>body{font-family:'Inter',sans-serif}</style></head>
<body class="bg-gray-900 text-white">
    <div class="container mx-auto p-4 md:p-8">
        <header class="text-center mb-12">
             <div class="flex justify-between items-center">
                <span></span><h1 class="text-4xl md:text-5xl font-bold text-indigo-400">Panel de Diagnóstico</h1>
                <a href="/logout" class="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg">Cerrar Sesión</a>
            </div>
            <p class="text-gray-400 mt-2">Bienvenido, <strong>{{ username }}</strong>.</p>
        </header>
        
        <main class="grid grid-cols-1 md:grid-cols-2 gap-8">
            
            <div class="bg-gray-800 p-6 rounded-lg">
                <h2 class="text-2xl font-bold text-red-400 mb-4">BLOQUEAR UNIDADES</h2>
                <div class="space-y-3">
                    <button onclick="sendCommand('472', 'stop', this)" class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-4 rounded-lg">Bloquear Motor (Freightliner)</button>
                    <button onclick="sendCommand('475', 'block_unit', this)" class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-4 rounded-lg">Bloquear Unidad (Prueba)</button>
                    <button onclick="sendCommand('362', 'block_fifth_wheel', this)" class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-4 rounded-lg">Bloquear 5ta Rueda (Prueba)</button>
                </div>
            </div>

            <div class="bg-gray-800 p-6 rounded-lg">
                <h2 class="text-2xl font-bold text-green-400 mb-4">DESBLOQUEAR UNIDADES</h2>
                <div class="space-y-3">
                    <button onclick="sendCommand('472', 'resume', this)" class="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-4 rounded-lg">Desbloquear Motor (Freightliner)</button>
                    <button onclick="sendCommand('475', 'unblock_unit', this)" class="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-4 rounded-lg">Desbloquear Unidad (Prueba)</button>
                    <button onclick="sendCommand('362', 'unblock_fifth_wheel', this)" class="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-4 rounded-lg">Desbloquear 5ta Rueda (Prueba)</button>
                </div>
            </div>

        </main>

        <div id="status-message" class="mt-8 text-center text-lg h-6"></div>

    </div>
    <footer class="text-center p-4 mt-8">
        <p class="text-sm text-gray-500">Desarrollado por Gerardo De La Torre</p>
    </footer>
    <script>
    async function sendCommand(deviceId, commandType, buttonElement) {
        const statusDiv = document.getElementById('status-message');
        statusDiv.innerHTML = '<span class="text-blue-400">Enviando comando...</span>';
        
        // Deshabilitar todos los botones para evitar envíos múltiples
        document.querySelectorAll('button').forEach(b => b.disabled = true);

        try {
            const response = await fetch('/api/send_command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_id: deviceId, type: commandType }) // deviceId no se usa en todos los casos, pero lo enviamos por consistencia
            });
            const result = await response.json();
            if (response.ok && (result.status === 1 || response.status === 200) ) {
                statusDiv.innerHTML = '<span class="text-green-400">¡Éxito! Revisa los logs y el vehículo.</span>';
            } else {
                statusDiv.innerHTML = `<span class="text-red-400">Error: ${result.message || 'Fallo inesperado.'} Revisa los logs.</span>`;
            }
        } catch (err) {
            statusDiv.innerHTML = '<span class="text-red-400">Error de Conexión. Revisa los logs.</span>';
        } finally {
            // Habilitar todos los botones después de un tiempo
            setTimeout(() => { 
                document.querySelectorAll('button').forEach(b => b.disabled = false);
                statusDiv.innerHTML = 'Listo para la siguiente prueba.';
             }, 4000);
        }
    }
    </script>
</body></html>
"""
