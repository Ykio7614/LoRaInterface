import matplotlib.pyplot as plt
import numpy as np
import json
import os
from datetime import datetime
from collections import defaultdict

class GraphicsBuilder:
    def __init__(self, json_file_path):
        self.json_file_path = json_file_path
        # Создаем директорию для графиков с тем же именем, что и JSON файл
        self.graphs_dir = os.path.join(
            "../GraphsFiles",
            os.path.splitext(os.path.basename(json_file_path))[0]
        )
        os.makedirs(self.graphs_dir, exist_ok=True)
        self.distance_interval = 15  # интервал для группировки в метрах

    def load_data(self):
        """Загружает и группирует данные из JSON файла по значению BW"""
        with open(self.json_file_path, 'r') as f:
            data = json.load(f)
        
        # Создаем словари для группировки данных по BW
        bw_groups = defaultdict(lambda: {'distances': [], 'snr': [], 'rssi': []})
        
        # Группируем данные по значению BW
        for packet in data:
            bw = float(packet['bw'])
            bw_groups[bw]['distances'].append(float(packet['distance']))
            bw_groups[bw]['snr'].append(float(packet['snr']))
            bw_groups[bw]['rssi'].append(float(packet['rssi']))
        
        return bw_groups

    def average_by_distance_intervals(self, distances, values):
        """Группирует и усредняет значения по интервалам расстояний"""
        if not distances or not values:
            return [], []
            
        # Создаем интервалы на основе минимального и максимального расстояния
        min_dist = min(distances)
        max_dist = max(distances)
        intervals = np.arange(min_dist, max_dist + self.distance_interval, self.distance_interval)
        
        avg_distances = []
        avg_values = []
        
        # Группируем и усредняем значения по интервалам
        for i in range(len(intervals)-1):
            start = intervals[i]
            end = intervals[i+1]
            
            # Находим все значения в текущем интервале
            mask = (np.array(distances) >= start) & (np.array(distances) < end)
            if np.any(mask):
                interval_values = np.array(values)[mask]
                interval_distances = np.array(distances)[mask]
                
                # Вычисляем средние значения
                avg_distances.append(np.mean(interval_distances))
                avg_values.append(np.mean(interval_values))
        
        return avg_distances, avg_values

    def create_snr_plot(self):
        """Создает график зависимости SNR от расстояния для разных значений BW"""
        bw_groups = self.load_data()
        
        plt.figure(figsize=(12, 8))
        
        # Разные цвета для разных значений BW
        colors = plt.cm.rainbow(np.linspace(0, 1, len(bw_groups)))
        
        for (bw, color) in zip(sorted(bw_groups.keys()), colors):
            # Получаем усредненные значения
            avg_distances, avg_snr = self.average_by_distance_intervals(
                bw_groups[bw]['distances'], 
                bw_groups[bw]['snr']
            )
            
            if avg_distances and avg_snr:
                plt.scatter(avg_distances, avg_snr, alpha=0.7, label=f'BW = {bw} kHz')
                plt.plot(avg_distances, avg_snr, '-', color=color, alpha=0.5)
        
        plt.xlabel('Расстояние (м)')
        plt.ylabel('SNR (дБ)')
        plt.title(f'Зависимость SNR от расстояния (усреднение по {self.distance_interval}м)')
        plt.grid(True)
        plt.legend()
        
        # Добавляем временную метку к имени файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.graphs_dir, f'snr_vs_distance_averaged_{timestamp}.png')
        plt.savefig(filename)
        plt.close()
        
        return filename

    def create_rssi_plot(self):
        """Создает график зависимости RSSI от расстояния для разных значений BW"""
        bw_groups = self.load_data()
        
        plt.figure(figsize=(12, 8))
        
        # Разные цвета для разных значений BW
        colors = plt.cm.rainbow(np.linspace(0, 1, len(bw_groups)))
        
        for (bw, color) in zip(sorted(bw_groups.keys()), colors):
            # Получаем усредненные значения
            avg_distances, avg_rssi = self.average_by_distance_intervals(
                bw_groups[bw]['distances'], 
                bw_groups[bw]['rssi']
            )
            
            if avg_distances and avg_rssi:
                plt.scatter(avg_distances, avg_rssi, alpha=0.7, label=f'BW = {bw} kHz')
                plt.plot(avg_distances, avg_rssi, '-', color=color, alpha=0.5)
        
        plt.xlabel('Расстояние (м)')
        plt.ylabel('RSSI (дБм)')
        plt.title(f'Зависимость RSSI от расстояния (усреднение по {self.distance_interval}м)')
        plt.grid(True)
        plt.legend()
        
        # Добавляем временную метку к имени файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.graphs_dir, f'rssi_vs_distance_averaged_{timestamp}.png')
        plt.savefig(filename)
        plt.close()
        
        return filename

    def create_all_plots(self):
        """Создает все графики"""
        snr_plot = self.create_snr_plot()
        rssi_plot = self.create_rssi_plot()
        return snr_plot, rssi_plot
    
