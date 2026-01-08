# pause_handler.py
import keyboard
import time
import threading
import os
import sys

class PauseHandler:
    def __init__(self):
        self.paused = False
        self.shutdown_requested = False
        self.restart_requested = False
        self.restart_reason = ""
        self.pause_lock = threading.Lock()
        self.shutdown_lock = threading.Lock()
        self.restart_lock = threading.Lock()
        
        # 🔥 ПРОСТОЕ ДОБАВЛЕНИЕ ДЛЯ УЧЕТА ВРЕМЕНИ НА ПАУЗЕ
        self.pause_start_time = None  # Когда началась текущая пауза
        self.total_pause_time = 0.0   # Общее время на паузе в этой сессии
        
        self.current_operation = "Инициализация"
        self.last_operation = "Инициализация"
        self.operation_start_time = time.time()
        self.operation_details = {}

        # 🔥 ИНИЦИАЛИЗИРУЕМ status_history (если используется где-то)
        self.status_history = []  # ✅ ДОБАВЛЯЕМ ЭТУ СТРОКУ
        self.max_history_size = 50  # ✅ ДОБАВЛЯЕМ ЭТУ СТРОКУ

        self.setup_hotkeys()

    
    def set_current_operation(self, operation_name, details=None):
        """Установка текущей операции с сохранением в историю"""
        # Сохраняем предыдущую операцию в историю
        history_entry = {
            'timestamp': time.time(),
            'time_str': time.strftime("%H:%M:%S"),
            'operation': self.current_operation,
            'details': self.operation_details.copy() if self.operation_details else {},
            'duration': time.time() - self.operation_start_time
        }
        
        self.status_history.append(history_entry)
        
        # Ограничиваем размер истории
        if len(self.status_history) > self.max_history_size:
            self.status_history = self.status_history[-self.max_history_size:]
        
        # Устанавливаем новую операцию
        self.current_operation = operation_name
        self.operation_start_time = time.time()
        if details:
            self.operation_details = details
        else:
            self.operation_details = {}
        
        print(f"📱 Текущая операция: {operation_name}")
        if details:
            print(f"   📋 Детали: {details}")

    def get_status_history(self, limit=10):
        """Получение истории статусов"""
        history = self.status_history[-limit:] if self.status_history else []
        return history

    def get_detailed_status_for_telegram(self):
        """Детальный статус с историей для Telegram"""
        current_status = self.get_current_status()
        history = self.get_status_history(5)  # Последние 5 операций
        
        status_text = f"""
    📱 *ДЕТАЛЬНЫЙ СТАТУС ПРОГРАММЫ*

    🎯 *Текущая операция:* {current_status['current_operation']}
    ⏱️ *В работе:* {current_status['operation_duration']}
    📅 *Время:* {current_status['timestamp']}

    💡 *Детали операции:*
    """
        
        # Добавляем детали
        details = current_status.get('operation_details', {})
        for key, value in details.items():
            status_text += f"• *{key}:* {value}\n"
        
        # Добавляем историю
        if history:
            status_text += "\n📋 *ИСТОРИЯ ОПЕРАЦИЙ:*\n"
            for i, entry in enumerate(reversed(history), 1):
                duration_str = f"{int(entry['duration'])}сек"
                if entry['duration'] > 60:
                    minutes = int(entry['duration'] // 60)
                    seconds = int(entry['duration'] % 60)
                    duration_str = f"{minutes}м {seconds}сек"
                
                status_text += f"{i}. {entry['time_str']}: {entry['operation']} ({duration_str})\n"
        
        return status_text
    
    def update_operation_details(self, details):
        """Обновление деталей текущей операции"""
        self.operation_details.update(details)
    
    def get_current_status(self):
        """Получение текущего статуса программы"""
        operation_duration = time.time() - self.operation_start_time
        
        # Форматируем время операции
        if operation_duration < 60:
            duration_str = f"{int(operation_duration)}сек"
        elif operation_duration < 3600:
            minutes = int(operation_duration // 60)
            seconds = int(operation_duration % 60)
            duration_str = f"{minutes}м {seconds}сек"
        else:
            hours = int(operation_duration // 3600)
            minutes = int((operation_duration % 3600) // 60)
            duration_str = f"{hours}ч {minutes}м"
        
        status = {
            'paused': self.paused,
            'shutdown_requested': self.shutdown_requested,
            'restart_requested': self.restart_requested,
            'current_operation': self.current_operation,
            'operation_duration': duration_str,
            'operation_details': self.operation_details,
            'timestamp': time.strftime("%H:%M:%S")
        }
        
        return status
        
    def setup_hotkeys(self):
        """Устанавливает горячие клавиши для паузы/продолжения и завершения"""
        # Основная горячая клавиша F11 - пауза/продолжение
        keyboard.on_press_key('F11', self.toggle_pause)
        
        # Горячая клавиша F10 - завершение программы
        keyboard.on_press_key('F10', self.request_shutdown)
        
        # Альтернативная комбинация клавиш (работает даже в Dota 2)
        keyboard.add_hotkey('ctrl+shift+p', self.toggle_pause)
        
        print("🎮 Горячие клавиши установлены:")
        print("   F11 - пауза/продолжение (может не работать в Dota 2)")
        print("   Ctrl+Shift+P - пауза/продолжение (работает всегда)")
        print("   F10 - завершение программы")
    
    def show_notification(self, title, message):
        """Показывает уведомление через консоль и звук"""
        try:
            # Выводим в консоль
            print(f"\n🔔 {title}: {message}")
            
            # Издаем звуковой сигнал (бип)
            print('\a')  # Это вызовет системный звук
            
            # Дополнительные визуальные эффекты
            print("!" * 50)
            print(f"! {title:^46} !")
            print(f"! {message:^46} !") 
            print("!" * 50)
            
        except Exception as e:
            print(f"⚠️ Не удалось показать уведомление: {e}")
    
    def toggle_pause(self, event=None):
        """Переключает состояние паузы"""
        with self.pause_lock:
            self.paused = not self.paused
            if self.paused:
                # 🔥 ЗАПОМИНАЕМ КОГДА НАЧАЛАСЬ ПАУЗА
                self.pause_start_time = time.time()
                print("\n⏸️ ПАУЗА: Скрипт приостановлен.")
                print("   Нажмите F11 или Ctrl+Shift+P для продолжения...")
                self.show_notification("Dota 2 Automator - ПАУЗА", "Скрипт приостановлен")
            else:
                # 🔥 РАССЧИТЫВАЕМ СКОЛЬКО БЫЛО НА ПАУЗЕ И ДОБАВЛЯЕМ В ОБЩЕЕ ВРЕМЯ
                if self.pause_start_time:
                    pause_duration = time.time() - self.pause_start_time
                    self.total_pause_time += pause_duration
                    print(f"⏱ Время на паузе: {pause_duration:.1f} секунд")
                    self.pause_start_time = None
                
                print("\n▶️ ПРОДОЛЖЕНИЕ: Скрипт возобновляет работу...")
                self.show_notification("Dota 2 Automator - ПРОДОЛЖЕНИЕ", "Скрипт возобновляет работу")
    
    def get_adjusted_time(self, operation_start_time=None):
        """
        Возвращает время с учетом пауз
        Если передан start_time, возвращает прошедшее время с учетом пауз
        """
        current_time = time.time()
        
        if operation_start_time:
            # Рассчитываем прошедшее время с учетом текущей паузы
            elapsed = current_time - operation_start_time - self.total_pause_time
            
            # Если сейчас на паузе, не считаем время текущей паузы
            if self.paused and self.pause_start_time:
                elapsed -= (current_time - self.pause_start_time)
            
            return elapsed
        else:
            # Возвращаем текущее время с поправкой на паузы
            return current_time - self.total_pause_time

    def check_pause_with_timeout(self, operation_name, timeout, start_time=None):
        """
        Улучшенная проверка паузы с учетом таймаута
        Возвращает: (should_continue, elapsed_time_without_pauses)
        """
        # 🔥 Определяем время начала если не передано
        if start_time is None:
            start_time = time.time()
        
        # Проверяем запросы на перезапуск и завершение
        restart_requested, restart_reason = self.check_restart()
        if restart_requested:
            print(f"🔄 Операция '{operation_name}' прервана - немедленный перезапуск: {restart_reason}")
            return False, 0
        
        if self.shutdown_requested:
            print(f"🛑 Операция '{operation_name}' прервана - завершение программы")
            return False, 0
        
        # 🔥 Рассчитываем прошедшее время БЕЗ учета времени на паузе
        elapsed_without_pauses = self.get_adjusted_time(start_time)
        
        # Проверяем таймаут
        if elapsed_without_pauses >= timeout:
            print(f"⏰ Таймаут операции '{operation_name}' истек: {elapsed_without_pauses:.1f}с ≥ {timeout}с")
            return False, elapsed_without_pauses
        
        # 🔥 Проверяем паузу с информацией о времени
        if self.paused:
            remaining_time = timeout - elapsed_without_pauses
            print(f"⏸️ Операция '{operation_name}' на паузе. Осталось времени: {remaining_time:.1f}с")
            
            # Ждем снятия паузы
            self.wait_if_paused()
            
            # После паузы снова проверяем завершение/перезапуск
            if self.shutdown_requested or restart_requested:
                return False, elapsed_without_pauses
            
            # 🔥 Возвращаем true чтобы продолжить, время уже учтено в get_adjusted_time
            return True, elapsed_without_pauses
        
        # 🔥 Если не на паузе и время не вышло, продолжаем
        remaining_time = timeout - elapsed_without_pauses
        if int(elapsed_without_pauses) % 30 == 0:  # Каждые 30 секунд
            print(f"⏱ Операция '{operation_name}': прошло {elapsed_without_pauses:.1f}с, осталось {remaining_time:.1f}с")
        
        return True, elapsed_without_pauses

    def wait_with_timeout(self, operation_name, timeout, callback=None):
        """
        Ожидание с таймаутом, которое учитывает паузу
        callback - функция, которая вызывается периодически (если нужно)
        """
        start_time = time.time()
        last_callback_time = start_time
        
        while True:
            should_continue, elapsed = self.check_pause_with_timeout(
                operation_name, 
                timeout, 
                start_time
            )
            
            if not should_continue:
                return False, elapsed
            
            # Вызываем callback если нужно
            if callback and time.time() - last_callback_time > 5.0:  # Каждые 5 секунд
                callback(elapsed, timeout - elapsed)
                last_callback_time = time.time()
            
            # Проверяем завершение таймаута
            if elapsed >= timeout:
                return False, elapsed
            
            # Ждем немного
            time.sleep(1)
        
        return True, elapsed

    def request_shutdown(self, event=None):
        """Запрашивает завершение программы"""
        with self.shutdown_lock:
            if not self.shutdown_requested:
                self.shutdown_requested = True
                print("\n🛑 ЗАВЕРШЕНИЕ: Запрошено завершение программы...")
                print("   Программа завершится после текущей операции.")
                self.show_notification(
                    "Dota 2 Automator - ЗАВЕРШЕНИЕ", 
                    "Запрошено завершение программы"
                )
    
    def check_shutdown(self):
        """Проверяет, запрошено ли завершение программы"""
        return self.shutdown_requested
    
    def wait_if_paused(self):
        """Блокирует выполнение если скрипт на паузе"""
        while self.paused and not self.shutdown_requested:
            time.sleep(0.5)
    
    def request_restart(self, reason=""):
        """Запрашивает немедленный перезапуск программы"""
        with self.restart_lock:
            if not self.restart_requested:
                self.restart_requested = True
                self.restart_reason = reason
                print(f"\n🔄 ЗАПРОШЕН НЕМЕДЛЕННЫЙ ПЕРЕЗАПУСК!")
                print(f"   Причина: {reason}")
                self.show_notification(
                    "Dota 2 Automator - ПЕРЕЗАПУСК", 
                    f"Запрошен немедленный перезапуск: {reason}"
                )
                return True
        return False
    
    def check_restart(self):
        """Проверяет, запрошен ли перезапуск"""
        with self.restart_lock:
            return self.restart_requested, self.restart_reason
    
    def clear_restart(self):
        """Очищает флаг перезапуска"""
        with self.restart_lock:
            self.restart_requested = False
            self.restart_reason = ""

    def get_real_elapsed_time(self, start_time):
        """
        Возвращает реальное прошедшее время БЕЗ учета времени на паузе
        """
        current_time = time.time()
        
        # 🔥 ПРОСТОЙ И ПРАВИЛЬНЫЙ РАСЧЕТ:
        # 1. Общее прошедшее время
        total_elapsed = current_time - start_time
        
        # 2. Вычитаем общее время на паузе
        elapsed_without_pauses = total_elapsed - self.total_pause_time
        
        # 3. Если сейчас на паузе, вычитаем текущую паузу
        if self.paused and self.pause_start_time:
            current_pause_duration = current_time - self.pause_start_time
            elapsed_without_pauses -= current_pause_duration
        
        # 🔥 НЕ ДОПУСКАЕМ ОТРИЦАТЕЛЬНЫХ ЗНАЧЕНИЙ
        if elapsed_without_pauses < 0:
            return 0.0
        
        return elapsed_without_pauses
    
    def check_pause_with_real_timeout(self, operation_name, timeout, start_time):
        """
        Простая проверка паузы с учетом реального времени (без времени на паузе)
        Возвращает: (should_continue, elapsed_without_pauses)
        """
        # 1. Сначала проверяем обычные прерывания
        if not self.check_pause(operation_name):
            restart_requested, _ = self.check_restart()
            if restart_requested:
                return False, 0
            if self.shutdown_requested:
                return False, 0
            return False, 0
        
        # 2. Рассчитываем прошедшее время БЕЗ учета пауз
        elapsed_without_pauses = self.get_real_elapsed_time(start_time)
        
        # 3. Проверяем таймаут
        if elapsed_without_pauses >= timeout:
            print(f"⏰ Таймаут операции '{operation_name}' истек: {elapsed_without_pauses:.1f}с ≥ {timeout}с")
            return False, elapsed_without_pauses
        
        # 4. Если не на паузе, показываем статус каждые 30 секунд
        if not self.paused and int(elapsed_without_pauses) % 30 == 0:
            remaining = timeout - elapsed_without_pauses
            print(f"⏱ Операция '{operation_name}': прошло {elapsed_without_pauses:.1f}с, осталось {remaining:.1f}с")
        
        return True, elapsed_without_pauses

    def check_pause(self, operation_name=""):
        """
        Базовая проверка паузы (оставляем как есть для совместимости)
        """
        restart_requested, restart_reason = self.check_restart()
        if restart_requested:
            print(f"🔄 Операция '{operation_name}' прервана - перезапуск")
            return False
            
        if self.shutdown_requested:
            print(f"🛑 Операция '{operation_name}' прервана - завершение")
            return False
            
        if self.paused:
            if operation_name:
                print(f"⏸️ Операция '{operation_name}' на паузе...")
            self.wait_if_paused()
            
            # После паузы снова проверяем
            if self.shutdown_requested or restart_requested:
                return False
                
        return True

    def force_pause(self):
        """Принудительно ставит на паузу"""
        with self.pause_lock:
            if not self.paused:
                self.paused = True
                print("\n⏸️ ПРИНУДИТЕЛЬНАЯ ПАУЗА: Скрипт приостановлен.")
                self.show_notification(
                    "Dota 2 Automator - ПАУЗА", 
                    "Скрипт приостановлен"
                )
    
    def force_resume(self):
        """Принудительно снимает с паузы"""
        with self.pause_lock:
            if self.paused:
                self.paused = False
                print("\n▶️ ПРИНУДИТЕЛЬНОЕ ПРОДОЛЖЕНИЕ: Скрипт возобновляет работу...")
                self.show_notification(
                    "Dota 2 Automator - ПРОДОЛЖЕНИЕ", 
                    "Скрипт возобновляет работу"
                )

    def graceful_shutdown(self):
        """Выполняет graceful shutdown программы"""
        print("\n🎯 Завершение программы...")
        print("Спасибо за использование Dota 2 Automator!")
        # Здесь можно добавить сохранение статистики или другие завершающие действия
        sys.exit(0)

# Глобальный экземпляр
pause_handler = PauseHandler()