# AFK_lobby.py
import time
import pyautogui
import pytesseract
import os
from PIL import Image, ImageEnhance, ImageOps
import config
from pause_handler import pause_handler
from config import ENABLE_DEBUG_SCREENSHOTS, GOLD_MONITOR_TIMEOUT, GOLD_CHECK_INTERVAL, INFINITE_ATTEMPT_INTERVAL
from statistics import stats
from avatar_monitor import AvatarMonitor
from infinite_mode import InfiniteMode


class AFKLobbyMonitor:
    def __init__(self, logger):
        self.logger = logger
        self.avatar_monitor = AvatarMonitor(logger)
        self.setup_tesseract()
        self.infinite_mode = InfiniteMode(logger)
        self.gold_monitor_start_time = None
        self.lobby_timeout = GOLD_MONITOR_TIMEOUT
        self.arrow_delay = 420  # 7 минут в секундах

        # 🔥 ДОБАВЛЯЕМ PET_MANAGER
        from pet_manager import PetManager
        self.pet_manager = PetManager(logger)
        
        # 🔥 ДЛЯ ОТСЛЕЖИВАНИЯ ТРИГГЕРОВ
        self.last_trigger_check = {}
        self.last_trigger_check_time = time.time()
    
    def setup_tesseract(self):
        """
        Настройка пути к Tesseract
        """
        possible_tesseract_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]
        
        found_path = None
        for path in possible_tesseract_paths:
            if os.path.exists(path):
                found_path = path
                break
        
        if found_path:
            pytesseract.pytesseract.tesseract_cmd = found_path
            print(f"✅ Tesseract найден: {found_path}")
        else:
            print("❌ Tesseract не найден. Установите Tesseract-OCR")
    
    def press_enter(self):
        """Нажимает кнопку ENTER для активации чата"""
        try:
            pyautogui.press('enter')
            time.sleep(0.2)
            return True
        except Exception as e:
            print(f"⚠️ Ошибка при нажатии ENTER: {e}")
            return False
    
    def close_chat(self):
        """Закрывает чат с помощью ESC"""
        try:
            pyautogui.press('esc')
            time.sleep(0.2)
            return True
        except Exception as e:
            print(f"⚠️ Ошибка при закрытии чата: {e}")
            return False
    
    def check_gold_text_fast(self):
        """
        УЛУЧШЕННЫЙ поиск текста 9999999 в чате (текст должен СОДЕРЖАТЬ 9999999)
        """
        try:
            print("💰 ПОИСК 9999999 В ОБЛАСТИ ЧАТА")
            
            # Активация чата
            self.press_enter()
            time.sleep(0.3)
            
            # Область чата - ниже центра экрана
            screen_width, screen_height = pyautogui.size()
            chat_region = (
                int(screen_width * 0.2),    # 20% от левого края  
                int(screen_height * 0.35),  # 35% от верха (ЦЕНТР ЭКРАНА)
                int(screen_width * 0.6),    # 60% ширины
                int(screen_height * 0.4)    # 40% высоты
            )
            
            print(f"📐 Область чата: {chat_region}")
            screenshot = pyautogui.screenshot(region=chat_region)
            
            # Закрытие чата
            self.close_chat()
            
            # 🔥 ОПТИМИЗИРОВАННАЯ ОБРАБОТКА ДЛЯ ЧАТА
            if screenshot.mode != 'L':
                processed = screenshot.convert('L')
            else:
                processed = screenshot.copy()
            
            # Увеличение контраста для белого текста в чате
            enhancer = ImageEnhance.Contrast(processed)
            processed = enhancer.enhance(3.0)  # Сильный контраст
            
            # Бинаризация для белого текста
            binary = processed.point(lambda x: 255 if x > 200 else 0)
            
            # 🔥 ТОЛЬКО ОДНА НАСТРОЙКА TESSERACT - как раньше
            custom_config = r'--oem 3 --psm 6'
            data = pytesseract.image_to_data(
                binary, 
                output_type=pytesseract.Output.DICT,
                config=custom_config,
                lang='eng'
            )
            
            # 🔥 ПОИСК ТЕКСТА, КОТОРЫЙ СОДЕРЖИТ 9999999
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                confidence = int(data['conf'][i])
                
                # 🔥 ИЩЕМ ЛЮБОЙ ТЕКСТ, КОТОРЫЙ СОДЕРЖИТ "9999999"
                if "9999999" in text and confidence > 40:
                    print(f"🎉 НАЙДЕНО: '{text}'! Уверенность: {confidence}%")
                    if ENABLE_DEBUG_SCREENSHOTS:
                        # Сохраняем скриншот для отладки при успешном нахождении
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        debug_dir = "debug/gold"
                        import os
                        os.makedirs(debug_dir, exist_ok=True)
                        screenshot.save(f"{debug_dir}/gold_found_{timestamp}.png")
                    
                    return True
            
            print("❌ Текст содержащий 9999999 не найден в этой проверке")
            return False
            
        except Exception as e:
            print(f"⚠️ Ошибка при поиске 9999999: {e}")
            return False

    def check_infinite_triggers(self, current_cycles):
        """
        Проверка триггеров бесконечки и выполнение переключения питомцев
        """
        if not hasattr(self, 'pet_manager'):
            print("❌ PetManager не доступен!")
            return
        
        # Проверяем питомцев через pet_manager
        triggered_pets = self.pet_manager.check_infinite_triggers(current_cycles)
        
        if not triggered_pets:
            # 🔥 ДОБАВЛЯЕМ ОТЛАДОЧНУЮ ИНФОРМАЦИЮ
            print(f"ℹ️ Триггеры не сработали при {current_cycles} циклах")
            return
        
        print(f"🎯 НАЙДЕНО ТРИГГЕРОВ: {len(triggered_pets)}")
        
        for trigger_info in triggered_pets:
            pet_id = trigger_info['pet_id']
            trigger_cycles = trigger_info['trigger_cycles']
            
            # 🔥 ПРОВЕРЯЕМ, ЧТОБЫ ТРИГГЕР НЕ СРАБАТЫВАЛ МНОГОКРАТНО
            trigger_key = f"{pet_id}_{trigger_cycles}"
            
            should_trigger = (
                trigger_key not in self.last_trigger_check or 
                self.last_trigger_check[trigger_key] < trigger_cycles
            )
            
            print(f"🔍 Триггер для {pet_id} : {trigger_cycles} циклов")
            print(f"   Текущие циклы: {current_cycles}")
            print(f"   Должен сработать: {'✅ ДА' if should_trigger else '❌ НЕТ (уже срабатывал)'}")
            
            if should_trigger:
                print(f"\n🎯 ВЫПОЛНЕНИЕ ТРИГГЕРА БЕСКОНЕЧКИ!")
                print(f"   Питомец: {trigger_info['pet_name']}")
                print(f"   Триггер: {trigger_cycles} циклов")
                print(f"   Текущие: {current_cycles} циклов")
                
                # 🔥 ОТПРАВЛЯЕМ В ТЕЛЕГРАМ СРАЗУ
                self.send_telegram_notification(
                    trigger_info['pet_name'],
                    trigger_cycles,
                    current_cycles
                )
                
                # 🔥 ВЫПОЛНЯЕМ ПЕРЕКЛЮЧЕНИЕ С ПРИОСТАНОВКОЙ ДРУГИХ ДЕЙСТВИЙ
                try:
                    # Приостанавливаем бесконечку на время переключения
                    print("⏸️ Приостанавливаем бесконечку на время переключения...")
                    
                    # Временно отключаем бесконечку
                    infinite_was_active = self.infinite_mode.is_active
                    if self.infinite_mode.is_active:
                        self.infinite_mode.is_active = False
                        print("   Бесконечка приостановлена")
                    
                    # Выполняем переключение
                    success, message = self.pet_manager.execute_triggered_switch(
                        pet_id, 
                        current_cycles, 
                        trigger_cycles
                    )
                    
                    if success:
                        print(f"✅ Переключение выполнено: {message}")
                        # Запоминаем, что триггер сработал
                        self.last_trigger_check[trigger_key] = current_cycles
                        
                        # 🔥 ЗАПИСЫВАЕМ В СТАТИСТИКУ
                        try:
                            from statistics import stats
                            stats.record_pet_switch_by_trigger(
                                pet_id,
                                trigger_info['pet_name'],
                                trigger_cycles,
                                current_cycles
                            )
                            print("📊 Статистика записана")
                        except Exception as e:
                            print(f"⚠️ Ошибка записи статистики: {e}")
                    else:
                        print(f"❌ Ошибка переключения: {message}")
                    
                    # Восстанавливаем состояние бесконечки
                    if infinite_was_active:
                        self.infinite_mode.is_active = True
                        print("▶️ Бесконечка восстановлена")
                    
                except Exception as e:
                    print(f"❌ Ошибка при выполнении триггера: {e}")
                    import traceback
                    traceback.print_exc()
                
                print("▶️ Возобновляем нормальную работу...")

    def send_telegram_notification(self, pet_name, trigger_cycles, current_cycles):
        """Отправка уведомления в Telegram о срабатывании триггера"""
        try:
            from telegram_bot import get_bot_manager
            from config import TELEGRAM_ADMIN_IDS
            
            bot_manager = get_bot_manager()
            if bot_manager and hasattr(bot_manager, 'bot') and TELEGRAM_ADMIN_IDS:
                chat_id = TELEGRAM_ADMIN_IDS[0]
                
                message = (
                    f"🎯 *Сработал триггер бесконечки!*\n\n"
                    f"🌀 *Циклов бесконечки:* {current_cycles}\n"
                    f"🎯 *Триггер сработал при:* {trigger_cycles} циклов\n"
                    f"🐾 *Переключаемся на питомца:* {pet_name}\n\n"
                    f"⏳ Переключение займет примерно 10 секунд"
                )
                
                bot_manager.bot.send_message(
                    chat_id,
                    message,
                    parse_mode='Markdown'
                )
                
                print(f"✅ Уведомление отправлено в Telegram")
                
        except Exception as e:
            print(f"⚠️ Не удалось отправить уведомление в Telegram: {e}")

    def monitor_after_accept(self, restart_count=0):
        """
        Мониторинг AFK лобби с учетом времени на паузе
        """
        print("🎯 МОНИТОРИНГ AFK ЛОББИ С ОТСЛЕЖИВАНИЕМ ЦВЕТА РАМКИ")
        print("⚙️ Бесконечка: " + ("ВКЛЮЧЕНА" if self.infinite_mode.enabled else "ВЫКЛЮЧЕНА"))
        
        # 🔥 ДОБАВЛЯЕМ ОТЛАДОЧНУЮ ИНФОРМАЦИЮ
        print(f"📊 PetManager доступен: {hasattr(self, 'pet_manager')}")
        if hasattr(self, 'pet_manager'):
            print(f"📊 Питомцев в системе: {len(self.pet_manager.pets)}")

        # 🔥 ОБНОВЛЯЕМ ТЕКУЩУЮ ОПЕРАЦИЮ
        pause_handler.set_current_operation("AFK мониторинг", {
            'stage': 'Начало мониторинга',
            'arrow_found': False,
            'frame_found': False,
            'gold_found': 0
        })
        
         # 🔥 ВАЖНО: АКТИВИРУЕМ БЕСКОНЕЧКУ
        if self.infinite_mode.enabled:
            self.infinite_mode.is_active = True
            print("🌀 АКТИВИРОВАНА БЕСКОНЕЧКА! (is_active = True)")

        start_time = time.time()  # 🔥 ЗАПОМИНАЕМ ВРЕМЯ НАЧАЛА
        check_counter = 0
        arrow_clicked = False
        frame_found = False
        frame_search_attempted = False
        last_color_check_time = 0
        color_check_interval = 5
        last_infinite_check_time = start_time
        gold_found_count = 0
        
        # 🔥 ИЗМЕНЯЕМ УСЛОВИЕ ЦИКЛА - используем вечный цикл с ручной проверкой таймаута
        while True:
            # 1. Проверяем таймаут с учетом паузы
            should_continue, elapsed = pause_handler.check_pause_with_real_timeout(
                "Мониторинг AFK лобби",
                self.lobby_timeout,
                start_time
            )
            
            if not should_continue:
                if elapsed >= self.lobby_timeout:
                    print("⏰ Таймаут лобби истек")
                    return "RESTART", "Лобби AFK больше таймаута"
                else:
                    return "RESTART", "Пауза/перезапуск"
            
            check_counter += 1
            current_time = time.time()
            
            # 🔥 2. ПРОВЕРКА БЕСКОНЕЧКИ (возвращаем обратно)
            if (self.infinite_mode.enabled and 
                self.infinite_mode.is_active and
                current_time - last_infinite_check_time >= 10):  # Каждые 10 секунд
                
                last_infinite_check_time = current_time
                
                # 🔥 ВЫВОДИМ СТАТУС БЕСКОНЕЧКИ
                print(f"\n🌀 ПРОВЕРКА БЕСКОНЕЧКИ...")
                
                # 🔥 ВЫПОЛНЯЕМ ПОПЫТКУ ВХОДА В БЕСКОНЕЧКУ
                attempt_result = self.infinite_mode.check_and_attempt()
                
                if attempt_result is not None:
                    if attempt_result == "ENTRY_SUCCESS":
                        print("🎉 БЕСКОНЕЧКА: Успешный вход!")
                    elif attempt_result == "EXIT_SUCCESS":
                        print("🚪 БЕСКОНЕЧКА: Успешный выход!")
            
            # 🔥 ВСЯ ОСТАЛЬНАЯ ЛОГИКА ОСТАЕТСЯ БЕЗ ИЗМЕНЕНИЙ
            check_counter += 1
            current_time = time.time()
            
            # ЭТАП 1: ПОИСК СТРЕЛКИ В ТЕЧЕНИЕ 7 МИНУТ
            if not arrow_clicked and elapsed < self.arrow_delay:
                print(f"\n🔍 ПОИСК СТРЕЛКИ '>'... ({int(elapsed)}/{self.arrow_delay} сек)")
                
                arrow_found = self.avatar_monitor.find_greater_than_symbol_fast()
                
                if arrow_found:
                    print("🎯 Стрелка '>' найдена! Кликаем и убираем мышь...")
                    click_success = self.avatar_monitor.click_arrow()
                    
                    if click_success:
                        print("✅ Стрелка успешно нажата! Мышь убрана. Ищем рамку...")
                        arrow_clicked = True
                        
                        # 🔥 ПОСЛЕ НАЖАТИЯ СТРЕЛКИ ИЩЕМ РАМКУ РЯДОМ
                        print("\n🎯 ИЩЕМ РАМКУ АВАТАРКИ РЯДОМ СО СТРЕЛКОЙ...")
                        time.sleep(1)
                        
                        frame_found = self.avatar_monitor.find_avatar_frame_near_arrow()
                        frame_search_attempted = True
                        
                        if frame_found:
                            frame_x, frame_y = self.avatar_monitor.avatar_frame_position
                            arrow_x, arrow_y = self.avatar_monitor.arrow_position
                            distance_x = abs(frame_x - arrow_x)
                            distance_y = abs(frame_y - arrow_y)
                            print(f"✅ Рамка найдена! Расстояние от стрелки: X:{distance_x}px, Y:{distance_y}px")
                            
                            print("🎨 Первоначальная проверка цвета рамки...")
                            frame_result = self.avatar_monitor.check_frame_color_with_info()
                            print(f"🎯 Начальный цвет: {frame_result['color_info']}")
                        else:
                            print("❌ Рамка аватарки не найдена рядом со стрелкой.")
                    else:
                        print("❌ Не удалось кликнуть по стрелке")
                else:
                    print("❌ Стрелка не найдена в этой проверке")
            
            # 🔥 ЭТАП 2: ПОСЛЕ 7 МИНУТ
            # 🔥 4. ЭТАП 2: ПОСЛЕ 7 МИНУТ (реальных, без паузы)
            elif not arrow_clicked and elapsed >= self.arrow_delay:
                print(f"\n⏰ {self.arrow_delay//60} МИНУТ ПРОШЛО - ОТКЛЮЧАЕМ ПОИСК СТРЕЛКИ")
                arrow_clicked = True
                
                if not frame_search_attempted:
                    frame_found = self.avatar_monitor.find_avatar_frame()
                    frame_search_attempted = True
            
            # 🔥 5. ЭТАП 3: ПРОВЕРКА ЦВЕТА РАМКИ
            if frame_found and current_time - last_color_check_time >= color_check_interval:
                print("\n🎯 ПРОВЕРКА ЦВЕТА РАМКИ...")
                frame_result = self.avatar_monitor.check_frame_color_with_info()
                
                if frame_result['death_detected']:
                    print(f"🎉 СМЕРТЬ ХОСТА ОБНАРУЖЕНА!")
                    return "RESTART", "Смерть хоста по цвету рамки"
                
                last_color_check_time = current_time

            # 🔥 ЭТАП 4: ПРОВЕРКА ЧАТА НА 9999999
            if check_counter % 3 == 0:
                print(f"\n💰 ПРОВЕРКА ЧАТА #{check_counter//3} НА 9999999...")
                
                if self.press_enter():
                    gold_found = self.check_gold_text_fast()
                    
                    if gold_found:
                        print("🎯 9999999 ОБНАРУЖЕНЫ В ЧАТЕ!")
                        gold_found_count += 1
                        
                        # 🔥 ЗАПИСЫВАЕМ СТАТИСТИКУ 9999999
                        from statistics import stats
                        stats.record_host_death('gold_text', 
                            f"9999999 найдены в чате через {time.time() - start_time:.1f} сек, проверка #{check_counter//3}")
                        
                        return "RESTART", "9999999 найдены в чате"
                    else:
                        print("✅ 9999999 не найдены")
                    self.close_chat()
            
            # 🔥 3. ПРОВЕРКА ТРИГГЕРОВ БЕСКОНЕЧКИ ДЛЯ ПИТОМЦЕВ
            if self.infinite_mode.enabled and self.infinite_mode.is_active:
                # 🔥 ПОЛУЧАЕМ АКТУАЛЬНОЕ КОЛИЧЕСТВО ЦИКЛОВ
                infinite_stats = self.infinite_mode.get_stats_for_telegram()
                infinite_cycles = infinite_stats.get('total_cycles', 0)
                
                # 🔥 ДОБАВЛЯЕМ ОТЛАДОЧНУЮ ИНФОРМАЦИЮ
                if infinite_cycles > 0 and int(current_time) % 30 == 0:  # Каждые 30 секунд
                    print(f"📊 ОТЛАДКА: Циклы бесконечки = {infinite_cycles}")
                
                # Проверяем триггеры каждые 10 секунд
                if int(elapsed) % 10 == 0:
                    
                    # 🔥 ПРОВЕРЯЕМ И ВЫПОЛНЯЕМ ТРИГГЕРЫ
                    if infinite_cycles > 0 and hasattr(self, 'pet_manager'):
                        print(f"🔍 Проверка триггеров при {infinite_cycles} циклах...")
                        triggered_pets = self.pet_manager.check_infinite_triggers(infinite_cycles)
                        
                        if triggered_pets:
                            for triggered in triggered_pets:
                                pet_id = triggered['pet_id']
                                pet_name = triggered['pet_name']
                                trigger_cycles = triggered['trigger_cycles']
                                
                                print(f"🎯 Сработал триггер! {pet_name} при {trigger_cycles} циклах")
                                
                                # Выполняем переключение
                                success, message = self.pet_manager.execute_triggered_switch(
                                    pet_id, infinite_cycles, trigger_cycles
                                )
                                
                                if success:
                                    # Записываем в статистику с флагом деактивации
                                    from statistics import stats
                                    stats.record_pet_switch_by_trigger(
                                        pet_id, pet_name, trigger_cycles, infinite_cycles, trigger_deactivated=True
                                    )
                        
                        self.check_infinite_triggers(infinite_cycles)

            # 🔥 СТАТУС КАЖДЫЕ 30 СЕКУНД
            if int(elapsed) % 30 == 0:
                remaining = self.lobby_timeout - elapsed
                
                status_msg = f"\n⏱ В лобби: {int(elapsed)}сек | До перезапуска: {int(remaining)}сек"
                
                if not arrow_clicked and elapsed < self.arrow_delay:
                    remaining_arrow = self.arrow_delay - elapsed
                    status_msg += f" | 🔍 Поиск стрелки: {int(remaining_arrow)}сек"
                elif arrow_clicked:
                    status_msg += " | ✅ Стрелка нажата"
                
                if frame_found:
                    status_msg += " | 🎯 Рамка: отслеживается"
                
                # 🔥 ДОБАВЛЯЕМ СТАТУС БЕСКОНЕЧКИ
                if self.infinite_mode.enabled and self.infinite_mode.is_active:
                    # Получаем текущее количество циклов из деталей операции
                    #infinite_cycles = pause_handler.operation_details.get('infinite_cycles', 0)
                    
                    #self.check_infinite_triggers(infinite_cycles)

                    infinite_stats = self.infinite_mode.get_stats_for_telegram()
                    status_msg += f" | 🌀 Бесконечка:"
                    status_msg += f" ВХОДЫ={infinite_stats['total_entries']}"
                    status_msg += f" ВЫХОДЫ={infinite_stats['total_exits']}"
                    status_msg += f" ЦИКЛЫ={infinite_stats['total_cycles']}"
                    
                    # 🔥 ДОБАВЛЯЕМ ИНФОРМАЦИЮ О СМЕРТЯХ ГЕРОЯ
                    if infinite_stats.get('hero_dead', False):
                        status_msg += f" | 💀 ГЕРОЙ МЕРТВ (смертей: {infinite_stats.get('hero_death_count', 0)})"
                    if infinite_stats.get('hero_death_total', 0) > 0:
                        status_msg += f" | 💀 Всего смертей героя: {infinite_stats.get('hero_death_total', 0)}"
                
                print(status_msg)
                
                # 🔥 ОБНОВЛЯЕМ ДЕТАЛИ ОПЕРАЦИИ ДЛЯ ТЕЛЕГРАМ
                infinite_stats = self.infinite_mode.get_stats_for_telegram() if self.infinite_mode.enabled else {}
                
                pause_handler.update_operation_details({
                    'elapsed_seconds': int(elapsed),
                    'remaining_seconds': int(remaining),
                    'arrow_found': arrow_clicked,
                    'frame_found': frame_found,
                    'gold_found': gold_found_count,
                    'infinite_enabled': self.infinite_mode.enabled,
                    'infinite_is_active': self.infinite_mode.is_active,
                    'infinite_entries': infinite_stats.get('total_entries', 0),
                    'infinite_exits': infinite_stats.get('total_exits', 0),
                    'infinite_cycles': infinite_stats.get('total_cycles', 0),
                    'infinite_total_cycles': infinite_stats.get('total_cycles', 0),
                    'hero_dead': infinite_stats.get('hero_dead', False),
                    'hero_death_count': infinite_stats.get('hero_death_total', 0),
                    'hero_death_streak': infinite_stats.get('hero_death_count', 0)
                })
            
            time.sleep(1)

    # Методы для обратной совместимости
    def monitor_gold_text(self, timeout=GOLD_MONITOR_TIMEOUT):
        return self.monitor_after_accept(timeout)
    
    def monitor_gold_and_champion(self, timeout=GOLD_MONITOR_TIMEOUT):
        return self.monitor_after_accept(timeout)