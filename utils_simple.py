# utils_simple.py (новый простой файл)

import time
from pause_handler import pause_handler

def run_with_timeout_considering_pause(timeout_seconds, operation_name, func, *args, **kwargs):
    """
    Простая обертка для запуска функций с таймаутом, учитывающим паузу
    """
    start_time = time.time()
    attempt = 0
    
    while True:
        attempt += 1
        
        # Проверяем паузу с учетом времени
        should_continue, elapsed = pause_handler.check_pause_with_real_timeout(
            operation_name,
            timeout_seconds,
            start_time
        )
        
        if not should_continue:
            if elapsed >= timeout_seconds:
                print(f"⏰ {operation_name}: таймаут {timeout_seconds} секунд истек")
                return None
            else:
                print(f"🛑 {operation_name}: прервано")
                return None
        
        # Вызываем функцию
        result = func(*args, **kwargs)
        
        # Если функция вернула результат - возвращаем его
        if result is not None:
            return result
        
        # Если функция ничего не вернула, ждем и продолжаем цикл
        time.sleep(1)