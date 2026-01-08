# infinite_mode.py - добавим отслеживание смертей героя в бесконечке

import json
import os
import pyautogui
import time
import keyboard
from config import (
    INFINITE_MODE_ENABLED, 
    INFINITE_ATTEMPT_INTERVAL,
    INFINITE_KEY_PRESS,
    INFINITE_CLICK_X,
    INFINITE_CLICK_Y,
    INFINITE_BUTTON_COLOR,
    INFINITE_COLOR_TOLERANCE,
    INFINITE_SEARCH_REGION,
    INFINITE_AFTER_PRESS_DELAY,
    INFINITE_AFTER_KEY,
    INFINITE_STATS_FILE
)
from pause_handler import pause_handler
from statistics import stats

class InfiniteMode:
    def __init__(self, logger):
        self.logger = logger
        self.enabled = INFINITE_MODE_ENABLED
        self.is_active = False
        self.current_attempt_count = 0
        self.successful_entries = 0
        self.last_was_entry = None  # True если последнее было входом, False если выходом
        
        # 🔥 НОВЫЕ ПЕРЕМЕННЫЕ ДЛЯ ОТСЛЕЖИВАНИЯ СМЕРТИ ГЕРОЯ
        self.consecutive_found_entries = 0  # Подряд найденные кнопки входа (при смерти героя)
        self.hero_dead = False  # Флаг смерти героя
        self.hero_death_count = 0  # Счетчик смертей героя
        self.current_round_started = False  # Флаг начала нового раунда
        self.hero_death_stats = {  # Статистика смертей героя
            'total_deaths': 0,
            'deaths_detected': 0,
            'last_death_time': None,
            'current_death_streak': 0
        }       
        
        self.total_infinite_stats = self._load_stats()

        print(f"🌀 Режим бесконечки: {'ВКЛЮЧЕН' if self.enabled else 'ВЫКЛЮЧЕН'}")
    
    def _load_stats(self):  # 🔥 ИЗМЕНЕНИЕ: Переименовали в _load_stats и определили ДО вызова
        """Загрузка статистики из файла"""
        try:
            if os.path.exists(INFINITE_STATS_FILE):
                with open(INFINITE_STATS_FILE, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                    print(f"✅ Статистика бесконечки загружена из {INFINITE_STATS_FILE}")
                    return stats
        except Exception as e:
            print(f"⚠️ Ошибка загрузки статистики бесконечки: {e}")
        
        # Возвращаем статистику по умолчанию
        return {
            'total_entries': 0,
            'total_exits': 0,
            'total_cycles': 0,
            'hero_death_count': 0,
            'last_entry_time': None,
            'last_exit_time': None
        }
    
    def _save_stats(self):  # 🔥 ИЗМЕНЕНИЕ: Переименовали в _save_stats
        """Сохранение статистики в файл"""
        try:
            # Создаем папку если не существует
            os.makedirs(os.path.dirname(INFINITE_STATS_FILE), exist_ok=True)
            
            with open(INFINITE_STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.total_infinite_stats, f, indent=2, ensure_ascii=False)
            
            # print(f"✅ Статистика бесконечки сохранена в {INFINITE_STATS_FILE}")  # Можно раскомментировать для отладки
            return True
        except Exception as e:
            print(f"⚠️ Ошибка сохранения статистики бесконечки: {e}")
            return False

    def get_stats_for_telegram(self):
        """Получение статистики для Telegram"""
        return {
            'enabled': self.enabled,
            'is_active': self.is_active,
            'attempt_count': self.current_attempt_count,
            'successful_entries': self.successful_entries,
            'last_was_entry': self.last_was_entry,
            'hero_dead': self.hero_dead,
            'hero_death_count': self.hero_death_stats['total_deaths'],
            'consecutive_found_entries': self.consecutive_found_entries,
            'total_entries': self.total_infinite_stats['total_entries'],
            'total_exits': self.total_infinite_stats['total_exits'],
            'total_cycles': self.total_infinite_stats['total_cycles'],
            'hero_death_total': self.total_infinite_stats.get('hero_death_count', 0),  # 🔥 ДОБАВЛЕНО
            'last_entry_time': self.total_infinite_stats['last_entry_time'],
            'last_exit_time': self.total_infinite_stats['last_exit_time']
        }

    def calculate_search_region(self):
        """Расчет области поиска на основе процентов"""
        screen_width, screen_height = pyautogui.size()
        
        top_offset = int(screen_height * (INFINITE_SEARCH_REGION["top_percent"] / 100))
        bottom_offset = int(screen_height * (INFINITE_SEARCH_REGION["bottom_percent"] / 100))
        left_offset = int(screen_width * (INFINITE_SEARCH_REGION["left_percent"] / 100))
        right_offset = int(screen_width * (INFINITE_SEARCH_REGION["right_percent"] / 100))
        
        region = (
            left_offset,
            top_offset,
            screen_width - left_offset - right_offset,
            screen_height - top_offset - bottom_offset
        )
        
        return region
    
    def find_button_by_color(self):
        """Поиск кнопки по цвету"""
        region = self.calculate_search_region()
        
        try:
            screenshot = pyautogui.screenshot(region=region)
            rgb_screenshot = screenshot.convert('RGB')
            pixels = rgb_screenshot.load()
            width, height = rgb_screenshot.size
            
            target_color = INFINITE_BUTTON_COLOR
            tolerance = INFINITE_COLOR_TOLERANCE
            
            # Поиск пикселей с похожим цветом
            found_pixels = []
            
            for y in range(height):
                for x in range(width):
                    current_color = pixels[x, y]
                    if self.color_match(current_color, target_color, tolerance):
                        found_pixels.append((x, y))
            
            if found_pixels:
                # Находим центр группы пикселей
                avg_x = sum(p[0] for p in found_pixels) / len(found_pixels)
                avg_y = sum(p[1] for p in found_pixels) / len(found_pixels)
                
                # Конвертируем в абсолютные координаты
                abs_x = region[0] + int(avg_x)
                abs_y = region[1] + int(avg_y)
                
                return (abs_x, abs_y, len(found_pixels))
            else:
                return None
                
        except Exception as e:
            print(f"⚠️ Ошибка при поиске кнопки бесконечки: {e}")
            return None
    
    def color_match(self, color1, color2, tolerance):
        """Проверка соответствия цвета с допуском"""
        return (abs(color1[0] - color2[0]) <= tolerance and
                abs(color1[1] - color2[1]) <= tolerance and
                abs(color1[2] - color2[2]) <= tolerance)
    
    def check_and_attempt(self):
        """
        Проверяет и выполняет попытку входа в бесконечку
        """
        try:
            return self.perform_cycle()
        except Exception as e:
            print(f"⚠️ Ошибка при проверке бесконечки: {e}")
            return None

    def perform_cycle(self):
        """
        УЛУЧШЕННЫЙ метод: сначала клик по координатам, потом проверка
        С ОТСЛЕЖИВАНИЕМ СМЕРТИ ГЕРОЯ
        """
        try:
            print(f"\n🌀 НАЧАЛО ЦИКЛА БЕСКОНЕЧКИ (попытка #{self.current_attempt_count + 1})")
            print(f"   Клавиша: '{INFINITE_KEY_PRESS}', Жесткие координаты: ({INFINITE_CLICK_X}, {INFINITE_CLICK_Y})")
            
            # 🔥 УВЕЛИЧИВАЕМ СЧЕТЧИК ПОПЫТОК
            self.current_attempt_count += 1
            
            # 🔥 ПРОВЕРКА: ЕСЛИ ГЕРОЙ УМЕР, ОЖИДАЕМ НОВЫЙ РАУНД
            if self.hero_dead:
                print(f"💀 ГЕРОЙ УМЕР! Ожидаем новый раунд... (пропущено попыток: {self.consecutive_found_entries})")
                
                # Проверяем кнопку - если не найдена, значит начался новый раунд
                button_result = self.find_button_by_color()
                if button_result is None:
                    print("🎉 НОВЫЙ РАУНД НАЧАЛСЯ! Герой воскрес, продолжаем нормальную работу.")
                    self.hero_dead = False
                    self.consecutive_found_entries = 0
                    self.current_round_started = True
                    
                    # 🔥 ОБНОВЛЯЕМ СТАТИСТИКУ ДЛЯ ТЕЛЕГРАМ
                    pause_handler.update_operation_details({
                        'hero_dead': False,
                        'hero_death_streak': self.hero_death_stats['current_death_streak']
                    })
                else:
                    # Герой все еще мертв, пропускаем попытку
                    print(f"💀 Герой все еще мертв, кнопка найдена. Пропускаем попытку #{self.current_attempt_count}")
                    return "HERO_DEAD_SKIP"
            
            # 🔥 УЛУЧШЕННОЕ ОПРЕДЕЛЕНИЕ ВХОДА/ВЫХОДА
            if self.last_was_entry is None:
                # Первый запуск - начинаем с входа
                is_entry_attempt = True
                print("🎯 Первый запуск - начинаем с ВХОДА")
            elif self.last_was_entry == True:
                # Последнее было входом - теперь выход
                is_entry_attempt = False
                print("🚪 Последнее было ВХОДОМ - теперь ВЫХОД")
            else:
                # Последнее было выходом - теперь вход
                is_entry_attempt = True
                print("🎯 Последнее было ВЫХОДОМ - теперь ВХОД")
            
            print(f"📊 Определено как: {'ВХОД' if is_entry_attempt else 'ВЫХОД'}")
            
            # 🔥 ШАГ 1: Всегда нажимаем клавишу перемещения камеры через keyboard
            print(f"⌨️ 1. Нажатие клавиши перемещения камеры: '{INFINITE_KEY_PRESS}'...")
            keyboard.press_and_release(INFINITE_KEY_PRESS)
            time.sleep(0.2)
            
            # 🔥 ШАГ 2: Всегда кликаем по жестко заданным координатам
            print(f"🖱️ 2. Клик по жестким координатам: ({INFINITE_CLICK_X}, {INFINITE_CLICK_Y})...")
            try:
                pyautogui.moveTo(INFINITE_CLICK_X, INFINITE_CLICK_Y, duration=0.2)
                pyautogui.click()
                print(f"✅ Клик по координатам выполнен!")
                time.sleep(0.3)
            except Exception as e:
                print(f"⚠️ Ошибка клика по координатах: {e}")
            
            # 🔥 ШАГ 3: После клика проверяем результат - ищем кнопку по цвету
            print("🔍 3. Проверка результата - поиск кнопки по цвету...")
            button_result = self.find_button_by_color()
            
            if button_result:
                x, y, pixel_count = button_result
                print(f"✅ Кнопка бесконечки найдена после клика! Пикселей: {pixel_count}")
                print(f"📍 Найденные координаты: ({x}, {y}) vs жесткие: ({INFINITE_CLICK_X}, {INFINITE_CLICK_Y})")
                print(f"📊 Тип попытки: {'ВХОД' if is_entry_attempt else 'ВЫХОД'}")
                
                # 🔥 ОБРАБОТКА СМЕРТИ ГЕРОЯ: если это попытка ВХОДА
                if is_entry_attempt:
                    self.consecutive_found_entries += 1
                    print(f"📈 Подряд найденных входов: {self.consecutive_found_entries}")
                    
                    # 🔥 ПРОВЕРКА НА СМЕРТЬ ГЕРОЯ: 6 раз подряд найден вход
                    if self.consecutive_found_entries >= 6 and not self.hero_dead:
                        print("💀 ОБНАРУЖЕНА СМЕРТЬ ГЕРОЯ! 6 раз подряд найден вход в бесконечку.")
                        print("💀 Герой умер и не может зайти на бесконечку.")
                        
                        # Устанавливаем флаг смерти героя
                        self.hero_dead = True
                        self.hero_death_count += 1
                        self.hero_death_stats['total_deaths'] += 1
                        self.hero_death_stats['deaths_detected'] += 1
                        self.hero_death_stats['last_death_time'] = time.time()
                        self.hero_death_stats['current_death_streak'] += 1
                        
                        # Записываем в общую статистику
                        self.total_infinite_stats['hero_death_count'] = self.total_infinite_stats.get('hero_death_count', 0) + 1
                        
                        # 🔥 ОБНОВЛЯЕМ СТАТИСТИКУ ДЛЯ ТЕЛЕГРАМ
                        pause_handler.update_operation_details({
                            'hero_dead': True,
                            'hero_death_count': self.hero_death_stats['total_deaths'],
                            'hero_death_streak': self.hero_death_stats['current_death_streak']
                        })
                        
                        # Логируем смерть героя
                        print(f"📊 СТАТИСТИКА: Герой умер в бесконечке! Всего смертей: {self.hero_death_stats['total_deaths']}")
                        
                        # 🔥 НЕ ЗАПИСЫВАЕМ ЭТОТ ВХОД В СТАТИСТИКУ!
                        # 🔥 НЕ увеличиваем счетчики successful_entries и total_entries
                        
                        # 🔥 НЕ нажимаем D и не выполняем вход
                        print("💀 Пропускаем этот вход - герой мертв!")
                        return "HERO_DEAD"
                
                # 🔥 ШАГ 4: Дополнительный клик по найденной кнопке (если координаты отличаются)
                if abs(x - INFINITE_CLICK_X) > 10 or abs(y - INFINITE_CLICK_Y) > 10:
                    print(f"🖱️ 4. Дополнительный клик по найденной кнопке...")
                    pyautogui.moveTo(x, y, duration=0.1)
                    pyautogui.click()
                    print(f"✅ Дополнительный клик выполнен!")
                
                # 🔥 ШАГ 5: ВЫПОЛНЯЕМ ВХОД ИЛИ ВЫХОД (если герой не умер)
                if is_entry_attempt and not self.hero_dead:
                    print("🎯 ВЫПОЛНЯЕМ ВХОД - ожидаю и нажимаю D...")
                    time.sleep(INFINITE_AFTER_PRESS_DELAY)
                    keyboard.press_and_release(INFINITE_AFTER_KEY)
                    print(f"⌨️ Нажата клавиша '{INFINITE_AFTER_KEY}' после входа")
                    
                    # Сбрасываем счетчик подряд найденных входов при успешном входе
                    self.consecutive_found_entries = 0
                    
                    # Запоминаем что это был ВХОД
                    self.last_was_entry = True
                    self.successful_entries += 1
                    self.total_infinite_stats['total_entries'] += 1
                    self.total_infinite_stats['last_entry_time'] = time.time()
                    
                    # 🔥 СОХРАНЯЕМ СТАТИСТИКУ
                    self._save_stats()

                    try:
                        # Получаем текущее значение
                        current_details = pause_handler.operation_details.copy()
                        current_cycles = current_details.get('infinite_cycles', 0)
                        
                        # Увеличиваем счетчик на 1
                        new_cycles = current_cycles + 1
                        
                        # Обновляем статистику
                        pause_handler.update_operation_details({
                            'infinite_cycles': new_cycles,
                            'infinite_last_action': time.strftime("%H:%M:%S"),
                            'infinite_entries': self.total_infinite_stats['total_entries'],
                            'infinite_exits': self.total_infinite_stats['total_exits']
                        })
                        
                        print(f"📊 Циклов бесконечки: {new_cycles}")
                        print(f"📊 Входов: {self.total_infinite_stats['total_entries']}, Выходов: {self.total_infinite_stats['total_exits']}")
                        
                    except Exception as stats_error:
                        print(f"⚠️ Не удалось обновить статистику: {stats_error}")
                    
                    return "ENTRY_SUCCESS"
                elif not is_entry_attempt:
                    # Это ВЫХОД - НЕ нажимаем D
                    print("🚪 ВЫПОЛНЯЕМ ВЫХОД - нажатие D не требуется")
                    
                    # Сбрасываем счетчик подряд найденных входов при выходе
                    self.consecutive_found_entries = 0
                    
                    # Запоминаем что это был ВЫХОД
                    self.last_was_entry = False
                    self.total_infinite_stats['total_exits'] += 1
                    self.total_infinite_stats['last_exit_time'] = time.time()
                    
                    # 🔥 КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Каждый выход - это завершение цикла
                    # (предполагаем, что перед каждым выходом был вход)
                    if self.total_infinite_stats['total_entries'] >= self.total_infinite_stats['total_exits']:
                        self.total_infinite_stats['total_cycles'] = self.total_infinite_stats['total_exits']
                    
                    # 🔥 СОХРАНЯЕМ СТАТИСТИКУ
                    self._save_stats()

                    print(f"📊 УСПЕШНЫЙ ВЫХОД! Всего выходов: {self.total_infinite_stats['total_exits']}")
                    print(f"🎉 ЦИКЛОВ БЕСКОНЕЧКИ: {self.total_infinite_stats['total_cycles']}")
                    
                    try:
                        # 🔥 ОБНОВЛЯЕМ СТАТИСТИКУ ДЛЯ ТЕЛЕГРАМ
                        pause_handler.update_operation_details({
                            'infinite_entries': self.total_infinite_stats['total_entries'],
                            'infinite_exits': self.total_infinite_stats['total_exits'],
                            'infinite_cycles': self.total_infinite_stats['total_cycles'],
                            'infinite_last_action': time.strftime("%H:%M:%S"),
                            'infinite_last_exit': time.strftime("%H:%M:%S")
                        })
                        
                        # 🔥 ОБНОВЛЯЕМ ОБЩУЮ СТАТИСТИКУ
                        from statistics import stats
                        # Обновляем счетчик циклов в текущей сессии
                        stats.current_session_data['infinite_cycles'] = self.total_infinite_stats['total_cycles']
                        
                    except Exception as stats_error:
                        print(f"⚠️ Не удалось обновить статистику: {stats_error}")
                    
                    return "EXIT_SUCCESS"
            else:
                print(f"❌ Кнопка бесконечки не найдена после клика (попытка #{self.current_attempt_count})")
                print(f"ℹ️ Возможно кнопка не появилась или изменился цвет")
                
                # Сбрасываем счетчик подряд найденных входов если кнопка не найдена
                self.consecutive_found_entries = 0
                
                return "BUTTON_NOT_FOUND"
            
            if self.consecutive_found_entries >= 6 and not self.hero_dead:
                print("💀 ОБНАРУЖЕНА СМЕРТЬ ГЕРОЯ! 6 раз подряд найден вход в бесконечку.")
                print("💀 Герой умер и не может зайти на бесконечку.")
                
                # Устанавливаем флаг смерти героя
                self.hero_dead = True
                self.hero_death_count += 1
                self.hero_death_stats['total_deaths'] += 1
                self.hero_death_stats['deaths_detected'] += 1
                self.hero_death_stats['last_death_time'] = time.time()
                self.hero_death_stats['current_death_streak'] += 1
                
                # Записываем в общую статистику
                self.total_infinite_stats['hero_death_count'] = self.total_infinite_stats.get('hero_death_count', 0) + 1
                self._save_stats()

                # 🔥 ЗАПИСЫВАЕМ В СТАТИСТИКУ
                try:
                    from statistics import stats
                    stats.record_hero_death_in_infinite(f"Герой умер в бесконечке, 6 подряд входов. Всего смертей героя: {self.hero_death_stats['total_deaths']}")
                except Exception as e:
                    print(f"⚠️ Ошибка записи статистики смерти героя: {e}")
                
                # 🔥 ОБНОВЛЯЕМ СТАТИСТИКУ ДЛЯ ТЕЛЕГРАМ
                pause_handler.update_operation_details({
                    'hero_dead': True,
                    'hero_death_count': self.hero_death_stats['total_deaths'],
                    'hero_death_streak': self.hero_death_stats['current_death_streak']
                })
                
                # Логируем смерть героя
                print(f"📊 СТАТИСТИКА: Герой умер в бесконечке! Всего смертей: {self.hero_death_stats['total_deaths']}")
                
                # 🔥 НЕ ЗАПИСЫВАЕМ ЭТОТ ВХОД В СТАТИСТИКУ!
                # 🔥 НЕ увеличиваем счетчики successful_entries и total_entries
                
                # 🔥 НЕ нажимаем D и не выполняем вход
                print("💀 Пропускаем этот вход - герой мертв!")
                return "HERO_DEAD"

        except Exception as e:
            print(f"⚠️ Ошибка при выполнении цикла бесконечки: {e}")
            import traceback
            traceback.print_exc()
            return "ERROR"
    
    def reset_session_stats(self):
        """Сброс сессионной статистики (но сохранение общей в файле)"""
        self.current_attempt_count = 0
        self.successful_entries = 0
        self.last_was_entry = None
        self.consecutive_found_entries = 0
        self.hero_dead = False
        self.current_round_started = False
        
        # Но НЕ сбрасываем:
        # - self.total_infinite_stats (она уже сохранена в файле)
        # - self.hero_death_stats['total_deaths'] (она в total_infinite_stats)
        # - self.hero_death_stats['current_death_streak'] (оставляем для текущей сессии)
        
        print("🔄 Сессионная статистика бесконечки сброшена (общая статистика сохранена)")

    def reset_for_new_round(self):
        """
        Сброс при начале нового раунда (после смерти героя)
        """
        print("🔄 Сброс бесконечки для нового раунда...")
        self.hero_dead = False
        self.consecutive_found_entries = 0
        self.current_round_started = True
        
        # 🔥 ОБНОВЛЯЕМ СТАТИСТИКУ ДЛЯ ТЕЛЕГРАМ
        pause_handler.update_operation_details({
            'hero_dead': False,
            'hero_death_streak': self.hero_death_stats['current_death_streak']
        })