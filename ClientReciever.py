import socketio
import json
import logging
import sys
from PyQt6.QtWidgets import QApplication
from LoRaInterface.ClientRecieverGui import MainWindow

# Настройка логирования
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Создаем экземпляр Socket.IO клиента
sio = socketio.Client(logger=False, engineio_logger=False)



current_settings = {
    "sf": 12,
    "tx": 17,
    "bw": 125.0,
    "current_distance": None,
    "latitude": None,
    "longitude": None
}


Server_url = ""
Lora_ip = "192.168."

@sio.event
def connect():
    logger.info('Подключение к серверу установлено')
    sio.emit('register_desktop')

@sio.event
def connect_error(data):
    logger.error(f'Ошибка подключения: {data}')

@sio.event
def disconnect():
    logger.info('Отключено от сервера')

@sio.on('message')
def on_message(data):
    message = json.loads(data) if isinstance(data, str) else data
    print(f'Получено сообщение: {message}')
    
    if message.get("settings"):
        update_settings(message["settings"])
    
    if "distance" in message:
        current_settings["current_distance"] = message["distance"]
    
    if "latitude" in message:
        current_settings["latitude"] = message["latitude"]
    if "longitude" in message:
        current_settings["longitude"] = message["longitude"]
        
    if all(key in message for key in ['datetime', 'distance', 'bit_errors', 'snr', 'rssi']):
        try:
            try:
                with open('packets_info.json', 'r') as f:
                    packets = json.load(f)
                    if not isinstance(packets, list):
                        packets = []
            except (FileNotFoundError, json.JSONDecodeError):
                packets = []
            
            packet_info = {
                'datetime': str(message['datetime']),
                'distance': float(message['distance']),
                'bit_errors': int(message['bit_errors']),
                'snr': float(message['snr']),
                'rssi': float(message['rssi']),
                'sf': int(current_settings['sf']),
                'tx': int(current_settings['tx']),
                'bw': float(current_settings['bw']),
                'latitude': current_settings.get('latitude'),
                'longitude': current_settings.get('longitude')
            }
            
            packets.append(packet_info)
            
            with open('packets_info.json', 'w') as f:
                json.dump(packets, f, indent=2)
        except Exception as e:
            print(f"Ошибка при сохранении данных: {str(e)}")

def update_settings(new_settings):
    global current_settings
    current_settings = new_settings
    print(f'Получены новые настройки: {current_settings}')
    
    import requests
    from urllib.parse import urlencode
    params = urlencode({
        "sf": current_settings["sf"],
        "tx": current_settings["tx"],
        "bw": current_settings["bw"]
    })
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(f"http://{Lora_ip}:80/update", data=params, headers=headers)
    if response.ok:
        logger.info("Настройки успешно отправлены на ESP32")
        sio.emit('settings_update_response', {
            "status": "success",
            "message": "Настройки успешно применены на устройстве"
        })
    else:
        logger.error(f"Ошибка при отправке настроек на ESP32: {response.status_code}")
        sio.emit('settings_update_response', {
            "status": "error",
            "message": f"Ошибка при отправке настроек на ESP32: {response.status_code}"
        })

def start_client():
    try:
        app = QApplication(sys.argv)
        from PyQt6.QtGui import QPalette, QColor
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Button, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(51, 153, 255))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        app.setPalette(palette)
        window = MainWindow(sys.modules[__name__])
        window.show()
        return app.exec()
    except Exception as e:
        logger.error(f'Ошибка при запуске приложения: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(start_client())
