# config_loader.py
import os
import importlib.util
import sys
from typing import Any

class ConfigLoader:
    def __init__(self):
        self.config_file = "config.py"
        self.last_modified_time = 0
        
    def get_value(self, key: str, default: Any = None) -> Any:
        """Динамически читает значение из config.py"""
        try:
            # Проверяем время изменения файла
            if os.path.exists(self.config_file):
                current_mtime = os.path.getmtime(self.config_file)
                
                # Если файл изменился, принудительно перезагружаем модуль
                if current_mtime > self.last_modified_time:
                    self._reload_config()
                    self.last_modified_time = current_mtime
            
            # Используем альтернативный метод загрузки
            return self._load_value(key, default)
            
        except Exception as e:
            print(f"⚠️ Ошибка при чтении config.{key}: {e}")
            return default
    
    def _reload_config(self):
        """Принудительная перезагрузка модуля config"""
        try:
            # Удаляем модуль из кэша
            if 'config' in sys.modules:
                del sys.modules['config']
        except:
            pass
    
    def _load_value(self, key: str, default: Any) -> Any:
        """Загружает значение, читая файл напрямую"""
        try:
            # Метод 1: Чтение файла как текста
            with open(self.config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Ищем переменную в тексте
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith(f"{key} ="):
                    # Извлекаем значение после знака =
                    value_part = line.split('=', 1)[1].strip()
                    
                    # Убираем комментарии
                    if '#' in value_part:
                        value_part = value_part.split('#')[0].strip()
                    
                    # Обрабатываем строки
                    if value_part.startswith('"') and value_part.endswith('"'):
                        return value_part[1:-1]
                    elif value_part.startswith("'") and value_part.endswith("'"):
                        return value_part[1:-1]
                    else:
                        # Пробуем конвертировать другие типы
                        try:
                            return eval(value_part)
                        except:
                            return value_part
        except Exception as e:
            print(f"⚠️ Ошибка при парсинге config.{key}: {e}")
        
        # Метод 2: Используем importlib если первый метод не сработал
        try:
            spec = importlib.util.spec_from_file_location("config", self.config_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, key, default)
        except:
            pass
        
        return default

# Глобальный экземпляр загрузчика
config_loader = ConfigLoader()

# Удобная функция для использования
def get_config(key: str, default: Any = None) -> Any:
    return config_loader.get_value(key, default)