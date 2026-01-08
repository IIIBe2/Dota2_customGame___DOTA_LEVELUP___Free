# dynamic_config.py
import ast
import os
import time

class DynamicConfig:
    def __init__(self):
        self.config_file = "config.py"
        self.cache = {}
        self.cache_time = 0
        self.file_mtime = 0
        
    def get(self, key, default=None):
        """Получает значение напрямую из файла, минуя импорт Python"""
        try:
            # Проверяем время изменения файла
            current_mtime = os.path.getmtime(self.config_file)
            
            # Если файл изменился или кэш пустой, перечитываем
            if current_mtime != self.file_mtime or not self.cache:
                self._parse_config_file()
                self.file_mtime = current_mtime
            
            return self.cache.get(key, default)
            
        except Exception as e:
            print(f"⚠️ Динамическое чтение {key}: {e}")
            return default
    
    def _parse_config_file(self):
        """Парсит config.py напрямую как Python файл"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Ищем все присваивания переменных
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_name = target.id
                            try:
                                # Пытаемся вычислить значение
                                value = ast.literal_eval(node.value)
                                self.cache[var_name] = value
                            except:
                                # Для сложных выражений - пытаемся как строку
                                try:
                                    value_str = ast.unparse(node.value)
                                    if value_str.startswith('"') and value_str.endswith('"'):
                                        self.cache[var_name] = value_str[1:-1]
                                    elif value_str.startswith("'") and value_str.endswith("'"):
                                        self.cache[var_name] = value_str[1:-1]
                                except:
                                    pass
        except Exception as e:
            print(f"⚠️ Ошибка парсинга config.py: {e}")

# Глобальный экземпляр
dynamic_config = DynamicConfig()

# Удобная функция
def get_dynamic_config(key, default=None):
    return dynamic_config.get(key, default)