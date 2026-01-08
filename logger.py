import datetime
import os
from config import LOG_FILE

class Logger:
    def __init__(self):
        self.log_file = LOG_FILE
        self.ensure_log_file()
    
    def ensure_log_file(self):
        """Создает файл лога если он не существует"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write("=== ЛОГ АВТОМАТИЗАЦИИ DOTA 2 ===\n")
                f.write(f"Создан: {self.get_timestamp()}\n")
                f.write("=" * 50 + "\n\n")
    
    def get_timestamp(self):
        """Возвращает текущую дату и время в формате строки"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def log_event(self, event_type, message, attempt_number=None):
        """Записывает событие в лог"""
        timestamp = self.get_timestamp()
        attempt_info = f" [Попытка {attempt_number}]" if attempt_number else ""
        log_entry = f"[{timestamp}]{attempt_info} [{event_type}] {message}\n"
        
        print(f"📝 ЛОГ: {log_entry.strip()}")
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def log_dota_start(self, attempt_number):
        """Логирует запуск Dota 2"""
        self.log_event("LAUNCH", "Запуск Dota 2", attempt_number)
    
    def log_dota_close(self, attempt_number, reason):
        """Логирует закрытие Dota 2"""
        self.log_event("CLOSE", f"Закрытие Dota 2. Причина: {reason}", attempt_number)
    
    def log_restart(self, attempt_number, reason):
        """Логирует перезапуск"""
        self.log_event("RESTART", f"Перезапуск. Причина: {reason}", attempt_number)
    
    def log_success(self, attempt_number, operation):
        """Логирует успешное выполнение операции"""
        self.log_event("SUCCESS", f"Успешно: {operation}", attempt_number)
    
    def log_error(self, attempt_number, operation, error_details=""):
        """Логирует ошибку"""
        details = f" - {error_details}" if error_details else ""
        self.log_event("ERROR", f"Ошибка: {operation}{details}", attempt_number)
    
    def log_info(self, message, attempt_number=None):
        """Логирует информационное сообщение"""
        self.log_event("INFO", message, attempt_number)

    def log_host_death(self, death_type, details, attempt_number=None):
        """
        Логирует смерть хоста
        """
        death_name = "9999999 в чате" if death_type == 'gold_text' else "красная рамка"
        message = f"Смерть хоста ({death_name}): {details}"
        self.log_event("HOST_DEATH", message, attempt_number)
        print(f"🔴 ЛОГ СМЕРТИ: {message}")