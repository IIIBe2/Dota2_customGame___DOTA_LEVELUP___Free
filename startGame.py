import subprocess
import psutil
import time
import os

import pause_handler

class Dota2Launcher:
    def __init__(self):
        self.steam_path = self.find_steam()
        self.dota2_process_name = "dota2.exe"  # Windows
        
    def find_steam(self):
        """Поиск установленного Steam"""
        possible_paths = [
            r"C:\Program Files (x86)\Steam\steam.exe",
            r"C:\Program Files\Steam\steam.exe",
            os.path.expanduser("~/.steam/steam/steam.sh"),  # Linux
            "/Applications/Steam.app/Contents/MacOS/steam_osx"  # macOS
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Steam найден: {path}")
                return path
        
        print("Steam не найден!")
        return None
    
    def is_steam_running(self):
        """Проверка, запущен ли Steam"""
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'steam' in proc.info['name'].lower():
                return True
        return False
    
    def is_dota2_running(self):
        """Проверка, запущена ли Dota 2"""
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'dota' in proc.info['name'].lower():
                return True
        return False
    
    def start_steam(self):
        """Запуск Steam если не запущен"""
        if not self.is_steam_running():
            print("Запускаем Steam...")
            subprocess.Popen([self.steam_path])
            time.sleep(10)  # Ждем запуска Steam
        else:
            print("Steam уже запущен")
    
    def check_and_fix_keyboard_layout():
        """Проверить и исправить раскладку клавиатуры при запуске"""
        try:
            from telegram_bot import get_bot_manager
            bot_manager = get_bot_manager()
            
            if bot_manager:
                layout_code, layout_name = bot_manager.get_keyboard_layout()
                
                if layout_code != "en":
                    print(f"⚠️ Обнаружена неанглийская раскладка: {layout_name}")
                    print("⌨️ Пытаюсь переключить на английскую...")
                    
                    success, message = bot_manager.force_english_layout_for_dota()
                    print(f"Результат: {message}")
                else:
                    print("✅ Английская раскладка активирована")
        except Exception as e:
            print(f"⚠️ Ошибка при проверке раскладки: {e}")

    def launch_dota2(self, options=None):
        #pause_handler.set_current_operation("Запуск Dota 2", {'options': options})
        """Основной метод запуска Dota 2"""
        if not self.steam_path:
            print("Не удалось найти Steam")
            return False, "Steam не найден на системе"
        
        if self.is_dota2_running():
            print("Dota 2 уже запущена!")
            return True, "Dota 2 уже была запущена"
        
        # Стандартные параметры запуска
        if options is None:
            options = ["-novid", "-high"]
        
        print("Запускаем Dota 2...")
        
        try:
            # Запуск через Steam
            command = [self.steam_path, "-applaunch", "570"] + options
            process = subprocess.Popen(command)
            
            # Ожидание запуска игры
            print("Ожидаем запуск игры...")
            for i in range(30):  # Ждем до 30 секунд
                time.sleep(2)
                if self.is_dota2_running():
                    print("Dota 2 успешно запущена!")
                    return True, "Dota 2 успешно запущена"
                print(f"Ожидание... {i*2} секунд")
            
            print("Dota 2 не запустилась в течение 30 секунд")
            return False, "Таймаут запуска игры"
            
        except Exception as e:
            print(f"Ошибка при запуске Dota 2: {e}")
            return False, f"Ошибка запуска: {str(e)}"
    
    def close_dota2(self):
        """Закрытие Dota 2"""
        for proc in psutil.process_iter(['name', 'pid']):
            if proc.info['name'] and 'dota' in proc.info['name'].lower():
                print(f"Закрываем Dota 2 (PID: {proc.info['pid']})")
                proc.terminate()
                time.sleep(5)
                if proc.is_running():
                    proc.kill()
                return True
        print("Dota 2 не запущена")
        return False

# Функция для запуска из других файлов
def launch_dota_game():
    """Запускает Dota 2 и возвращает статус"""
    launcher = Dota2Launcher()
    
    # Запуск с кастомными параметрами
    custom_options = [
        "-novid",
        "-high", 
        "-dx11",
        "-console"
    ]
    
    # Запускаем Dota 2 и возвращаем результат
    success, message = launcher.launch_dota2(custom_options)
    return success, message

# Если файл запущен напрямую
if __name__ == "__main__":
    success, message = launch_dota_game()
    
    if success:
        print("Игра запущена! Можно начинать автоматизацию...")
    else:
        print("Не удалось запустить Dota 2")