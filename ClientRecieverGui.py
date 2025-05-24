from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QGroupBox, 
                            QTableWidget, QTableWidgetItem, QPushButton,
                            QMessageBox, QComboBox, QFileDialog)
from PyQt6.QtCore import QTimer, Qt
import sys
from datetime import datetime
import json
import serial
import serial.tools.list_ports
import re
import os
from GraphicsBuilder import GraphicsBuilder

class MainWindow(QMainWindow):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.setWindowTitle("LoRa Receiver")
        self.setMinimumSize(800, 600)
        
        # Инициализируем путь к текущему файлу до создания интерфейса
        self.current_file = os.path.join("PacketsInfoFiles", "packets_info.json")
        
        # Создаем директорию для файлов, если её нет
        os.makedirs("PacketsInfoFiles", exist_ok=True)
        
        # Создаем пустой файл, если он не существует
        if not os.path.exists(self.current_file):
            with open(self.current_file, 'w') as f:
                json.dump([], f)
        
        # Проверяем права доступа к файлу и директории
        try:
            if not os.path.exists("PacketsInfoFiles"):
                os.makedirs("PacketsInfoFiles")
            
            # Проверяем права на запись
            test_file = os.path.join("PacketsInfoFiles", "test_write.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            print("Права доступа к директории проверены успешно")
        except Exception as e:
            print(f"Ошибка при проверке прав доступа: {str(e)}")
            QMessageBox.warning(self, "Warning", "Problems with file permissions detected!")
        
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        layout = QVBoxLayout(central_widget)
        
        # Верхняя панель с настройками соединения
        connection_group = QGroupBox("Connection Settings")
        connection_layout = QHBoxLayout()
        
        # Server URL
        server_layout = QVBoxLayout()
        self.server_url_label = QLabel("Server URL:")
        self.server_url_input = QLineEdit()
        self.server_url_input.setText(self.client.Server_url)
        self.server_url_input.textChanged.connect(self.update_server_url)
        server_layout.addWidget(self.server_url_label)
        server_layout.addWidget(self.server_url_input)
        
        # LoRa Receiver IP
        lora_ip_layout = QVBoxLayout()
        self.lora_ip_label = QLabel("LoRa Receiver IP:")
        self.lora_ip_input = QLineEdit()
        self.lora_ip_input.setText(self.client.Lora_ip)
        self.lora_ip_input.textChanged.connect(self.update_lora_ip)
        lora_ip_layout.addWidget(self.lora_ip_label)
        lora_ip_layout.addWidget(self.lora_ip_input)
        
        # Добавляем кнопку подключения
        self.connect_button = QPushButton("Connect to Server")
        self.connect_button.clicked.connect(self.toggle_connection)
        connection_layout.addWidget(self.connect_button)
        
        # Добавляем индикатор состояния
        self.connection_status = QLabel("Not Connected")
        connection_layout.addWidget(self.connection_status)
        
        connection_layout.addLayout(server_layout)
        connection_layout.addLayout(lora_ip_layout)
        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)
        
        # Добавляем выбор COM порта после настроек соединения
        com_group = QGroupBox("Serial Connection")
        com_layout = QHBoxLayout()
        
        # Комбобокс для выбора порта
        self.port_combo = QComboBox()
        self.update_ports_list()
        com_layout.addWidget(self.port_combo)
        
        # Кнопка обновления списка портов
        refresh_button = QPushButton("Refresh Ports")
        refresh_button.clicked.connect(self.update_ports_list)
        com_layout.addWidget(refresh_button)
        
        # Кнопка подключения к порту
        self.connect_serial_button = QPushButton("Connect to Port")
        self.connect_serial_button.clicked.connect(self.toggle_serial_connection)
        com_layout.addWidget(self.connect_serial_button)
        
        com_group.setLayout(com_layout)
        layout.addWidget(com_group)
        
        # Текущее расстояние (изменяем начальное значение)
        distance_group = QGroupBox("Current Distance")
        distance_layout = QVBoxLayout()
        self.distance_label = QLabel("- м")
        self.distance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        distance_layout.addWidget(self.distance_label)
        distance_group.setLayout(distance_layout)
        layout.addWidget(distance_group)
        
        # Текущие настройки
        settings_group = QGroupBox("Current Settings")
        settings_layout = QVBoxLayout()
        self.sf_label = QLabel(f"Spreading Factor: {self.client.current_settings['sf']}")
        self.tx_label = QLabel(f"Output Power: {self.client.current_settings['tx']}")
        self.bw_label = QLabel(f"Bandwidth: {self.client.current_settings['bw']}")
        settings_layout.addWidget(self.sf_label)
        settings_layout.addWidget(self.tx_label)
        settings_layout.addWidget(self.bw_label)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Последний пакет
        last_packet_group = QGroupBox("Last Packet Parameters")
        last_packet_layout = QVBoxLayout()
        self.last_datetime_label = QLabel("DateTime: -")
        self.last_rssi_label = QLabel("RSSI: -")
        self.last_snr_label = QLabel("SNR: -")
        self.last_errors_label = QLabel("Bit Errors: -")
        self.last_distance_label = QLabel("Distance: -")
        last_packet_layout.addWidget(self.last_datetime_label)
        last_packet_layout.addWidget(self.last_rssi_label)
        last_packet_layout.addWidget(self.last_snr_label)
        last_packet_layout.addWidget(self.last_errors_label)
        last_packet_layout.addWidget(self.last_distance_label)
        last_packet_group.setLayout(last_packet_layout)
        layout.addWidget(last_packet_group)
        
        # Добавляем группу для работы с файлами
        files_group = QGroupBox("Packets Files")
        files_layout = QHBoxLayout()
        
        # Комбобокс для выбора файла
        self.files_combo = QComboBox()
        self.update_files_list()
        files_layout.addWidget(self.files_combo)
        
        # Кнопка обновления списка файлов
        refresh_files_button = QPushButton("Refresh Files")
        refresh_files_button.clicked.connect(self.update_files_list)
        files_layout.addWidget(refresh_files_button)
        
        # Кнопка создания нового файла
        new_file_button = QPushButton("New File")
        new_file_button.clicked.connect(self.create_new_file)
        files_layout.addWidget(new_file_button)

        new_graphs_button = QPushButton("New Graphs")
        new_graphs_button.clicked.connect(self.create_new_graphs)
        files_layout.addWidget(new_graphs_button)
        
        files_group.setLayout(files_layout)
        layout.addWidget(files_group)
        
        # Добавляем таблицу после группы файлов
        self.packets_table = QTableWidget()
        self.packets_table.setColumnCount(8)
        self.packets_table.setHorizontalHeaderLabels([
            "DateTime", "Distance", "Bit Errors", "SNR", 
            "RSSI", "SF", "TX", "BW"
        ])
        layout.addWidget(self.packets_table)
        
        # Таймер для обновления данных
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.start(1000)  # Обновление каждую секунду
        
        # Добавляем последовательное соединение
        self.serial = None
        self.serial_timer = QTimer()
        self.serial_timer.timeout.connect(self.read_serial)
        
    def update_server_url(self, url):
        self.client.Server_url = url
        
    def update_lora_ip(self, ip):
        self.client.Lora_ip = ip
        
    def update_data(self):
        # Обновление текущих настроек
        self.sf_label.setText(f"Spreading Factor: {self.client.current_settings['sf']}")
        self.tx_label.setText(f"Output Power: {self.client.current_settings['tx']}")
        self.bw_label.setText(f"Bandwidth: {self.client.current_settings['bw']}")
        
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
                if isinstance(packets, list):  # Проверяем, что packets это список
                    self.packets_table.setRowCount(len(packets))
                    for i, packet in enumerate(packets):
                        if isinstance(packet, dict):  # Проверяем, что packet это словарь
                            # Безопасное получение значений с значениями по умолчанию
                            self.packets_table.setItem(i, 0, QTableWidgetItem(str(packet.get('datetime', '-'))))
                            self.packets_table.setItem(i, 1, QTableWidgetItem(str(packet.get('distance', '-'))))
                            self.packets_table.setItem(i, 2, QTableWidgetItem(str(packet.get('bit_errors', '-'))))
                            self.packets_table.setItem(i, 3, QTableWidgetItem(str(packet.get('snr', '-'))))
                            self.packets_table.setItem(i, 4, QTableWidgetItem(str(packet.get('rssi', '-'))))
                            self.packets_table.setItem(i, 5, QTableWidgetItem(str(packet.get('sf', '-'))))
                            self.packets_table.setItem(i, 6, QTableWidgetItem(str(packet.get('tx', '-'))))
                            self.packets_table.setItem(i, 7, QTableWidgetItem(str(packet.get('bw', '-'))))
                    
                    # Обновление информации о последнем пакете
                    if packets and isinstance(packets[-1], dict):
                        last_packet = packets[-1]
                        self.last_datetime_label.setText(f"DateTime: {last_packet.get('datetime', '-')}")
                        self.last_rssi_label.setText(f"RSSI: {last_packet.get('rssi', '-')}")
                        self.last_snr_label.setText(f"SNR: {last_packet.get('snr', '-')}")
                        self.last_errors_label.setText(f"Bit Errors: {last_packet.get('bit_errors', '-')}")
                        self.last_distance_label.setText(f"Distance: {last_packet.get('distance', '-')} м")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Ошибка при чтении файла {self.current_file}: {str(e)}")

    def toggle_connection(self):
        if self.connect_button.text() == "Connect to Server":
            try:
                self.client.sio.connect(self.client.Server_url, wait_timeout=10)
                self.connection_status.setText("Connected")
                self.connect_button.setText("Disconnect")
            except Exception as e:
                self.connection_status.setText("Connection Failed")
                QMessageBox.critical(self, "Connection Error", f"Failed to connect: {str(e)}")
        else:
            try:
                self.client.sio.disconnect()
                self.connection_status.setText("Not Connected")
                self.connect_button.setText("Connect to Server")
            except Exception as e:
                QMessageBox.warning(self, "Disconnect Error", f"Error during disconnect: {str(e)}")

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
                self.connect_serial_button.setText("Disconnect")
                self.serial_timer.start(100)  # Читаем порт каждые 100мс
            except Exception as e:
                QMessageBox.critical(self, "Serial Connection Error", f"Failed to connect: {str(e)}")
        else:
            try:
                self.serial_timer.stop()
                self.serial.close()
                self.serial = None
                self.connect_serial_button.setText("Connect to Port")
            except Exception as e:
                QMessageBox.warning(self, "Serial Disconnect Error", f"Error during disconnect: {str(e)}")
    
    def read_serial(self):
        """Чтение данных из последовательного порта"""
        if self.serial and self.serial.is_open:
            try:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8').strip()
                    print(f"Прочитано из порта: {line}")  # Отладочный вывод
                    if line:  # Проверяем, что строка не пустая
                        self.process_serial_data(line)
            except Exception as e:
                print(f"Ошибка чтения из порта: {str(e)}")
                import traceback
                print(traceback.format_exc())
    
    def process_serial_data(self, data):
        """Обработка данных из порта"""
        print(f"Получены данные: {data}")  # Отладочный вывод
        
        # Обработка обновления настроек
        settings_match = re.match(r"SettingsUpdated{\s*SF:\s*(\d+)\s*TX:\s*(\d+)\s*BW:\s*(\d+\.\d+)\s*}", data)
        if settings_match:
            print("Обнаружено обновление настроек")  # Отладочный вывод
            sf, tx, bw = settings_match.groups()
            self.client.current_settings.update({
                "sf": int(sf),
                "tx": int(tx),
                "bw": float(bw)
            })
            print(f"Настройки обновлены: {self.client.current_settings}")  # Отладочный вывод
            return

        # Обработка информации о пакете
        packet_match = re.match(r"PacketInfo{\s*Rssi:\s*(-?\d+)\s*Snr:\s*(-?\d+\.\d+)\s*Bit errors:\s*(\d+)\s*}", data)
        if packet_match:
            print("Обнаружена информация о пакете")  # Отладочный вывод
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
            print(f"Сформирован пакет: {packet_info}")  # Отладочный вывод
            
            try:
                # Загружаем существующие пакеты
                try:
                    with open(self.current_file, 'r') as f:
                        packets = json.load(f)
                        if not isinstance(packets, list):
                            packets = []
                except (FileNotFoundError, json.JSONDecodeError):
                    packets = []
                
                print(f"Текущее количество пакетов: {len(packets)}")  # Отладочный вывод
                
                # Добавляем новый пакет
                packets.append(packet_info)
                
                # Сохраняем обновленный список
                with open(self.current_file, 'w') as f:
                    json.dump(packets, f, indent=2)
                
                print(f"Пакет сохранен, всего пакетов: {len(packets)}")  # Отладочный вывод
                
                # Обновляем информацию о последнем пакете в интерфейсе
                self.last_datetime_label.setText(f"DateTime: {packet_info['datetime']}")
                self.last_rssi_label.setText(f"RSSI: {packet_info['rssi']}")
                self.last_snr_label.setText(f"SNR: {packet_info['snr']}")
                self.last_errors_label.setText(f"Bit Errors: {packet_info['bit_errors']}")
                self.last_distance_label.setText(f"Distance: {packet_info['distance']} м")
                
                # Принудительно обновляем таблицу
                self.update_data()
                
            except Exception as e:
                print(f"Ошибка при сохранении данных пакета: {str(e)}")
                # Добавляем более подробную информацию об ошибке
                import traceback
                print(traceback.format_exc())

    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        if self.serial and self.serial.is_open:
            self.serial.close()
        event.accept()

    def update_files_list(self):
        """Обновляет список доступных файлов"""
        self.files_combo.clear()
        
        # Получаем список JSON файлов
        files = [f for f in os.listdir("PacketsInfoFiles") if f.endswith('.json')]
        self.files_combo.addItems(files)
        
        # Устанавливаем текущий файл, если он есть в списке
        current_filename = os.path.basename(self.current_file)
        index = self.files_combo.findText(current_filename)
        if index >= 0:
            self.files_combo.setCurrentIndex(index)
            
        # Подключаем обработчик изменения файла
        self.files_combo.currentTextChanged.connect(self.change_current_file)
    
    def change_current_file(self, filename):
        """Обработчик смены текущего файла"""
        if filename:
            self.current_file = os.path.join("PacketsInfoFiles", filename)
            # Обновляем данные в интерфейсе
            self.update_data()
    
    def create_new_file(self):
        """Создает новый файл для записи пакетов"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Create New Packets File",
            "PacketsInfoFiles",
            "JSON Files (*.json)"
        )
        
        if filename:
            # Убеждаемся, что файл находится в нужной директории
            if not filename.startswith(os.path.abspath("PacketsInfoFiles")):
                filename = os.path.join("PacketsInfoFiles", os.path.basename(filename))
            
            # Добавляем расширение .json если его нет
            if not filename.endswith('.json'):
                filename += '.json'
            
            # Создаем пустой файл
            with open(filename, 'w') as f:
                json.dump([], f)
            
            self.current_file = filename
            self.update_files_list()

    def create_new_graphs(self):
        """Создает новые графики из текущего файла"""
        try:
            # Создаем директорию для графиков, если её нет
            os.makedirs("GraphsFiles", exist_ok=True)
            
            # Создаем построитель графиков
            builder = GraphicsBuilder(self.current_file)
            
            # Создаем графики
            snr_plot, rssi_plot = builder.create_all_plots()
            
            # Показываем сообщение об успехе
            QMessageBox.information(
                self,
                "Success",
                f"Graphs created successfully!\nSNR plot: {snr_plot}\nRSSI plot: {rssi_plot}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create graphs: {str(e)}"
            )

