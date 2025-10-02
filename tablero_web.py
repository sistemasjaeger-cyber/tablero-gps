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
# Contiene todos los dispositivos físicos que el sistema puede controlar.
VEHICULOS = {
    "Freightliner":      {"id": "472", "imei": "863719069189398"},
    "Toma de Fuerza1":   {"id": "128", "imei": "807397674"},
    "Prueba_Unidad":     {"id": "475", "imei": "863719069189364"}, # Bloqueo de unidad para "Prueba"
    "Prueba_QuintaR":    {"id": "362", "imei": "007352724"}      # Bloqueo de 5ta rueda para "Prueba"
}

# --- USUARIOS (VERSIÓN SIMPLE SIN BASE DE DATOS) ---
USERS = {
    "admin": { "password_hash": generate_password_hash("admin123"), "role": "administrador" },
    "cliente": { "password_hash": generate_password_hash("cliente123"), "role": "cliente" }
}

# ... (El resto del código Python, como las funciones de Telegram y login, va aquí sin cambios) ...

# --- RUTAS DE LA API ---
@app.route('/api/get_devices_status')
def get_devices_status_api():
    if 'username' not in session:
        return jsonify({"error": "No autorizado"}), 401
    
    # --- LÓGICA PARA MOSTRAR LAS UNIDADES EN EL TABLERO ---
    # Aquí iría tu código para obtener el estado real de la API
    # y luego construirías los datos para las tarjetas que quieres mostrar.
    
    # Datos de ejemplo para el frontend:
    devices_to_display = {
        "Freightliner": {"id": "472", "online": "online", "speed": 0, "lat": 25.68, "lng": -100.31, "engine_status": "desbloqueado"},
        "Prueba":       {"id": "475", "online": "online", "speed": 0, "lat": 19.43, "lng": -99.13, "engine_status": "desbloqueado"}
    }
    return jsonify(devices_to_display)

@app.route('/api/send_command', methods=['POST'])
def send_command_api():
    if 'username' not in session: return jsonify({"status": 0, "message": "No autorizado"}), 401
    if session.get('role') == 'cliente': return jsonify({"status": 0, "message": "Acción no permitida"}), 403

    data = request.get_json()
    command_type = data.get('type')
    
    target_device = None
    command_message = None

    # --- LÓGICA DE COMANDOS ACTUALIZADA ---
    
    # Comandos para Freightliner
    if command_type in ['stop', 'resume']:
        device_id = data.get('device_id')
        target_device = next((v for v in VEHICULOS.values() if v['id'] == device_id), None)
        command_message = '  setdigout 1' if command_type == 'stop' else '  setdigout 0'
    
    elif command_type == 'pto_off':
        target_device = VEHICULOS.get("Toma de Fuerza1")
        # El comando para esto es el que ya teníamos, si cambia, avísame.
        command_message = f'ST300CMD;{target_device["imei"]};02;Disable2'

    # --- NUEVOS COMANDOS PARA "PRUEBA" ---
    elif command_type == 'block_unit':
        target_device = VEHICULOS.get("Prueba_Unidad")
        # --- ¡¡¡NECESITO EL COMANDO REAL PARA ESTA ACCIÓN!!! ---
        command_message = "  setdigout 1" # <-- EJEMPLO. REEMPLAZAR CON TU COMANDO REAL
    
    elif command_type == 'block_fifth_wheel':
        target_device = VEHICULOS.get("Prueba_QuintaR")
        # --- ¡¡¡NECESITO EL COMANDO REAL PARA ESTA ACCIÓN!!! ---
        command_message = "  setdigout 1" # <-- EJEMPLO. REEMPLAZAR CON TU COMANDO REAL

    else:
        return jsonify({"status": 0, "message": "Tipo de comando no válido."}), 400

    if not target_device:
        return jsonify({"status": 0, "message": "Dispositivo objetivo no encontrado."}), 404

    # --- Envío del comando a la API ---
    url = f"{API_BASE_URL}{COMMAND_ENDPOINT}"
    payload = {
        'user_api_hash': USER_API_HASH, 
        'device_id': target_device['id'],
        'type': 'custom',
        'data': command_message
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"status": 0, "message": f"Error al enviar comando: {e}"}), 500


# --- PLANTILLA HTML (JAVASCRIPT ACTUALIZADO) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<script>
    // ... (Tus funciones showOnMap y sendCommand van aquí sin cambios) ...

    async function fetchDevices() {
        const grid = document.getElementById('device-grid');
        try {
            const response = await fetch('/api/get_devices_status');
            const data = await response.json();
            grid.innerHTML = ''; // Limpiamos el grid para redibujar

            for (const deviceName in data) {
                const device = data[deviceName];
                let buttonsHTML = '';

                // --- Lógica para dibujar los botones correctos para cada tarjeta ---
                if (deviceName === 'Freightliner') {
                    const toggleButton = device.engine_status === 'bloqueado'
                        ? `<button onclick="sendCommand('${device.id}', 'resume', this)" class="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg">Encender Motor</button>`
                        : `<button onclick="sendCommand('${device.id}', 'stop', this)" class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg">Apagar Motor</button>`;
                    
                    buttonsHTML = `
                        ${toggleButton}
                        <button onclick="sendCommand('${device.id}', 'pto_off', this)" class="w-full bg-yellow-600 hover:bg-yellow-700 text-white font-semibold py-2 px-4 rounded-lg">Apagar Toma de Fuerza</button>
                    `;

                } else if (deviceName === 'Prueba') {
                    buttonsHTML = `
                        <button onclick="sendCommand('${device.id}', 'block_unit', this)" class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg">Bloquear Unidad</button>
                        <button onclick="sendCommand('${device.id}', 'block_fifth_wheel', this)" class="w-full bg-orange-600 hover:bg-orange-700 text-white font-semibold py-2 px-4 rounded-lg">Bloquear 5ta Rueda</button>
                    `;
                }
                
                // Construimos la tarjeta con sus botones específicos
                const card = `
                    <div class="device-card bg-gray-800 p-6 rounded-2xl shadow-lg border border-gray-700">
                        <h2 class="text-xl font-bold text-white">${deviceName}</h2>
                        <div class="mt-6 space-y-3">
                            <button onclick="showOnMap(${device.lat}, ${device.lng})" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg">Ver en Mapa</button>
                            ${buttonsHTML}
                        </div>
                        <div id="status-${device.id}" class="text-center text-xs mt-3 h-4"></div>
                    </div>
                `;
                grid.innerHTML += card;
            }
        } catch (err) {
            console.error("Error fetching devices:", err);
            grid.innerHTML = '<p class="text-red-400">Error al cargar los vehículos.</p>';
        }
    }
    document.addEventListener('DOMContentLoaded', fetchDevices);
    </script>
</body></html>
"""
