# utils.py (простой вариант)

import time
from pause_handler import pause_handler

def run_with_pause_aware_timeout(timeout_seconds, operation_name, check_interval=1):
    """
    Генератор для использования в циклах с таймаутом
    Возвращает (should_continue, elapsed_seconds)
    
    Использование:
    start_time = time.time()
    for should_continue, elapsed in run_with_pause_aware_timeout(60, "Поиск кнопки"):
        if not should_continue:
            break
            
        # Ваш код поиска...
        if found_button():
            break
            
        time.sleep(check_interval)
    """
    start_time = time.time()
    
    while True:
        # Проверяем паузу и запросы на остановку
        if not pause_handler.check_pause(operation_name):
            yield False, pause_handler.get_real_elapsed_time(start_time)
            break
        
        # Рассчитываем прошедшее время без учета паузы
        elapsed = pause_handler.get_real_elapsed_time(start_time)
        
        # Проверяем таймаут
        if elapsed >= timeout_seconds:
            print(f"⏰ Таймаут {operation_name}: {elapsed:.1f}с ≥ {timeout_seconds}с")
            yield False, elapsed
            break
        
        # Показываем статус каждые 30 секунд
        if int(elapsed) % 30 == 0:
            remaining = timeout_seconds - elapsed
            print(f"⏱ {operation_name}: прошло {elapsed:.1f}с, осталось {remaining:.1f}с")
        
        yield True, elapsed
        time.sleep(check_interval)