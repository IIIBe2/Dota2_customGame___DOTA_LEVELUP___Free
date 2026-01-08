# lobby_navigator.py
import time
import pyautogui
import pytesseract
import sys
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from config import (ACCEPT_SINGLE_ATTEMPT_TIMEOUT, ENABLE_DEBUG_SCREENSHOTS, INVITE_MODE_ACCEPT_TIMEOUT, INVITE_MODE_SECOND_ACCEPT_TIMEOUT, OK_SINGLE_ATTEMPT_TIMEOUT, OK_TIMEOUT, PASS_LOBBY, ACCEPT_TIMEOUT, REFRESH_TIMEOUT, REFRESH_INTERVAL, 
                   SEARCH_INTERVAL, CLICK_INTERVAL)
from pause_handler import pause_handler

# 🔥 ПРАВИЛЬНЫЙ ИМПОРТ
from AFK_lobby import AFKLobbyMonitor  # Убедитесь что имя класса совпадает
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    print("⚠️ pyperclip не установлен, русские символы могут не вводиться правильно")

class LobbyNavigator:
    def __init__(self, text_detector, logger, pet_manager=None):
        self.detector = text_detector
        self.logger = logger
        
        self.afk_monitor = AFKLobbyMonitor(logger)  # Теперь должно работать
        self.refresh_position = None
        self.refresh_confidence = 0
        self.dotaland_position = None
        self.dotaland_confidence = 0
        self.dotaland_miss_count = 0
        self.dotaland_check_counter = 0

    def safe_password_input(self, password):
        """
        СУПЕРУМНЫЙ ввод пароля с авто-переключением раскладки
        Работает для ЛЮБЫХ паролей: ячс228, drfgyerывп, ячсdrfgyer228ывп и т.д.
        """
        print(f"⌨️ СУПЕРУМНЫЙ ВВОД ПАРОЛЯ: {'*' * len(password)}")
        print(f"   Пример: '{password[:3]}...{password[-3:] if len(password) > 6 else ''}'")
        
        try:
            # 🔥 ИСПОЛЬЗУЕМ УМНЫЙ ВВОДЧИК
            from keyboard_input import SmartKeyboardInput
            
            # Даем время для фокуса на поле ввода
            time.sleep(0.4)
            
            # Вводим пароль УМНО с восстановлением раскладки
            success = SmartKeyboardInput.type_password_smart(
                password, 
                interval=0.12,  # Немного медленнее для надежности
                restore_layout=True  # Восстанавливаем исходную раскладку
            )
            
            if success:
                print("✅ Пароль введен СУПЕРУМНО с авто-переключением раскладки!")
                time.sleep(CLICK_INTERVAL)
                return True
            else:
                # Запасной вариант: простой ввод
                print("⚠️ Умный ввод не сработал, пробуем простой...")
                return self.simple_password_input(password)
                
        except Exception as e:
            print(f"⚠️ Ошибка суперумного ввода: {e}")
            return self.simple_password_input(password)

    def simple_password_input(self, password):
        """Простой запасной метод ввода"""
        try:
            import pyautogui
            print(f"⌨️ Простой ввод пароля...")
            pyautogui.write(password, interval=0.15)
            time.sleep(CLICK_INTERVAL)
            return True
        except Exception as e:
            print(f"❌ Ошибка простого ввода: {e}")
            return False

    def find_accept_button_accurate(self, timeout=ACCEPT_SINGLE_ATTEMPT_TIMEOUT):  # Используем конфиг
        """
        ТОЧНЫЙ поиск кнопки ACCEPT без проверки размера
        """
        print(f"🎯 ОДНА ПОПЫТКА поиска ACCEPT ({timeout} сек)")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < timeout:
            attempt += 1
            print(f"  🔍 Попытка {attempt} распознавания ACCEPT...")
            
            try:
                screenshot = pyautogui.screenshot()
                
                # Обработка для ACCEPT (белый текст на зеленом фоне)
                if screenshot.mode != 'L':
                    processed = screenshot.convert('L')
                else:
                    processed = screenshot.copy()
                
                # Усиление контраста для белого текста
                binary_high = processed.point(lambda x: 255 if x > 200 else 0)
                
                custom_config = r'--oem 3 --psm 6'
                data = pytesseract.image_to_data(
                    binary_high, 
                    output_type=pytesseract.Output.DICT,
                    config=custom_config,
                    lang='eng'
                )
                
                valid_accepts = []
                
                for i in range(len(data['text'])):
                    text = data['text'][i].strip().upper()
                    confidence = int(data['conf'][i])
                    
                    if text == "ACCEPT" and confidence > 50:
                        x = data['left'][i]
                        y = data['top'][i]
                        w = data['width'][i]
                        h = data['height'][i]
                        
                        center_x_btn = x + w // 2
                        center_y_btn = y + h // 2
                        
                        valid_accepts.append({
                            'text': text,
                            'position': (center_x_btn, center_y_btn),
                            'confidence': confidence,
                            'bbox': (x, y, w, h)
                        })
                
                if valid_accepts:
                    best_accept = max(valid_accepts, key=lambda x: x['confidence'])
                    print(f"    ✅ ACCEPT найден за {time.time() - start_time:.1f} сек! Уверенность: {best_accept['confidence']}%")
                    return best_accept
                
                # Если не нашли в этой попытке, ждем немного перед повторным скриншотом
                time.sleep(0.5)
                
            except Exception as e:
                print(f"⚠️ Ошибка при поиске ACCEPT: {e}")
                time.sleep(1)
        
        print(f"❌ ACCEPT не найден за {timeout} сек (одна попытка)")
        return None

    def screenshot(self, *args, **kwargs):
        """
        Временный метод для отладки - покажет где используется self.screenshot
        """
        print("❌ ОШИБКА: Обнаружен вызов self.screenshot()!")
        print("📍 Это должно быть pyautogui.screenshot()")
        print(f"📋 Аргументы: {args}, {kwargs}")
        raise AttributeError("Используйте pyautogui.screenshot() вместо self.screenshot()")

    def find_disconnect_button_fast(self):
        """
        ОПТИМИЗИРОВАННЫЙ поиск кнопок DISCONNECT или LEAVE
        """
        print("🎯 ОПТИМИЗИРОВАННЫЙ ПОИСК DISCONNECT/LEAVE")
        
        try:
            # Область поиска
            screen_width, screen_height = pyautogui.size()
            search_region = (
                int(screen_width * 0.6),
                int(screen_height * 0.7),
                int(screen_width * 0.4),
                int(screen_height * 0.3)
            )
            print(f"📍 Область поиска: {search_region}")
            
            screenshot = pyautogui.screenshot(region=search_region)
            
            # 🔥 ИСПОЛЬЗУЕМ ТОЛЬКО РАБОЧИЙ МЕТОД
            if screenshot.mode != 'RGB':
                rgb_screenshot = screenshot.convert('RGB')
            else:
                rgb_screenshot = screenshot
            
            # 🔥 ТОЛЬКО WHITE_MASK МЕТОД И PSM 6
            white_mask = rgb_screenshot.point(lambda x: 255 if x > 200 else 0)
            processed_image = white_mask.convert('L')
            
            # 🔥 ТОЛЬКО РАБОЧИЙ КОНФИГ
            custom_config = r'--oem 3 --psm 6'
            
            print("  🧪 Метод: white_mask (оптимизированный)")
            
            data = pytesseract.image_to_data(
                processed_image, 
                output_type=pytesseract.Output.DICT,
                config=custom_config,
                lang='eng'
            )
            
            for i in range(len(data['text'])):
                text = data['text'][i].strip().upper()
                confidence = int(data['conf'][i])
                
                # 🔥 РАСШИРЕННЫЙ ПОИСК
                if ("DISCONNECT" in text or "LEAVE" in text) and confidence > 25:
                    x = data['left'][i] + search_region[0]
                    y = data['top'][i] + search_region[1]
                    w = data['width'][i]
                    h = data['height'][i]
                    
                    center_x = x + w // 2
                    center_y = y + h // 2
                    
                    # Определяем тип кнопки
                    if "DISCONNECT" in text or "CONNECT" in text:
                        button_type = "DISCONNECT"
                    else:
                        button_type = "LEAVE"
                    
                    print(f"    ✅ {button_type} найден! Уверенность: {confidence}%")
                    print(f"    📍 Позиция: ({center_x}, {center_y})")
                    print(f"    📏 Размер: {w}x{h}")
                    
                    return {
                        'text': text,
                        'position': (center_x, center_y),
                        'confidence': confidence,
                        'button_type': button_type,
                        'bbox': (x, y, w, h)
                    }
            
            print("❌ DISCONNECT/LEAVE не найдены")
            return None
                
        except Exception as e:
            print(f"⚠️ Ошибка при поиске DISCONNECT/LEAVE: {e}")
            return None
        
    def click_disconnect_if_found(self):
        """
        Быстро проверяет и кликает DISCONNECT если найден (только один раз перед FIND)
        """
        print("🔍 Быстрая проверка DISCONNECT перед поиском FIND...")
        disconnect_result = self.find_disconnect_button_fast()
        
        if disconnect_result:
            x, y = disconnect_result['position']
            print(f"🎯 Найден DISCONNECT! Кликаем: ({x}, {y})")
            
            # Сверхбыстрый клик
            try:
                pyautogui.moveTo(x, y, duration=0.1)
                time.sleep(0.05)
                pyautogui.click()
                print("✅ DISCONNECT нажат!")
                time.sleep(1)  # Ждем реакции
                return True
            except Exception as e:
                print(f"❌ Ошибка клика по DISCONNECT: {e}")
                return False
        
        return False


    def find_ok_during_accept_search(self, timeout=5):
        """
        Поиск кнопки OK во время поиска ACCEPT
        """
        print("🎯 ПОИСК КНОПКИ 'OK' ВО ВРЕМЯ ПОИСКА ACCEPT")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < timeout:
            if not pause_handler.check_pause("Поиск OK во время ACCEPT"):
                return None
                
            attempt += 1
            print(f"🔍 Попытка {attempt} поиска OK...")
            
            try:
                # 🔥 УБЕДИТЕСЬ ЧТО ИСПОЛЬЗУЕТСЯ pyautogui.screenshot(), а не self.screenshot
                screenshot = pyautogui.screenshot()  # Правильно!
                
                # Обработка для OK (белый текст на зеленом фоне)
                if screenshot.mode != 'L':
                    processed = screenshot.convert('L')
                else:
                    processed = screenshot.copy()
                
                # Усиление контраста для белого текста
                binary_high = processed.point(lambda x: 255 if x > 200 else 0)
                
                custom_config = r'--oem 3 --psm 6'
                data = pytesseract.image_to_data(
                    binary_high, 
                    output_type=pytesseract.Output.DICT,
                    config=custom_config,
                    lang='eng'
                )
                
                for i in range(len(data['text'])):
                    text = data['text'][i].strip().upper()
                    confidence = int(data['conf'][i])
                    
                    if text == "OK" and confidence > 40:
                        x = data['left'][i]
                        y = data['top'][i]
                        w = data['width'][i]
                        h = data['height'][i]
                        
                        center_x = x + w // 2
                        center_y = y + h // 2
                        
                        print(f"✅ OK найден во время поиска ACCEPT! Уверенность: {confidence}%")
                        
                        return {
                            'text': text,
                            'position': (center_x, center_y),
                            'confidence': confidence,
                            'bbox': (x, y, w, h)
                        }
                
            except Exception as e:
                print(f"⚠️ Ошибка при поиске OK: {e}")
            
            time.sleep(1)
        
        return None

    def move_mouse_away(self):
        """
        Надежно убирает указатель мыши в безопасное место
        """
        try:
            screen_width, screen_height = pyautogui.size()
            # Перемещаем мышь в левый верхний угол (минимальные координаты)
            pyautogui.moveTo(10, 10, duration=0.1)
            time.sleep(0.1)
            # Дополнительно перемещаем для надежности
            pyautogui.moveTo(5, 5, duration=0.1)
            return True
        except Exception as e:
            print(f"⚠️ Не удалось переместить мышь: {e}")
            return False

    def smart_preprocess_for_accept_button(self, image):
        """
        Специальная обработка для кнопки ACCEPT с белым текстом на зеленом фоне
        """
        if image.mode != 'L':
            gray = image.convert('L')
        else:
            gray = image.copy()
        
        binary_high = gray.point(lambda x: 255 if x > 200 else 0)
        
        return {
            'binary_high': binary_high
        }

    

    def handle_ok_during_accept_search(self):
        """
        Обработка ситуации когда найден OK во время поиска ACCEPT
        """
        print("🔄 ОБРАБОТКА: Найден OK вместо ACCEPT")
        
        # Нажимаем OK
        ok_result = self.find_ok_during_accept_search(timeout=5)
        if ok_result:
            x, y = ok_result['position']
            print(f"🎯 Нажимаем OK: ({x}, {y})")
            
            if self.detector.reliable_click(x, y):
                print("✅ OK нажат! Обновляем список...")
                time.sleep(CLICK_INTERVAL)
                
                # Нажимаем REFRESH
                print("🔄 Нажимаем REFRESH после OK...")
                refresh_success = self.guaranteed_click_refresh()
                
                if refresh_success:
                    print("✅ REFRESH нажат! Проверяем DOTALAND...")
                    time.sleep(2)
                    
                    # Проверяем наличие DOTALAND
                    dotaland_result = self.find_dotaland_single_attempt()
                    if dotaland_result:
                        print("✅ DOTALAND доступен! Продолжаем цикл...")
                        return "CONTINUE"
                    else:
                        print("❌ DOTALAND не найден после OK + REFRESH")
                        return "RESTART"
                else:
                    print("❌ Не удалось нажать REFRESH после OK")
                    return "RESTART"
            else:
                print("❌ Не удалось нажать OK")
                return "RESTART"
        else:
            print("❌ OK не найден для нажатия")
            return "RESTART"

    def find_and_click_accept_button_fast(self, timeout=ACCEPT_TIMEOUT):
        """
        Улучшенный поиск и клик по кнопке ACCEPT с обработкой OK
        """
        print(f"🎯 БЫСТРЫЙ ПОИСК КНОПКИ ACCEPT ({timeout} СЕКУНД)")
        
        start_time = time.time()
        attempt = 0
        
        while True:
            # Проверка паузы с учетом времени на паузе
            should_continue, elapsed = pause_handler.check_pause_with_real_timeout(
                "Поиск ACCEPT",
                timeout,
                start_time
            )
            
            if not should_continue:
                if elapsed >= timeout:
                    print("❌ Кнопка ACCEPT не найдена за отведенное время")
                    return "RESTART"
                else:
                    return "RESTART"  # Прервано пользователем
                    
            attempt += 1
            print(f"\n🔍 ПОПЫТКА {attempt} ПОИСКА ACCEPT")
            print(f"⏱ Прошло времени: {elapsed:.1f}с, Осталось: {timeout - elapsed:.1f}с")
            
            # 🔥 ИЗМЕНЕНИЕ 1: Проверяем наличие OK (ложного OK после DOTALAND)
            ok_result = self.find_ok_during_accept_search(timeout=2)
            if ok_result:
                print("🎯 Обнаружен OK после DOTALAND! Нажимаем и продолжаем поиск ACCEPT...")
                
                x, y = ok_result['position']
                print(f"📍 Позиция OK: ({x}, {y})")
                
                # 🔥 ИЗМЕНЕНИЕ 2: Просто нажимаем OK и продолжаем цикл
                if self.detector.reliable_click(x, y):
                    print("✅ OK нажат! Продолжаем поиск ACCEPT...")
                    time.sleep(CLICK_INTERVAL)
                    continue  # 🔥 ВАЖНО: продолжаем поиск ACCEPT, а не возвращаем RESTART
                else:
                    print("⚠️ Не удалось нажать OK, продолжаем поиск ACCEPT...")
                    continue
            
            # 🔥 ИЗМЕНЕНИЕ 3: Затем ищем ACCEPT
            result = self.find_accept_button_accurate(timeout=OK_SINGLE_ATTEMPT_TIMEOUT)
            
            if result:
                x, y = result['position']
                print(f"🎯 Кнопка ACCEPT найдена!")
                print(f"📍 Позиция: ({x}, {y})")
                print(f"🎯 Уверенность: {result['confidence']}%")
                
                if self.detector.reliable_click(x, y):
                    print("✅ Успешный клик по ACCEPT!")
                    time.sleep(CLICK_INTERVAL)
                    return True
                else:
                    print("❌ Не удалось кликнуть по ACCEPT")
            
            time.sleep(SEARCH_INTERVAL)

    def navigate_to_lobby(self):
        """
        Основная функция навигации от ARCADE до лобби
        """
        print("🎯 НАЧИНАЕМ НАВИГАЦИЮ К ЛОББИ")
        print("=" * 60)
        
        steps = [
            ("ARCADE", ["ARCADE"], None),  # Полный экран
            ("LIBRARY", ["LIBRARY"], None),  # Полный экран
            ("LOBBY", ["LOBBY"], "top_half"),  # Только верхняя половина экрана
        ]
        
        for step_name, texts, search_region in steps:
            # Проверка паузы перед каждым шагом
            if not pause_handler.check_pause(f"Навигация: {step_name}"):
                return False
                
            print(f"\n🎯 Шаг: {step_name}")
            
            # Определяем область поиска
            region = None
            if search_region == "top_half":
                screen_width, screen_height = pyautogui.size()
                region = (0, 0, screen_width, screen_height // 3)  # Верхняя половина экрана
                print(f"📍 Поиск только в верхней половине экрана: {region}")
            
            result = self.detector.find_text_on_screen(texts, timeout=30, interval=SEARCH_INTERVAL, region=region)
            if result:
                x, y = result['position']
                self.detector.reliable_click(x, y)
                time.sleep(CLICK_INTERVAL)
            else:
                print(f"❌ Не удалось найти {step_name}")
                return False
        
        print("🎉 Успешно перешли в лобби!")
        return True

    def find_and_enter_lobby(self):
        """
        Упрощенный поиск и вход в лобби - только FIND → пароль → OK
        """
        pause_handler.set_current_operation("Поиск лобби", {'stage': 'Поиск FIND'})
        print("\n" + "=" * 60)
        print("🎯 ПОИСК И ВХОД В ЛОББИ")
        print("=" * 60)
        
        # Проверка паузы
        if not pause_handler.check_pause("Поиск и вход в лобби"):
            return False
        
        # Проверка DISCONNECT перед поиском FIND
        print("🔍 Проверяем DISCONNECT...")
        self.click_disconnect_if_found()
        
        # Поиск FIND
        find_success = self.detector.find_and_click_find_button(timeout=60)
    
        if find_success:
            print("🎉 FIND найден и кликнут! Продолжаем...")
            time.sleep(CLICK_INTERVAL)
            

            # 🔥 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Читаем пароль из config.py ТАК ЖЕ, как в telegram_bot.py
            current_password = self._read_password_from_config()
            
            print(f"⌨️ Вводим пароль: {'*' * len(current_password)}")
            if current_password:
                self.safe_password_input(current_password)
            else:
                print("⚠️ Пароль пустой, пропускаем ввод")
            time.sleep(CLICK_INTERVAL)
            
            ok_success = self.detector.find_and_click_ok_button(timeout=90)
            
            if ok_success:
                print("🎉 OK найден и кликнут! Успешно вошли в лобби!")
                
                # Сразу ищем DOTALAND после входа
                print("🔍 Сразу ищем DOTALAND...")
                time.sleep(2)
                
                dotaland_result = self.find_dotaland_single_attempt()
                if dotaland_result:
                    x, y = dotaland_result['position']
                    print(f"✅ DOTALAND сразу найден! Позиция: ({x}, {y})")
                    # Быстрый клик
                    if self.ultra_fast_click_dotaland(x, y):
                        print("🎯 Сверхбыстрый клик по DOTALAND выполнен!")
                else:
                    print("❌ DOTALAND не найден сразу, будет искаться в основном цикле")
                
                return True
            else:
                print("❌ Не удалось найти OK")
                return False
        else:
            print("❌ Не удалось найти FIND")
            return False

    def _read_password_from_config(self):
        """Читает пароль напрямую из config.py (тот же код, что и в telegram_bot.py)"""
        try:
            with open("config.py", "r", encoding="utf-8") as f:
                content = f.read()
            
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith("PASS_LOBBY ="):
                    # Извлекаем значение
                    parts = line.split('=', 1)
                    if len(parts) > 1:
                        value = parts[1].strip()
                        
                        # Убираем кавычки
                        if value.startswith('"') and value.endswith('"'):
                            return value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            return value[1:-1]
                        else:
                            # Убираем комментарии
                            if '#' in value:
                                value = value.split('#')[0].strip()
                            return value
        except Exception as e:
            print(f"⚠️ Ошибка чтения пароля из config.py: {e}")
        
        return "1"  # значение по умолчанию

    def ultra_fast_click_dotaland(self, x, y):
        """
        Сверхбыстрый клик по DOTALAND без задержек - ТРОЙНОЙ КЛИК
        """
        try:
            print(f"⚡ СВЕРХБЫСТРЫЙ ТРОЙНОЙ КЛИК DOTALAND: ({x}, {y})")
            # Минимальные задержки
            pyautogui.moveTo(x, y, duration=0.05)
            time.sleep(0.02)
            pyautogui.click(clicks=3, interval=0.05)  # 🔥 Меняем на 3 клика
            print("✅ Сверхбыстрый ТРОЙНОЙ клик выполнен!")
            return True
        except Exception as e:
            print(f"❌ Ошибка сверхбыстрого клика: {e}")
            return False

    def find_refresh_button_enhanced(self, region=None, timeout=30):
        """
        Усиленный поиск кнопки REFRESH
        """
        print("🎯 УСИЛЕННЫЙ ПОИСК КНОПКИ 'REFRESH'")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < timeout:
            # Проверка паузы
            if not pause_handler.check_pause("Поиск REFRESH"):
                return None
                
            attempt += 1
            print(f"🔍 Попытка {attempt} поиска REFRESH...")
            
            try:
                # Делаем скриншот
                if region:
                    screenshot = pyautogui.screenshot(region=region)
                else:
                    screenshot = pyautogui.screenshot()
                
                # Пробуем разные области для обхода проблемы с указателем
                screen_width, screen_height = pyautogui.size()
                search_regions = [
                    ("Полный экран", None),
                    ("Правая часть", (screen_width//2, 0, screen_width//2, screen_height)),
                    ("Нижняя часть", (0, screen_height//2, screen_width, screen_height//2)),
                    ("Правый нижний угол", (screen_width - 300, screen_height - 200, 300, 200)),
                    ("Центр нижней части", (screen_width//2 - 150, screen_height - 150, 300, 150)),
                ]
                
                for reg_name, search_region in search_regions:
                    print(f"  📍 Область: {reg_name}")
                    
                    if search_region:
                        region_screenshot = pyautogui.screenshot(region=search_region)
                    else:
                        region_screenshot = screenshot
                    
                    # Базовая обработка
                    if region_screenshot.mode != 'L':
                        processed = region_screenshot.convert('L')
                    else:
                        processed = region_screenshot.copy()
                    
                    # Увеличиваем контраст
                    enhancer = ImageEnhance.Contrast(processed)
                    processed = enhancer.enhance(2.0)
                    
                    custom_config = r'--oem 3 --psm 6'
                    data = pytesseract.image_to_data(
                        processed, 
                        output_type=pytesseract.Output.DICT,
                        config=custom_config,
                        lang='eng'
                    )
                    
                    # Ищем точное совпадение "REFRESH"
                    for i in range(len(data['text'])):
                        text = data['text'][i].strip().upper()
                        confidence = int(data['conf'][i])
                        
                        if text == "REFRESH" and confidence > 40:
                            x = data['left'][i]
                            y = data['top'][i]
                            w = data['width'][i]
                            h = data['height'][i]
                            
                            # Добавляем смещение если поиск в области
                            if search_region:
                                x += search_region[0]
                                y += search_region[1]
                            
                            center_x = x + w // 2
                            center_y = y + h // 2
                            
                            print(f"    ✅ REFRESH найден в области {reg_name}! Уверенность: {confidence}%")
                            
                            return {
                                'text': text,
                                'position': (center_x, center_y),
                                'confidence': confidence,
                                'method': f"enhanced_{reg_name}",
                                'bbox': (x, y, w, h)
                            }
                
                print(f"❌ REFRESH не найден в попытке {attempt}")
                
            except Exception as e:
                print(f"⚠️ Ошибка при поиске REFRESH: {e}")
            
            time.sleep(SEARCH_INTERVAL)
        
        print(f"❌ Кнопка REFRESH не найдена за {timeout} секунд")
        return None

    def guaranteed_click_refresh(self):
        """
        Гарантированный клик по REFRESH - использует запомненную позицию или ищет заново
        """
        if self.refresh_position and self.refresh_confidence > 60:
            # Используем запомненную позицию с высокой уверенностью
            x, y = self.refresh_position
            print(f"🎯 Используем запомненную позицию REFRESH: ({x}, {y})")
            print(f"📊 Уверенность в позиции: {self.refresh_confidence}%")
            
            # Всегда перемещаем мышь на позицию REFRESH перед кликом
            try:
                pyautogui.moveTo(x, y, duration=0.1)
                time.sleep(0.05)
                pyautogui.click()
                print("✅ Успешный клик по запомненному REFRESH!")
                return True
            except Exception as e:
                print(f"❌ Ошибка клика по запомненному REFRESH: {e}")
                # Если клик не удался, сбрасываем позицию и ищем заново
                self.refresh_position = None
                self.refresh_confidence = 0
        
        # Если позиция не запомнена или клик не удался, ищем REFRESH заново
        print("🔍 Поиск REFRESH заново...")
        refresh_result = self.find_refresh_button_enhanced(timeout=5)
        
        if refresh_result:
            self.refresh_position = refresh_result['position']
            self.refresh_confidence = refresh_result['confidence']
            x, y = self.refresh_position
            
            print(f"✅ REFRESH найден! Позиция: ({x}, {y})")
            print(f"📊 Уверенность: {self.refresh_confidence}%")
            
            # Перемещаем мышь на позицию REFRESH и кликаем
            try:
                pyautogui.moveTo(x, y, duration=0.1)
                time.sleep(0.05)
                pyautogui.click()
                print("✅ Успешный клик по REFRESH!")
                return True
            except Exception as e:
                print(f"❌ Ошибка клика по REFRESH: {e}")
                return False
        else:
            print("❌ Не удалось найти REFRESH")
            return False

    def smart_click_dotaland(self):
        """
        Умный клик по DOTALAND - использует запомненную позицию с проверкой
        """
        # Каждые 5 циклов проверяем существование DOTALAND заново
        self.dotaland_check_counter += 1
        need_full_search = (self.dotaland_check_counter % 5 == 0)
        
        if self.dotaland_position and self.dotaland_confidence > 60 and not need_full_search:
            # Используем запомненную позицию - СВЕРХБЫСТРЫЙ КЛИК
            x, y = self.dotaland_position
            print(f"🎯 Используем запомненную позицию DOTALAND: ({x}, {y})")
            print(f"📊 Уверенность: {self.dotaland_confidence}%")
            
            # 🔥 СВЕРХБЫСТРЫЙ клик по запомненной позиции
            try:
                if self.ultra_fast_click_dotaland(x, y):
                    print("✅ Сверхбыстрый клик по запомненному DOTALAND!")
                    
                    # Быстрая проверка результата клика
                    time.sleep(0.5)
                    ok_found = self.find_ok_button_after_dotaland(timeout=2)  # Очень быстрая проверка OK
                    if ok_found:
                        return "OK_FOUND"
                    return "CLICKED"
                else:
                    self.dotaland_miss_count += 1
            except Exception as e:
                print(f"❌ Ошибка клика по запомненному DOTALAND: {e}")
                self.dotaland_miss_count += 1
            
            # Если много промахов, сбрасываем позицию
            if self.dotaland_miss_count >= 3:
                print("🔄 Слишком много промахов, сбрасываем позицию DOTALAND")
                self.dotaland_position = None
                self.dotaland_confidence = 0
                self.dotaland_miss_count = 0
        
        # Если позиция не запомнена или нужен полный поиск, ищем DOTALAND заново
        print("🔍 Полный поиск DOTALAND...")
        dotaland_result = self.find_dotaland_single_attempt()
        
        if dotaland_result:
            # Запоминаем новую позицию
            self.dotaland_position = dotaland_result['position']
            self.dotaland_confidence = dotaland_result['confidence']
            self.dotaland_miss_count = 0
            
            x, y = self.dotaland_position
            print(f"✅ DOTALAND найден! Новая позиция: ({x}, {y})")
            print(f"📊 Уверенность: {self.dotaland_confidence}%")
            
            # СВЕРХБЫСТРЫЙ клик
            try:
                if self.ultra_fast_click_dotaland(x, y):
                    print("🎉 DOTALAND кликнут дважды!")
                    time.sleep(0.5)
                    
                    # Проверяем результат
                    ok_found = self.find_ok_button_after_dotaland(timeout=2)
                    if ok_found:
                        return "OK_FOUND"
                    return "CLICKED"
                else:
                    return "ERROR"
            except Exception as e:
                print(f"❌ Ошибка при клике DOTALAND: {e}")
                return "ERROR"
        else:
            print("❌ DOTALAND не найден")
            return "NOT_FOUND"

    def guaranteed_refresh_dotaland_cycle(self, timeout=REFRESH_TIMEOUT):
        """
        Циклический поиск DOTALAND с учетом времени на паузе
        """
        print("🎯 УСКОРЕННЫЙ ЦИКЛ: УМНЫЙ DOTALAND + REFRESH")
        
        start_time = time.time()  # 🔥 ЗАПОМИНАЕМ ВРЕМЯ НАЧАЛА
        attempt = 0
        
        while True:
            # 🔥 ПРОВЕРКА С УЧЕТОМ ПАУЗЫ
            should_continue, elapsed = pause_handler.check_pause_with_real_timeout(
                "Циклический поиск DOTALAND",
                timeout,
                start_time
            )
            
            if not should_continue:
                if elapsed >= timeout:
                    return False, "Не удалось найти DOTALAND за отведенное время"
                else:
                    return False, "Прервано пользователем"
            
            attempt += 1
            print(f"\n🔄 ЦИКЛ {attempt}: УМНЫЙ ПОИСК DOTALAND + REFRESH")
            print(f"⏱ Прошло: {elapsed:.1f}с, Осталось: {timeout - elapsed:.1f}с")
            
            # 🔥 ВСЯ ОСТАЛЬНАЯ ЛОГИКА ОСТАЕТСЯ БЕЗ ИЗМЕНЕНИЙ
            dotaland_result = self.smart_click_dotaland()
            
            if dotaland_result in ["CLICKED", "OK_FOUND"]:
                print("✅ DOTALAND обработан!")
                
                # Если нашли OK, обрабатываем его
                if dotaland_result == "OK_FOUND":
                    print("🔍 OK уже найден при клике DOTALAND, продолжаем...")
                
                time.sleep(CLICK_INTERVAL)
                
                # ШАГ 2: Ищем OK после DOTALAND (если еще не нашли)
                if dotaland_result != "OK_FOUND":
                    print("🔍 Ищем OK после DOTALAND...")
                    ok_success = self.find_and_click_ok_after_dotaland()
                    
                    if ok_success:
                        print("✅ OK нажат! Ждем ACCEPT...")
                    else:
                        print("ℹ️ OK не найден, продолжаем поиск ACCEPT...")
                
                time.sleep(CLICK_INTERVAL)
                
                # ШАГ 3: Ищем ACCEPT с обработкой OK
                print("🔍 Ищем ACCEPT...")
                accept_success = self.find_and_click_accept_button_fast(timeout=ACCEPT_TIMEOUT)
                
                if accept_success == True:
                    print("🎉 ACCEPT успешно нажат! Все операции завершены!")
                    return True, ""
                elif accept_success == "RESTART":
                    # Определяем причину перезапуска
                    if dotaland_result == "OK_FOUND":
                        restart_reason = "Не успел зайти в лобби (найден OK)"
                    else:
                        restart_reason = "Не удалось найти ACCEPT"
                    return "RESTART", restart_reason
            
            elif dotaland_result == "ERROR":
                print("❌ Ошибка при клике DOTALAND, продолжаем цикл...")
            
            # ШАГ 4: Кликаем REFRESH
            print("🔄 Кликаем REFRESH...")
            refresh_success = self.guaranteed_click_refresh()
            
            if not refresh_success:
                print("❌ Не удалось кликнуть REFRESH, продолжаем цикл...")
            
            print(f"⏳ Ждем {REFRESH_INTERVAL} секунды до следующего цикла...")
            time.sleep(REFRESH_INTERVAL)

    def find_ok_button_after_dotaland(self, timeout=OK_TIMEOUT):
        """
        Поиск кнопки OK после нажатия DOTALAND
        """
        print("🎯 ПОИСК КНОПКИ 'OK' ПОСЛЕ DOTALAND")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < timeout:
            if not pause_handler.check_pause("Поиск OK после DOTALAND"):
                return None
                
            attempt += 1
            print(f"🔍 Попытка {attempt} поиска OK...")
            
            try:
                screenshot = pyautogui.screenshot()
                
                # Обработка для OK (белый текст на зеленом фоне)
                if screenshot.mode != 'L':
                    processed = screenshot.convert('L')
                else:
                    processed = screenshot.copy()
                
                # Усиление контраста для белого текста
                binary_high = processed.point(lambda x: 255 if x > 200 else 0)
                
                custom_config = r'--oem 3 --psm 6'
                data = pytesseract.image_to_data(
                    binary_high, 
                    output_type=pytesseract.Output.DICT,
                    config=custom_config,
                    lang='eng'
                )
                
                for i in range(len(data['text'])):
                    text = data['text'][i].strip().upper()
                    confidence = int(data['conf'][i])
                    
                    if text == "OK" and confidence > 40:
                        x = data['left'][i]
                        y = data['top'][i]
                        w = data['width'][i]
                        h = data['height'][i]
                        
                        center_x = x + w // 2
                        center_y = y + h // 2
                        
                        print(f"✅ OK найден! Уверенность: {confidence}%")
                        
                        return {
                            'text': text,
                            'position': (center_x, center_y),
                            'confidence': confidence,
                            'bbox': (x, y, w, h)
                        }
                
                print(f"❌ OK не найден в попытке {attempt}")
                
            except Exception as e:
                print(f"⚠️ Ошибка при поиске OK: {e}")
            
            time.sleep(1)
        
        print("❌ Кнопка OK не найдена")
        return None

    def find_and_click_ok_after_dotaland(self):
        """
        Поиск и клик по кнопке OK после DOTALAND
        """
        result = self.find_ok_button_after_dotaland(timeout=OK_TIMEOUT)
        
        if result:
            x, y = result['position']
            print(f"🎯 Кнопка OK найдена! Позиция: ({x}, {y})")
            
            if self.detector.reliable_click(x, y):
                print("✅ Успешный клик по OK!")
                time.sleep(CLICK_INTERVAL)
                return True
            else:
                print("❌ Не удалось кликнуть по OK")
                return False
        else:
            print("❌ Кнопка OK не найдена, продолжаем...")
            return False

    def refresh_and_join_game(self, restart_count=0):
        pause_handler.set_current_operation("Присоединение к игре", {'stage': 'Поиск DOTALAND'})
        """
        Обновление списка игр и присоединение к DOTALAND
        """
        print("\n" + "=" * 60)
        print("🎯 ОБНОВЛЕНИЕ И ПРИСОЕДИНЕНИЕ К ИГРЕ")
        print("=" * 60)
        
        print("\n" + "=" * 60)
        print("🔄 УСКОРЕННЫЙ ПОИСК: УМНЫЙ DOTALAND + REFRESH")
        print("=" * 60)
        
        # Сбрасываем счетчики при новом запуске
        self.dotaland_check_counter = 0
        self.dotaland_miss_count = 0
        
        cycle_success, restart_reason = self.guaranteed_refresh_dotaland_cycle(timeout=REFRESH_TIMEOUT)
        
        if cycle_success == True:
            print("🎉 ACCEPT успешно нажат! Передаем управление в AFK лобби...")
            
            # Сбрасываем позицию DOTALAND при успешном входе
            self.dotaland_position = None
            self.dotaland_confidence = 0
            
            monitor_result, monitor_reason = self.afk_monitor.monitor_after_accept(restart_count)
            
            if monitor_result == "RESTART":
                # Улучшаем логирование причины перезапуска из AFK
                if "таймаут" in monitor_reason.lower():
                    detailed_reason = "Лобби AFK больше таймаута"
                elif "9999999" in monitor_reason:
                    detailed_reason = "9999999 найден в чате"
                else:
                    detailed_reason = monitor_reason
                return "RESTART", detailed_reason
            else:
                return True, ""
        elif cycle_success == "RESTART":
            print("🔄 Требуется перезапуск игры")
            return "RESTART", restart_reason
        else:
            print("❌ Не удалось найти и присоединиться к игре")
            return False, "Не удалось найти DOTALAND"

    def find_dotaland_single_attempt(self):
        """
        Одиночная попытка найти DOTALAND
        """
        try:
            screenshot = pyautogui.screenshot()
            
            custom_config = r'--oem 3 --psm 6'
            data = pytesseract.image_to_data(
                screenshot, 
                output_type=pytesseract.Output.DICT,
                config=custom_config,
                lang='eng'
            )
            
            for i in range(len(data['text'])):
                text = data['text'][i].strip().upper()
                confidence = int(data['conf'][i])
                
                if text == "DOTALAND" and confidence > 40:
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    
                    center_x = x + w // 2
                    center_y = y + h // 2
                    
                    print(f"✅ DOTALAND найден! Уверенность: {confidence}%")
                    
                    return {
                        'text': text,
                        'position': (center_x, center_y),
                        'confidence': confidence,
                        'bbox': (x, y, w, h)
                    }
            
            print("❌ DOTALAND не найден в этой попытке")
            return None
            
        except Exception as e:
            print(f"⚠️ Ошибка при поиске DOTALAND: {e}")
            return None
        
# lobby_navigator.py (добавляем класс для режима по приглашению)

class InviteModeNavigator:
    """
    Навигатор для режима "По приглашению"
    """
    def __init__(self, text_detector, logger):
        self.detector = text_detector
        self.logger = logger
        self.afk_monitor = AFKLobbyMonitor(logger)
        
    def find_accept_button_accurate(self, timeout=10):
        """
        ТОЧНЫЙ поиск кнопки ACCEPT без проверки размера
        """
        try:
            screenshot = pyautogui.screenshot()
            
            # Обработка для ACCEPT (белый текст на зеленом фоне)
            if screenshot.mode != 'L':
                processed = screenshot.convert('L')
            else:
                processed = screenshot.copy()
            
            # Усиление контраста для белого текста
            binary_high = processed.point(lambda x: 255 if x > 200 else 0)
            
            custom_config = r'--oem 3 --psm 6'
            data = pytesseract.image_to_data(
                binary_high, 
                output_type=pytesseract.Output.DICT,
                config=custom_config,
                lang='eng'
            )
            
            valid_accepts = []
            
            for i in range(len(data['text'])):
                text = data['text'][i].strip().upper()
                confidence = int(data['conf'][i])
                
                if text == "ACCEPT" and confidence > 50:  # 🔥 Повышаем уверенность до 50%
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    
                    # 🔥 УБИРАЕМ ПРОВЕРКУ РАЗМЕРА - принимаем любые размеры
                    center_x_btn = x + w // 2
                    center_y_btn = y + h // 2
                    
                    valid_accepts.append({
                        'text': text,
                        'position': (center_x_btn, center_y_btn),
                        'confidence': confidence,
                        'bbox': (x, y, w, h)
                    })
            
            if valid_accepts:
                # 🔥 ВЫБИРАЕМ РЕЗУЛЬТАТ С НАИВЫСШЕЙ УВЕРЕННОСТЬЮ
                best_accept = max(valid_accepts, key=lambda x: x['confidence'])
                print(f"    ✅ ACCEPT найден! Уверенность: {best_accept['confidence']}%, "
                      f"Размер: {best_accept['bbox'][2]}x{best_accept['bbox'][3]}")
                
                return best_accept
            
            return None
            
        except Exception as e:
            print(f"⚠️ Ошибка при поиске ACCEPT: {e}")
            return None
        
    def wait_for_first_accept(self, timeout=INVITE_MODE_ACCEPT_TIMEOUT):
        """
        Ожидание первого ACCEPT в течение 5 минут
        """
        print("🎯 РЕЖИМ 'ПО ПРИГЛАШЕНИЮ': ОЖИДАНИЕ ПЕРВОГО ACCEPT")
        print(f"⏰ Таймаут: {timeout} секунд ({timeout//60} минут)")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < timeout:
            if not pause_handler.check_pause("Поиск ACCEPT"):
                return "RESTART"  # 🔥 ВОЗВРАЩАЕМ "RESTART" если был запрос перезапуска
            if not pause_handler.check_pause("Ожидание первого ACCEPT"):
                return False, "Пауза пользователем"
                
            attempt += 1
            elapsed = int(time.time() - start_time)
            remaining = timeout - elapsed
            
            print(f"\n🔍 Попытка {attempt} поиска первого ACCEPT...")
            print(f"⏱ Прошло: {elapsed}сек, Осталось: {remaining}сек")
            
            # Ищем ACCEPT с улучшенным алгоритмом
            accept_result = self.find_accept_button_accurate(timeout=10)
            
            if accept_result:
                x, y = accept_result['position']
                print(f"✅ ПЕРВЫЙ ACCEPT НАЙДЕН! Позиция: ({x}, {y})")
                print(f"📊 Уверенность: {accept_result['confidence']}%")
                
                # 🔥 ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: делаем скриншот области для отладки
                self.save_accept_debug_screenshot(accept_result['bbox'], "first_accept")
                
                # Кликаем по ACCEPT
                if self.detector.reliable_click(x, y):
                    print("✅ Успешный клик по первому ACCEPT!")
                    self.logger.log_info("Первый ACCEPT найден и нажат", attempt)
                    
                    # 🔥 Ждем немного после клика
                    time.sleep(2)
                    return True, ""
                else:
                    print("❌ Не удалось кликнуть по первому ACCEPT")
                    return False, "Ошибка клика по первому ACCEPT"
            
            # Ждем перед следующей попыткой
            time.sleep(3)
        
        print("❌ Первый ACCEPT не найден за отведенное время")
        return False, "Таймаут ожидания первого ACCEPT"
    
    def wait_for_second_accept(self, timeout=INVITE_MODE_SECOND_ACCEPT_TIMEOUT):
        """
        Ожидание второго ACCEPT в течение 4 минут
        """
        print("🎯 РЕЖИМ 'ПО ПРИГЛАШЕНИЮ': ОЖИДАНИЕ ВТОРОГО ACCEPT")
        print(f"⏰ Таймаут: {timeout} секунд ({timeout//60} минут)")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < timeout:
            if not pause_handler.check_pause("Ожидание второго ACCEPT"):
                return False, "Пауза пользователем"
                
            attempt += 1
            elapsed = int(time.time() - start_time)
            remaining = timeout - elapsed
            
            print(f"\n🔍 Попытка {attempt} поиска второго ACCEPT...")
            print(f"⏱ Прошло: {elapsed}сек, Осталось: {remaining}сек")
            
            # Ищем ACCEPT с улучшенным алгоритмом
            accept_result = self.find_accept_button_accurate(timeout=10)
            
            if accept_result:
                x, y = accept_result['position']
                print(f"✅ ВТОРОЙ ACCEPT НАЙДЕН! Позиция: ({x}, {y})")
                print(f"📊 Уверенность: {accept_result['confidence']}%")
                
                # 🔥 ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: делаем скриншот области для отладки
                self.save_accept_debug_screenshot(accept_result['bbox'], "second_accept")
                
                # Кликаем по ACCEPT
                if self.detector.reliable_click(x, y):
                    print("✅ Успешный клик по второму ACCEPT!")
                    self.logger.log_info("Второй ACCEPT найден и нажат", attempt)
                    
                    # 🔥 Ждем немного после клика
                    time.sleep(2)
                    return True, ""
                else:
                    print("❌ Не удалось кликнуть по второму ACCEPT")
                    return False, "Ошибка клика по второму ACCEPT"
            
            # Ждем 5 секунд перед следующей попыткой
            time.sleep(5)
        
        print("❌ Второй ACCEPT не найден за отведенное время")
        return False, "Таймаут ожидания второго ACCEPT"
    
    def save_accept_debug_screenshot(self, bbox, description):
        """
        Сохраняет скриншот области где был найден ACCEPT для отладки
        """
        try:
            if not ENABLE_DEBUG_SCREENSHOTS:
                return
            x, y, w, h = bbox
            # Увеличиваем область для лучшего обзора
            expanded_region = (
                max(0, x - 20),
                max(0, y - 20),
                w + 40,
                h + 40
            )
            
            screenshot = pyautogui.screenshot(region=expanded_region)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"debug/accept_{timestamp}_{description}.png"
            
            import os
            os.makedirs("debug", exist_ok=True)
            screenshot.save(filename)
            print(f"📸 Скриншот ACCEPT сохранен: {filename}")
            
        except Exception as e:
            print(f"⚠️ Не удалось сохранить скриншот ACCEPT: {e}")
    
    def run_invite_mode(self):
        """
        Основной метод для режима по приглашению с улучшенными проверками
        """
        print("🚀 ЗАПУСК РЕЖИМА 'ПО ПРИГЛАШЕНИЮ'")
        print("=" * 60)
        
        # 🔥 ПРОВЕРКА: убедимся что игра загрузилась
        print("⏳ Ожидаем полной загрузки игры...")
        time.sleep(10)
        
        # ШАГ 1: Ожидание первого ACCEPT (5 минут)
        first_accept, reason = self.wait_for_first_accept(INVITE_MODE_ACCEPT_TIMEOUT)
        
        if not first_accept:
            print(f"❌ Режим приглашения: не удалось найти первый ACCEPT - {reason}")
            return "RESTART", f"Первый ACCEPT не найден: {reason}"
        
        print("🎉 ПЕРВЫЙ ACCEPT УСПЕШНО ОБРАБОТАН!")
        print("⏳ Ожидаем второй ACCEPT...")
        
        # 🔥 ДОПОЛНИТЕЛЬНОЕ ОЖИДАНИЕ между ACCEPT'ами
        print("⏳ Ожидаем появление второго ACCEPT...")
        time.sleep(10)
        
        # ШАГ 2: Ожидание второго ACCEPT (4 минуты)
        second_accept, reason = self.wait_for_second_accept(INVITE_MODE_SECOND_ACCEPT_TIMEOUT)
        
        if not second_accept:
            print(f"❌ Режим приглашения: не удалось найти второй ACCEPT - {reason}")
            return "RESTART", f"Второй ACCEPT не найден: {reason}"
        
        print("🎉 ВТОРОЙ ACCEPT УСПЕШНО ОБРАБОТАН!")
        print("🚀 Переходим к стандартному AFK мониторингу...")
        
        # 🔥 ДОПОЛНИТЕЛЬНОЕ ОЖИДАНИЕ перед AFK мониторингом
        print("⏳ Ожидаем загрузку лобби...")
        time.sleep(15)
        
        # ШАГ 3: Стандартный AFK мониторинг (как в обычном режиме)
        monitor_result, monitor_reason = self.afk_monitor.monitor_after_accept(0)
        
        if monitor_result == "RESTART":
            return "RESTART", monitor_reason
        else:
            return True, "Все операции завершены успешно"