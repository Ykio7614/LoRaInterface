from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QGroupBox, 
                            QTableWidget, QTableWidgetItem, QPushButton,
                            QMessageBox, QComboBox, QFileDialog, QTabWidget,
                            QSizePolicy)
from PyQt6.QtCore import QTimer, Qt
import sys
from datetime import datetime
import json
import serial
import serial.tools.list_ports
import re
import os
import logging
import traceback
import folium
import webbrowser
from .GraphicsBuilder import GraphicsBuilder

# Настраиваем логирование
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def exception_hook(exctype, value, tb):
    logging.error("Необработанное исключение:", exc_info=(exctype, value, tb))
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = exception_hook

class MainWindow(QMainWindow):
    def __init__(self, client):
        try:
            super().__init__()
            self.client = client
            self.setWindowTitle("LoRa Приёмник")
            self.setMinimumSize(800, 600)
            
            logging.info("Инициализация главного окна")
            
            # путь к текущему файлу до создания интерфейса
            self.current_file = os.path.join("PacketsInfoFiles", "packets_info.json")
            
            # Создаем папку для файлов, если её нет
            os.makedirs("PacketsInfoFiles", exist_ok=True)
            
            # Создаем пустой файл, если его нет
            if not os.path.exists(self.current_file):
                with open(self.current_file, 'w') as f:
                    json.dump([], f)
            
            try:
                if not os.path.exists("PacketsInfoFiles"):
                    os.makedirs("PacketsInfoFiles")
                
                test_file = os.path.join("PacketsInfoFiles", "test_write.tmp")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                print("Права доступа к директории проверены успешно")
            except Exception as e:
                print(f"Ошибка при проверке прав доступа: {str(e)}")
                QMessageBox.warning(self, "Предупреждение", "Обнаружены проблемы с правами доступа к файлам!")
            
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            layout = QVBoxLayout(central_widget)
            
            # вкладки
            self.tabs = QTabWidget()
            
            # виджеты для каждой вкладки
            connection_tab = QWidget()
            data_tab = QWidget()
            map_tab = QWidget()
            
            # вкладки
            self.tabs.addTab(connection_tab, "Настройки подключения")
            self.tabs.addTab(data_tab, "Просмотр данных")
            self.tabs.addTab(map_tab, "Карта")
            
            connection_layout = QVBoxLayout(connection_tab)
            connection_layout.setContentsMargins(10, 10, 10, 10)
            connection_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            
            connection_group = QGroupBox("Настройки подключения")
            connection_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            connection_settings_layout = QVBoxLayout()
            
            connection_type_layout = QHBoxLayout()
            self.connection_type_label = QLabel("Тип подключения:")
            self.connection_type_combo = QComboBox()
            self.connection_type_combo.addItems(["Сервер", "GSM", "GPRS"])
            self.connection_type_combo.currentTextChanged.connect(self.on_connection_type_changed)
            connection_type_layout.addWidget(self.connection_type_label)
            connection_type_layout.addWidget(self.connection_type_combo)
            connection_settings_layout.addLayout(connection_type_layout)
            
            self.server_settings_container = QWidget()
            server_settings_layout = QHBoxLayout(self.server_settings_container)
            
            server_layout = QVBoxLayout()
            self.server_url_label = QLabel("URL сервера:")
            self.server_url_input = QLineEdit()
            self.server_url_input.setText(self.client.Server_url)
            self.server_url_input.textChanged.connect(self.update_server_url)
            server_layout.addWidget(self.server_url_label)
            server_layout.addWidget(self.server_url_input)
            
            lora_ip_layout = QVBoxLayout()
            self.lora_ip_label = QLabel("IP LoRa приёмника:")
            self.lora_ip_input = QLineEdit()
            self.lora_ip_input.setText(self.client.Lora_ip)
            self.lora_ip_input.textChanged.connect(self.update_lora_ip)
            lora_ip_layout.addWidget(self.lora_ip_label)
            lora_ip_layout.addWidget(self.lora_ip_input)
            
            self.connect_button = QPushButton("Подключиться к серверу")
            self.connect_button.clicked.connect(self.toggle_connection)
            server_settings_layout.addWidget(self.connect_button)
            
            self.connection_status = QLabel("Не подключено")
            server_settings_layout.addWidget(self.connection_status)
            
            server_settings_layout.addLayout(server_layout)
            server_settings_layout.addLayout(lora_ip_layout)
            connection_settings_layout.addWidget(self.server_settings_container)
            
            self.gsm_settings_container = QWidget()
            gsm_settings_layout = QVBoxLayout(self.gsm_settings_container)
            gsm_settings_layout.addWidget(QLabel("TODO: Добавить поля настроек GSM"))
            self.gsm_settings_container.setVisible(False)
            connection_settings_layout.addWidget(self.gsm_settings_container)
            
            self.gprs_settings_container = QWidget()
            gprs_settings_layout = QVBoxLayout(self.gprs_settings_container)
            gprs_settings_layout.addWidget(QLabel("TODO: Добавить поля настроек GPRS"))
            self.gprs_settings_container.setVisible(False)
            connection_settings_layout.addWidget(self.gprs_settings_container)
            
            connection_group.setLayout(connection_settings_layout)
            connection_layout.addWidget(connection_group)
            
            com_group = QGroupBox("Последовательное подключение")
            com_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            com_layout = QHBoxLayout()
            
            self.port_combo = QComboBox()
            self.update_ports_list()
            com_layout.addWidget(self.port_combo)
            
            refresh_button = QPushButton("Обновить порты")
            refresh_button.clicked.connect(self.update_ports_list)
            com_layout.addWidget(refresh_button)
            
            self.connect_serial_button = QPushButton("Подключиться к порту")
            self.connect_serial_button.clicked.connect(self.toggle_serial_connection)
            com_layout.addWidget(self.connect_serial_button)
            
            com_group.setLayout(com_layout)
            connection_layout.addWidget(com_group)
            
            data_layout = QVBoxLayout(data_tab)
            data_layout.setContentsMargins(10, 10, 10, 10)
            data_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            
            distance_group = QGroupBox("Текущее расстояние")
            distance_layout = QVBoxLayout()
            self.distance_label = QLabel("- м")
            self.distance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            distance_layout.addWidget(self.distance_label)
            distance_group.setLayout(distance_layout)
            data_layout.addWidget(distance_group)
            
            settings_group = QGroupBox("Текущие настройки")
            settings_layout = QVBoxLayout()
            self.sf_label = QLabel(f"SF: {self.client.current_settings['sf']}")
            self.tx_label = QLabel(f"Tx power: {self.client.current_settings['tx']}")
            self.bw_label = QLabel(f"BW: {self.client.current_settings['bw']}")
            settings_layout.addWidget(self.sf_label)
            settings_layout.addWidget(self.tx_label)
            settings_layout.addWidget(self.bw_label)
            settings_group.setLayout(settings_layout)
            data_layout.addWidget(settings_group)
            
            last_packet_group = QGroupBox("Параметры последнего пакета")
            last_packet_layout = QVBoxLayout()
            self.last_datetime_label = QLabel("Дата и время: -")
            self.last_rssi_label = QLabel("RSSI: -")
            self.last_snr_label = QLabel("SNR: -")
            self.last_errors_label = QLabel("Битовые ошибки: -")
            self.last_distance_label = QLabel("Расстояние: -")
            self.last_latitude_label = QLabel("Широта: -")
            self.last_longitude_label = QLabel("Долгота: -")
            last_packet_layout.addWidget(self.last_datetime_label)
            last_packet_layout.addWidget(self.last_rssi_label)
            last_packet_layout.addWidget(self.last_snr_label)
            last_packet_layout.addWidget(self.last_errors_label)
            last_packet_layout.addWidget(self.last_distance_label)
            last_packet_layout.addWidget(self.last_latitude_label)
            last_packet_layout.addWidget(self.last_longitude_label)
            last_packet_group.setLayout(last_packet_layout)
            data_layout.addWidget(last_packet_group)
            
            files_group = QGroupBox("Файлы пакетов")
            files_layout = QHBoxLayout()
            
            self.files_combo = QComboBox()
            self.update_files_list()
            files_layout.addWidget(self.files_combo)
            
            refresh_files_button = QPushButton("Обновить файлы")
            refresh_files_button.clicked.connect(self.update_files_list)
            files_layout.addWidget(refresh_files_button)
            
            new_file_button = QPushButton("Новый файл")
            new_file_button.clicked.connect(self.create_new_file)
            files_layout.addWidget(new_file_button)

            new_graphs_button = QPushButton("Новые графики")
            new_graphs_button.clicked.connect(self.create_new_graphs)
            files_layout.addWidget(new_graphs_button)
            
            files_group.setLayout(files_layout)
            data_layout.addWidget(files_group)
            
            self.packets_table = QTableWidget()
            self.packets_table.setColumnCount(10)
            self.packets_table.setHorizontalHeaderLabels([
                "Дата и время", "Расстояние", "Битовые ошибки", "SNR", 
                "RSSI", "SF", "Tx power", "BW", "Широта", "Долгота"
            ])
            data_layout.addWidget(self.packets_table)
            
            map_layout = QVBoxLayout(map_tab)
            map_layout.setContentsMargins(10, 10, 10, 10)
            map_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.show_map_button = QPushButton("Показать карту")
            self.show_map_button.clicked.connect(self.create_map)
            map_layout.addWidget(self.show_map_button)
            
            layout.addWidget(self.tabs)
            
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self.update_data)
            self.update_timer.start(1000)
            
            self.serial = None
            self.serial_timer = QTimer()
            self.serial_timer.timeout.connect(self.read_serial)
            
        except Exception as e:
            logging.error(f"Ошибка при инициализации главного окна: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при запуске приложения: {str(e)}")
            raise

    def update_server_url(self, url):
        self.client.Server_url = url
        
    def update_lora_ip(self, ip):
        self.client.Lora_ip = ip
        
    def update_data(self):
        try:
            # Обновление текущих настроек
            self.sf_label.setText(f"SF: {self.client.current_settings['sf']}")
            self.tx_label.setText(f"Tx power: {self.client.current_settings['tx']}")
            self.bw_label.setText(f"BW: {self.client.current_settings['bw']}")
            
            # Обновление текущего расстояния
            current_distance = self.client.current_settings.get('current_distance')
            if current_distance is not None:
                self.distance_label.setText(f"{current_distance:.2f} м")
            else:
                self.distance_label.setText("- м")
            
            # Загрузка и отображение истории пакетов
            try:
                with open(self.current_file, 'r') as f:
                    packets = json.load(f)
                    if isinstance(packets, list): 
                        self.packets_table.setRowCount(len(packets))
                        for i, packet in enumerate(packets):
                            if isinstance(packet, dict):
                                self.packets_table.setItem(i, 0, QTableWidgetItem(str(packet.get('datetime', '-'))))
                                self.packets_table.setItem(i, 1, QTableWidgetItem(f"{float(packet.get('distance', 0)):.2f}"))
                                self.packets_table.setItem(i, 2, QTableWidgetItem(str(packet.get('bit_errors', '-'))))
                                self.packets_table.setItem(i, 3, QTableWidgetItem(str(packet.get('snr', '-'))))
                                self.packets_table.setItem(i, 4, QTableWidgetItem(str(packet.get('rssi', '-'))))
                                self.packets_table.setItem(i, 5, QTableWidgetItem(str(packet.get('sf', '-'))))
                                self.packets_table.setItem(i, 6, QTableWidgetItem(str(packet.get('tx', '-'))))
                                self.packets_table.setItem(i, 7, QTableWidgetItem(str(packet.get('bw', '-'))))
                                self.packets_table.setItem(i, 8, QTableWidgetItem(str(packet.get('latitude', '-'))))
                                self.packets_table.setItem(i, 9, QTableWidgetItem(str(packet.get('longitude', '-'))))
                        
                        if packets and isinstance(packets[-1], dict):
                            last_packet = packets[-1]
                            self.last_datetime_label.setText(f"Дата и время: {last_packet.get('datetime', '-')}")
                            self.last_rssi_label.setText(f"RSSI: {last_packet.get('rssi', '-')}")
                            self.last_snr_label.setText(f"SNR: {last_packet.get('snr', '-')}")
                            self.last_errors_label.setText(f"Битовые ошибки: {last_packet.get('bit_errors', '-')}")
                            self.last_distance_label.setText(f"Расстояние: {last_packet.get('distance', '-'):.2f} м")
                            self.last_latitude_label.setText(f"Широта: {last_packet.get('latitude', '-')}")
                            self.last_longitude_label.setText(f"Долгота: {last_packet.get('longitude', '-')}")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Ошибка при чтении файла {self.current_file}: {str(e)}")
        except Exception as e:
            logging.error(f"Ошибка при обновлении данных: {str(e)}", exc_info=True)
            QMessageBox.warning(self, "Ошибка", f"Ошибка при обновлении данных: {str(e)}")

    def toggle_connection(self):
        try:
            if self.connect_button.text() == "Подключиться к серверу":
                try:
                    self.client.sio.connect(self.client.Server_url, wait_timeout=10)
                    self.connection_status.setText("Подключено")
                    self.connect_button.setText("Отключиться")
                except Exception as e:
                    self.connection_status.setText("Ошибка подключения")
                    QMessageBox.critical(self, "Ошибка подключения", f"Не удалось подключиться: {str(e)}")
            else:
                try:
                    self.client.sio.disconnect()
                    self.connection_status.setText("Не подключено")
                    self.connect_button.setText("Подключиться к серверу")
                except Exception as e:
                    QMessageBox.warning(self, "Ошибка отключения", f"Ошибка при отключении: {str(e)}")
        except Exception as e:
            logging.error(f"Ошибка при переключении соединения: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при переключении соединения: {str(e)}")

    def update_ports_list(self):
        """Обновляет список доступных COM портов"""
        self.port_combo.clear()
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo.addItems(ports)
    
    def toggle_serial_connection(self):
        """Подключение/отключение от COM порта"""
        if self.serial is None or not self.serial.is_open:
            try:
                port = self.port_combo.currentText()
                self.serial = serial.Serial(port, 115200, timeout=0)
                self.connect_serial_button.setText("Отключиться")
                self.serial_timer.start(100)  # Читаем порт каждые 100мс
            except Exception as e:
                QMessageBox.critical(self, "Ошибка подключения", f"Не удалось подключиться: {str(e)}")
        else:
            try:
                self.serial_timer.stop()
                self.serial.close()
                self.serial = None
                self.connect_serial_button.setText("Подключиться к порту")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка отключения", f"Ошибка при отключении: {str(e)}")
    
    def read_serial(self):
        try:
            if self.serial and self.serial.is_open:
                try:
                    if self.serial.in_waiting:
                        line = self.serial.readline().decode('utf-8').strip()
                        print(f"Прочитано из порта: {line}")
                        if line:
                            self.process_serial_data(line)
                except Exception as e:
                    print(f"Ошибка чтения из порта: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
        except Exception as e:
            logging.error(f"Ошибка при чтении из порта: {str(e)}", exc_info=True)
            QMessageBox.warning(self, "Ошибка", f"Ошибка при чтении из порта: {str(e)}")
    
    def process_serial_data(self, data):
        try:
            print(f"Получены данные: {data}")
            
            settings_match = re.match(r"SettingsUpdated{\s*SF:\s*(\d+)\s*TX:\s*(\d+)\s*BW:\s*(\d+\.\d+)\s*}", data)
            if settings_match:
                print("Обнаружено обновление настроек")
                sf, tx, bw = settings_match.groups()
                self.client.current_settings.update({
                    "sf": int(sf),
                    "tx": int(tx),
                    "bw": float(bw)
                })
                print(f"Настройки обновлены: {self.client.current_settings}")
                return

            packet_match = re.match(r"PacketInfo{\s*Rssi:\s*(-?\d+)\s*Snr:\s*(-?\d+\.\d+)\s*Bit errors:\s*(\d+)\s*}", data)
            if packet_match:
                print("Обнаружена информация о пакете")
                rssi, snr, bit_errors = packet_match.groups()
                packet_info = {
                    'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'distance': self.client.current_settings.get('current_distance', 0),
                    'bit_errors': int(bit_errors),
                    'snr': float(snr),
                    'rssi': float(rssi),
                    'sf': self.client.current_settings['sf'],
                    'tx': self.client.current_settings['tx'],
                    'bw': self.client.current_settings['bw']
                }
                print(f"Сформирован пакет: {packet_info}")
                
                try:
                    try:
                        with open(self.current_file, 'r') as f:
                            packets = json.load(f)
                            if not isinstance(packets, list):
                                packets = []
                    except (FileNotFoundError, json.JSONDecodeError):
                        packets = []
                    
                    print(f"Текущее количество пакетов: {len(packets)}")
                    
                    packets.append(packet_info)
                    
                    with open(self.current_file, 'w') as f:
                        json.dump(packets, f, indent=2)
                    
                    print(f"Пакет сохранен, всего пакетов: {len(packets)}")
                    
                    self.last_datetime_label.setText(f"Дата и время: {packet_info['datetime']}")
                    self.last_rssi_label.setText(f"RSSI: {packet_info['rssi']}")
                    self.last_snr_label.setText(f"SNR: {packet_info['snr']}")
                    self.last_errors_label.setText(f"Битовые ошибки: {packet_info['bit_errors']}")
                    self.last_distance_label.setText(f"Расстояние: {packet_info['distance']:.2f} м")
                    
                    self.update_data()
                    
                except Exception as e:
                    print(f"Ошибка при сохранении данных пакета: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
        except Exception as e:
            logging.error(f"Ошибка при обработке данных: {str(e)}", exc_info=True)
            QMessageBox.warning(self, "Ошибка", f"Ошибка при обработке данных: {str(e)}")

    def closeEvent(self, event):
        try:
            if self.serial and self.serial.is_open:
                self.serial.close()
            event.accept()
        except Exception as e:
            logging.error(f"Ошибка при закрытии приложения: {str(e)}", exc_info=True)
            event.accept()

    def update_files_list(self):
        """Обновляет список доступных файлов"""
        self.files_combo.clear()
        
        files = [f for f in os.listdir("PacketsInfoFiles") if f.endswith('.json')]
        self.files_combo.addItems(files)
        
        current_filename = os.path.basename(self.current_file)
        index = self.files_combo.findText(current_filename)
        if index >= 0:
            self.files_combo.setCurrentIndex(index)
            
        self.files_combo.currentTextChanged.connect(self.change_current_file)
    
    def change_current_file(self, filename):
        """Обработчик смены текущего файла"""
        if filename:
            self.current_file = os.path.join("PacketsInfoFiles", filename)
            self.update_data()
    
    def create_new_file(self):
        """Создает новый файл для записи пакетов"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Создать новый файл пакетов",
            "PacketsInfoFiles",
            "JSON файлы (*.json)"
        )
        
        if filename:
            if not filename.startswith(os.path.abspath("PacketsInfoFiles")):
                filename = os.path.join("PacketsInfoFiles", os.path.basename(filename))
            
            if not filename.endswith('.json'):
                filename += '.json'
            
            with open(filename, 'w') as f:
                json.dump([], f)
            
            self.current_file = filename
            self.update_files_list()

    def create_new_graphs(self):
        """Создает новые графики из текущего файла"""
        try:
            os.makedirs("../GraphsFiles", exist_ok=True)
            
            builder = GraphicsBuilder(self.current_file)
            
            snr_plot, rssi_plot = builder.create_all_plots()
            
            self.create_map()
            
            QMessageBox.information(
                self,
                "Успех",
                f"Графики и карта успешно созданы!\nГрафик SNR: {snr_plot}\nГрафик RSSI: {rssi_plot}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось создать графики или карту: {str(e)}"
            )


    # нужна другая библиотека...
    def create_map(self):
        """Создает интерактивную карту с точками из текущего файла"""
        try:        
            with open(self.current_file, 'r') as f:
                packets = json.load(f)
            
            packets_with_coords = [p for p in packets if p.get('latitude') and p.get('longitude')]
            
            if not packets_with_coords:
                QMessageBox.warning(self, "Предупреждение", "Нет координат для отображения на карте")
                return
            
            first_point = packets_with_coords[0]
            m = folium.Map(
                location=[first_point['latitude'], first_point['longitude']],
                zoom_start=13
            )
            
            for packet in packets_with_coords:
                popup_text = f"""
                <b>Время:</b> {packet.get('datetime', '-')}<br>
                <b>Расстояние:</b> {packet.get('distance', '-'):.2f} м<br>
                <b>RSSI:</b> {packet.get('rssi', '-')}<br>
                <b>SNR:</b> {packet.get('snr', '-')}<br>
                <b>Ошибки:</b> {packet.get('bit_errors', '-')}<br>
                <b>SF:</b> {packet.get('sf', '-')}<br>
                <b>Tx:</b> {packet.get('tx', '-')}<br>
                <b>BW:</b> {packet.get('bw', '-')}
                """
                folium.Marker(
                    location=[packet['latitude'], packet['longitude']],
                    popup=folium.Popup(popup_text, max_width=300),
                    tooltip=f"Расстояние: {packet.get('distance', '-'):.2f} м"
                ).add_to(m)
            
            map_file = os.path.join("../GraphsFiles", "map.html")
            m.save(map_file)
            
            webbrowser.open('file://' + os.path.abspath(map_file))
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось создать карту: {str(e)}"
            )

    def on_connection_type_changed(self, connection_type):
        self.server_settings_container.setVisible(False)
        self.gsm_settings_container.setVisible(False)
        self.gprs_settings_container.setVisible(False)
        
        if connection_type == "Сервер":
            self.server_settings_container.setVisible(True)
        elif connection_type == "GSM":
            self.gsm_settings_container.setVisible(True)
        elif connection_type == "GPRS":
            self.gprs_settings_container.setVisible(True)

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        import ClientReciever as client_module
        window = MainWindow(client_module)
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"Критическая ошибка при запуске приложения: {str(e)}", exc_info=True)
        QMessageBox.critical(None, "Критическая ошибка", f"Приложение не может быть запущено: {str(e)}")
        sys.exit(1)

