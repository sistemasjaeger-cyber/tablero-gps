import requests
import json
from flask import Flask, jsonify, render_template_string, request
import os

# --- Configuración de la API ---
# La URL base de la API de GPS
API_BASE_URL = 'http://5.78.94.130' 
# El hash de usuario se obtiene de una variable de entorno segura
USER_API_HASH = os.environ.get('USER_API_HASH') 
COMMAND_ENDPOINT = '/api/send_gprs_command' 
DEVICES_ENDPOINT = '/api/get_devices'

# --- LISTA DE VEHÍCULOS COMPLETA ---
# Aquí defines los vehículos que aparecerán en el tablero
VEHICULOS = {
    "CADDY 14":      {"id": "242", "imei": "807356113"},
    "CADDY 15":      {"id": "325", "imei": "807356123"},
    "CADDY 16":      {"id": "68",  "imei": "807356121"},
    "KANGOO 08":     {"id": "150", "imei": "807397691"},
    "KANGOO 09":     {"id": "149", "imei": "807397686"},
    "KANGOO 10":     {"id": "394", "imei": "807356127"},
    "NISSAN 11":     {"id": "74",  "imei": "807110416"},
    "Prueba ignición": {"id": "463", "imei": "807356132"}
}

# --- INICIALIZACIÓN DEL SERVIDOR WEB ---
app = Flask(__name__)

# --- MEMORIA PARA EL ESTADO DEL MOTOR ---
# Usamos un diccionario para guardar el estado conocido de cada motor
# 'bloqueado', 'desbloqueado'. Se reinicia si el servidor se reinicia.
engine_status_memory = {}

# --- PLANTILLA HTML DEL TABLERO ---
# Todo el código de la interfaz de usuario está aquí
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tablero de Control GPS</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .device-card { transition: all 0.2s ease-in-out; }
        .device-card:hover { transform: translateY(-4px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.2), 0 4px 6px -2px rgba(0,0,0,0.1); }
        .btn-action { transition: all 0.2s ease-in-out; }
        .btn-action:hover { transform: scale(1.05); }
    </style>
</head>
<body class="bg-gray-900 text-white">
    <div class="container mx-auto p-4 md:p-8">
        <header class="text-center mb-12">
            <h1 class="text-4xl md:text-5xl font-bold text-indigo-400">Tablero de Control de Flota</h1>
            <p class="text-gray-400 mt-2">Selecciona un vehículo para enviar comandos.</p>
        </header>

        <main id="device-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            </main>

        <div id="loading-state" class="text-center py-10">
            <p class="text-lg text-gray-400">Cargando vehículos...</p>
        </div>
        
        <div id="error-state" class="hidden text-center py-10 bg-red-900/50 p-6 rounded-lg">
            <p class="text-lg text-red-400">❌ Error al cargar los vehículos.</p>
            <p id="error-message" class="text-gray-400 mt-2"></p>
        </div>
    </div>

    <footer class="text-center p-4 mt-8">
        <p class="text-sm text-gray-500">Desarrollado por Gerardo De La Torre</p>
    </footer>

    <script>
        // Función para abrir la ubicación en Google Maps
        function showOnMap(lat, lng) {
            if (lat && lng && lat !== 'None' && lng !== 'None') {
                const url = `https://www.google.com/maps?q=${lat},${lng}`;
                window.open(url, '_blank');
            } else {
                alert('Ubicación no disponible para este vehículo.');
            }
        }

        // Función para obtener y mostrar los dispositivos
        async function fetchDevices() {
            const grid = document.getElementById('device-grid');
            const loading = document.getElementById('loading-state');
            const errorState = document.getElementById('error-state');
            const errorMessage = document.getElementById('error-message');

            try {
                const response = await fetch('/api/get_devices_status');
                const data = await response.json();

                if (!response.ok) throw new Error(data.error || 'Error desconocido.');

                grid.innerHTML = '';
                if (Object.keys(data).length === 0) {
                   throw new Error("No se encontraron vehículos. Revisa la configuración de la API.");
                }
                
                for (const deviceName in data) {
                    const device = data[deviceName];
                    let onlineStatusColor = 'bg-yellow-500';
                    let onlineStatusText = 'Offline';
                    if (device.online === 'online') {
                        onlineStatusColor = 'bg-green-500';
                        onlineStatusText = 'En Línea';
                    }
                    if (device.online === 'ack') {
                        onlineStatusColor = 'bg-blue-500';
                        onlineStatusText = 'Reconocido';
                    }
                    
                    let engineStatusColor = 'bg-gray-500';
                    let engineStatusText = 'Desconocido';
                    if (device.engine_status === 'en_uso') {
                        engineStatusColor = 'bg-green-600';
                        engineStatusText = 'En Movimiento';
                    } else if (device.engine_status === 'bloqueado') {
                        engineStatusColor = 'bg-red-600';
                        engineStatusText = 'Motor Bloqueado';
                    } else if (device.engine_status === 'desbloqueado') {
                        engineStatusColor = 'bg-sky-600';
                        engineStatusText = 'Motor Desbloqueado';
                    }


                    const card = `
                        <div class="device-card bg-gray-800 p-6 rounded-2xl shadow-lg border border-gray-700 flex flex-col justify-between">
                            <div>
                                <div class="flex justify-between items-start">
                                    <h2 class="text-xl font-bold text-white">${deviceName}</h2>
                                    <div class="flex items-center space-x-2">
                                        <div class="w-3 h-3 ${onlineStatusColor} rounded-full"></div>
                                        <span class="text-xs text-gray-400">${onlineStatusText}</span>
                                    </div>
                                </div>
                                <p class="text-xs text-gray-500 mt-1">ID: ${device.id}</p>
                                
                                <div class="flex justify-center items-center my-4 p-2 rounded-lg ${engineStatusColor}">
                                    <span class="font-semibold text-sm">${engineStatusText}</span>
                                </div>

                                <div class="flex items-center text-lg">
                                    <svg class="w-6 h-6 mr-2 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                                    <span class="font-semibold">${device.speed}</span>
                                    <span class="text-sm text-gray-400 ml-1">km/h</span>
                                </div>
                            </div>
                            <div class="mt-6 space-y-3">
                                <button onclick="showOnMap(${device.lat}, ${device.lng})" class="btn-action w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg flex items-center justify-center">
                                    <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                                    Ver en Mapa
                                </button>
                                <button onclick="sendCommand('${device.id}', 'stop', this)" class="btn-action w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg">
                                    Apagar Motor
                                </button>
                                <button onclick="sendCommand('${device.id}', 'resume', this)" class="btn-action w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg">
                                    Encender Motor
                                </button>
                            </div>
                            <div id="status-${device.id}" class="text-center text-xs mt-3 h-4"></div>
                        </div>
                    `;
                    grid.innerHTML += card;
                }

            } catch (err) {
                errorState.classList.remove('hidden');
                errorMessage.innerText = err.message;
            } finally {
                loading.classList.add('hidden');
            }
        }

        // Función para enviar un comando al backend
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
                if (response.ok && result.status === 1) {
                    statusDiv.innerHTML = '<span class="text-green-400">¡Comando enviado!</span>';
                    // Recargar los datos para ver el cambio de estado
                    setTimeout(fetchDevices, 2000); 
                } else {
                    statusDiv.innerHTML = `<span class="text-red-400">Error: ${result.message || 'Fallo inesperado.'}</span>`;
                }
            } catch (err) {
                statusDiv.innerHTML = '<span class="text-red-400">Error de Conexión.</span>';
            } finally {
                // Reactivar botones después de un tiempo
                setTimeout(() => {
                    statusDiv.innerHTML = '';
                    buttons.forEach(b => b.disabled = false);
                }, 4000);
            }
        }

        // Cargar los dispositivos cuando la página esté lista
        document.addEventListener('DOMContentLoaded', fetchDevices);
    </script>
</body>
</html>
"""

# --- RUTAS DE LA API INTERNA (EL BACKEND) ---

@app.route('/')
def dashboard():
    """ Sirve la página principal del tablero. """
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/get_devices_status')
def get_devices_status_api():
    """
    Obtiene el estado en tiempo real de los vehículos desde la API externa
    y lo combina con los datos locales y la memoria de estado.
    """
    # Primero, verificar si el HASH existe
    if not USER_API_HASH:
        return jsonify({"error": "La variable de entorno USER_API_HASH no está configurada en el servidor."}), 500

    url = f"{API_BASE_URL}{DEVICES_ENDPOINT}"
    params = {'lang': 'es', 'user_api_hash': USER_API_HASH}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        all_devices_data = response.json()
        
        status_map = {}
        for group in all_devices_data:
            if 'items' in group:
                for device in group['items']:
                    status_map[str(device.get('id'))] = {
                        "online": device.get('online', 'offline'),
                        "speed": device.get('speed', 0),
                        "lat": device.get('lat'),
                        "lng": device.get('lng')
                    }
        
        devices_with_status = {}
        for name, data in VEHICULOS.items():
            device_id_str = str(data['id'])
            status = status_map.get(device_id_str, {"online": "offline", "speed": 0, "lat": None, "lng": None})
            
            # --- Lógica de estado del motor ---
            engine_status = 'desconocido'
            if status['speed'] > 0:
                engine_status = 'en_uso'
                # Si se está moviendo, el estado "lógico" debe ser desbloqueado
                engine_status_memory[device_id_str] = 'desbloqueado'
            else:
                # Si está detenido, usamos el último estado que guardamos en memoria
                engine_status = engine_status_memory.get(device_id_str, 'desbloqueado')
            
            devices_with_status[name] = {
                "id": data['id'],
                "imei": data['imei'],
                "online": status['online'],
                "speed": status['speed'],
                "lat": status['lat'],
                "lng": status['lng'],
                "engine_status": engine_status
            }
            
        return jsonify(devices_with_status)
    except Exception as e:
        return jsonify({"error": f"Error al obtener estado de dispositivos: {e}"}), 500

@app.route('/api/send_command', methods=['POST'])
def send_command_api():
    """ 
    Recibe la solicitud del navegador, construye el comando correcto 
    y lo envía a la API externa de GPS.
    """
    if not USER_API_HASH:
        return jsonify({"status": 0, "message": "La variable de entorno USER_API_HASH no está configurada."}), 500

    data = request.get_json()
    device_id = data.get('device_id')
    command_type = data.get('type')

    vehicle_info = next((v for v in VEHICULOS.values() if v['id'] == device_id), None)
    if not vehicle_info:
        return jsonify({"status": 0, "message": "Dispositivo no encontrado."}), 404
    
    imei = vehicle_info.get('imei')

    if command_type == 'stop':
        command_message = f'ST300CMD;{imei};02;Disable1'
        # Actualizar nuestra memoria de estado
        engine_status_memory[device_id] = 'bloqueado'
    elif command_type == 'resume':
        command_message = f'ST300CMD;{imei};02;Enable1'
        # Actualizar nuestra memoria de estado
        engine_status_memory[device_id] = 'desbloqueado'
    else:
        return jsonify({"status": 0, "message": "Tipo de comando no válido."}), 400

    url = f"{API_BASE_URL}{COMMAND_ENDPOINT}"
    
    payload = {
        'user_api_hash': USER_API_HASH, 
        'device_id': device_id,
        'type': 'custom',
        'data': command_message
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"status": 0, "message": f"Error al enviar comando: {e}"}), 500