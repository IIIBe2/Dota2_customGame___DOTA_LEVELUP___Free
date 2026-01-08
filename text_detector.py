# text_detector.py
import time
import pyautogui
import os
import pytesseract
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from config import CLICK_INTERVAL, ENABLE_DEBUG_SCREENSHOTS
from pause_handler import pause_handler  # Добавляем импорт

class TextDetector:
    def __init__(self, tesseract_path=None):
        """
        Инициализация детектора текста
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
                
        if tesseract_path and os.path.exists(tesseract_path):
            found_path = tesseract_path
        
        if found_path:
            pytesseract.pytesseract.tesseract_cmd = found_path
            print(f"✅ Tesseract найден: {found_path}")
        else:
            print("❌ Tesseract не найден. Установите Tesseract-OCR")
    
    def smart_preprocess_for_ok_button(self, image):
        """
        Специальная обработка для кнопки OK с белым текстом на зеленом фоне
        """
        if image.mode != 'L':
            gray = image.convert('L')
        else:
            gray = image.copy()
        
        binary_high = gray.point(lambda x: 255 if x > 200 else 0)
        
        return {
            'binary_high': binary_high
        }

    def find_ok_button_enhanced_with_debug(self, region=None, timeout=60):
        """
        Усиленный поиск кнопки OK
        """
        print("🎯 УСИЛЕННЫЙ ПОИСК КНОПКИ 'OK'")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < timeout:
            # Проверка паузы
            if not pause_handler.check_pause("Поиск OK"):
                return None
                
            attempt += 1
            print(f"\n🔍 ПОПЫТКА {attempt} ПОИСКА OK")
            
            try:
                if region:
                    screenshot = pyautogui.screenshot(region=region)
                else:
                    screenshot = pyautogui.screenshot()
                
                processed_images = self.smart_preprocess_for_ok_button(screenshot)
                
                best_result = None
                best_confidence = 0
                
                method_name = 'binary_high'
                processed_image = processed_images[method_name]
                
                custom_config = r'--oem 3 --psm 6'
                try:
                    data = pytesseract.image_to_data(
                        processed_image, 
                        output_type=pytesseract.Output.DICT,
                        config=custom_config,
                        lang='eng'
                    )
                    
                    for i in range(len(data['text'])):
                        text = data['text'][i].strip().upper()
                        confidence = int(data['conf'][i])
                        
                        if text == "OK" and confidence > 30:
                            x = data['left'][i]
                            y = data['top'][i]
                            w = data['width'][i]
                            h = data['height'][i]
                            
                            center_x = x + w // 2
                            center_y = y + h // 2
                            
                            print(f"✅ OK найден! Уверенность: {confidence}%")
                            
                            if confidence > best_confidence:
                                best_confidence = confidence
                                best_result = {
                                    'text': text,
                                    'position': (center_x, center_y),
                                    'confidence': confidence,
                                    'method': f"{method_name}_PSM_6",
                                    'bbox': (x, y, w, h)
                                }
                    
                except Exception as e:
                    print(f"⚠️ Ошибка в PSM 6: {e}")
                
                if best_result and best_confidence > 40:
                    print(f"✅ УСПЕХ! Уверенность: {best_confidence}%")
                    return best_result
                else:
                    print("❌ OK не найден в этой попытке")
                
            except Exception as e:
                print(f"⚠️ Ошибка при поиске OK: {e}")
            
            print(f"⏳ Ждем 3 секунды...")
            time.sleep(3)
        
        print(f"❌ Кнопка OK не найдена за {timeout} секунд")
        return None

    def find_text_on_screen(self, search_texts, region=None, timeout=60, interval=3):
        """
        Стандартный поиск текста на экране с поддержкой регионов
        """
        print(f"🔍 Поиск: {search_texts}")
        if region:
            print(f"📍 Область поиска: {region}")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < timeout:
            # Проверка паузы
            if not pause_handler.check_pause("Поиск текста"):
                return None
                
            attempt += 1
            print(f"🕒 Попытка {attempt}...")
            
            try:
                if region:
                    screenshot = pyautogui.screenshot(region=region)
                else:
                    screenshot = pyautogui.screenshot()
                
                if screenshot.mode != 'L':
                    processed = screenshot.convert('L')
                else:
                    processed = screenshot.copy()
                
                enhancer = ImageEnhance.Contrast(processed)
                processed = enhancer.enhance(2.0)
                
                custom_config = r'--oem 3 --psm 6'
                data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT, config=custom_config, lang='eng')
                
                found_texts = []
                
                for i in range(len(data['text'])):
                    text = data['text'][i].strip()
                    confidence = int(data['conf'][i])
                    
                    if not text or confidence < 20:
                        continue
                    
                    for search_text in search_texts:
                        if search_text.upper() in text.upper():
                            x = data['left'][i]
                            y = data['top'][i]
                            w = data['width'][i]
                            h = data['height'][i]
                            
                            # Добавляем смещение если поиск в области
                            if region:
                                x += region[0]
                                y += region[1]
                            
                            center_x = x + w // 2
                            center_y = y + h // 2
                            
                            found_texts.append({
                                'text': text,
                                'search_text': search_text,
                                'position': (center_x, center_y),
                                'confidence': confidence,
                                'bbox': (x, y, w, h)
                            })
                            
                            print(f"✅ Найден: '{text}' (уверенность: {confidence}%)")
                
                if found_texts:
                    best_match = max(found_texts, key=lambda x: x['confidence'])
                    print(f"🎯 Лучшее совпадение: '{best_match['text']}'")
                    return best_match
                else:
                    print(f"❌ Искомые тексты не найдены. Ждем {interval} сек...")
                    
            except Exception as e:
                print(f"⚠️ Ошибка при распознавании: {e}")
            
            time.sleep(interval)
        
        print(f"❌ Ни один текст не найден за {timeout} секунд")
        return None

    def find_find_button_fast(self, region=None, timeout=60):
        pause_handler.set_current_operation("Поиск кнопки FIND")
        """
        НАДЕЖНЫЙ поиск кнопки FIND с проверкой координат и контекста
        """
        print("🎯 НАДЕЖНЫЙ ПОИСК КНОПКИ 'FIND'")
        
        start_time = time.time()
        attempt = 0
        
        # Создаем директорию для скриншотов если ее нет
        import os
        os.makedirs("debug/find_reliable", exist_ok=True)
        
        # 🔥 РАССЧИТЫВАЕМ ОЖИДАЕМЫЕ КООРДИНАТЫ FIND
        screen_width, screen_height = pyautogui.size()
        
        # FIND обычно находится в центре-правой части экрана, не слишком близко к краям
        expected_x_min = screen_width * 0.30  # Не слишком слева
        expected_x_max = screen_width * 0.85  # Не слишком справа
        expected_y_min = screen_height * 0.50  # Ниже центра
        expected_y_max = screen_height * 0.90  # Не слишком низко
        
        print(f"📏 Экран: {screen_width}x{screen_height}")
        print(f"📍 Ожидаемая область FIND: X[{int(expected_x_min)}-{int(expected_x_max)}], Y[{int(expected_y_min)}-{int(expected_y_max)}]")
        
        # 🔥 ОПТИМИЗИРОВАННАЯ ОБЛАСТЬ ПОИСКА
        if region is None:
            # Более узкая область поиска - там где ДОЛЖЕН быть FIND
            top_margin = int(screen_height * 0.50)    # 50%
            left_margin = int(screen_width * 0.40)    # 40% (уже чем было)
            right_margin = int(screen_width * 0.20)   # 20%
            bottom_margin = int(screen_height * 0.10) # 10%
            
            region = (
                left_margin,
                top_margin,
                screen_width - left_margin - right_margin,
                screen_height - top_margin - bottom_margin
            )
            
            print(f"📐 Область поиска: {region}")
        
        while time.time() - start_time < timeout:
            # Проверка паузы
            if not pause_handler.check_pause("Поиск FIND"):
                return None
                
            attempt += 1
            print(f"\n🔍 ПОПЫТКА {attempt} ПОИСКА FIND")
            print("=" * 40)
            
            try:
                screenshot = pyautogui.screenshot(region=region)
                
                # 🔥 СОХРАНЯЕМ СКРИНШОТ
                timestamp = time.strftime("%H%M%S")
                screenshot_filename = f"debug/find_reliable/find_attempt_{attempt}_{timestamp}.png"
                if ENABLE_DEBUG_SCREENSHOTS:
                    screenshot.save(screenshot_filename)
                print(f"📸 Скриншот: {screenshot_filename}")
                
                # 🔥 ТОЛЬКО ЭФФЕКТИВНЫЕ МЕТОДЫ
                if screenshot.mode != 'RGB':
                    rgb_screenshot = screenshot.convert('RGB')
                else:
                    rgb_screenshot = screenshot.copy()
                
                # 1. Простой метод - прямое распознавание
                gray = rgb_screenshot.convert('L')
                
                # 2. Фильтр для белого текста (FIND - белый текст)
                white_mask = gray.point(lambda x: 255 if x > 180 else 0)
                
                methods = [
                    ('direct', gray, r'--oem 3 --psm 6'),  # Прямое распознавание
                    ('white_text', white_mask, r'--oem 3 --psm 10'),  # Белый текст
                ]
                
                best_result = None
                best_confidence = 0
                
                for method_name, processed_img, custom_config in methods:
                    print(f"  🧪 Метод: {method_name}")
                    
                    try:
                        data = pytesseract.image_to_data(
                            processed_img, 
                            output_type=pytesseract.Output.DICT,
                            config=custom_config,
                            lang='eng'
                        )
                        
                        # 🔥 ВЫВОДИМ ТОЛЬКО ТЕКСТЫ С ВЫСОКОЙ УВЕРЕННОСТЬЮ И ПОХОЖИЕ НА FIND
                        found_candidates = []
                        
                        for i in range(len(data['text'])):
                            text = data['text'][i].strip().upper()
                            confidence = int(data['conf'][i])
                            
                            if not text or confidence < 60:  # 🔥 ПОВЫШАЕМ ПОРОГ УВЕРЕННОСТИ
                                continue
                            
                            x = data['left'][i] + region[0]
                            y = data['top'][i] + region[1]
                            w = data['width'][i]
                            h = data['height'][i]
                            
                            # 🔥 ПРОВЕРЯЕМ КООРДИНАТЫ
                            if not (expected_x_min <= x <= expected_x_max and 
                                    expected_y_min <= y <= expected_y_max):
                                # Текст не в ожидаемой области FIND
                                continue
                            
                            # 🔥 ПРОВЕРЯЕМ РАЗМЕР (FIND обычно 50-150px шириной, 20-50px высотой)
                            if not (40 <= w <= 150 and 15 <= h <= 60):
                                continue
                            
                            # 🔥 ПОИСК ТОЧНОГО СОВПАДЕНИЯ С FIND
                            search_texts = ["FIND"]
                            # F|ND и F1ND - это ошибки распознавания, но только если уверенность очень высокая
                            if confidence > 85:
                                search_texts.extend(["F|ND", "F1ND"])
                            
                            found_match = False
                            actual_text = text
                            
                            for search_text in search_texts:
                                if search_text == text:  # 🔥 ТОЛЬКО ТОЧНОЕ СОВПАДЕНИЕ
                                    found_match = True
                                    actual_text = search_text
                                    break
                            
                            if found_match:
                                center_x = x + w // 2
                                center_y = y + h // 2
                                
                                print(f"    ✅ КАНДИДАТ: '{actual_text}' {confidence}% "
                                    f"({w}x{h}) в ({x}, {y})")
                                
                                found_candidates.append({
                                    'text': actual_text,
                                    'position': (center_x, center_y),
                                    'confidence': confidence,
                                    'method': method_name,
                                    'bbox': (x, y, w, h),
                                    'original_text': text
                                })
                        
                        # 🔥 ВЫБИРАЕМ ЛУЧШЕГО КАНДИДАТА
                        for candidate in found_candidates:
                            # Дополнительная проверка: FIND обычно находится рядом с другими кнопками лобби
                            # Проверяем, есть ли рядом текст "PRIVATE", "LOBBY" и т.д.
                            x, y, w, h = candidate['bbox']
                            
                            if candidate['confidence'] > best_confidence:
                                best_confidence = candidate['confidence']
                                best_result = {
                                    'text': candidate['text'],
                                    'position': candidate['position'],
                                    'confidence': candidate['confidence'],
                                    'method': candidate['method'],
                                    'bbox': candidate['bbox'],
                                    'screenshot': screenshot_filename
                                }
                        
                        if found_candidates:
                            print(f"    📋 Найдено кандидатов: {len(found_candidates)}")
                                
                    except Exception as e:
                        print(f"    ⚠️ Ошибка: {e}")
                
                # 🔥 ЕСЛИ НЕ НАШЛИ, ПРОБУЕМ ПОИСК ПО ОКРЕСТНОСТЯМ КНОПОК ЛОББИ
                if best_result is None and attempt <= 3:
                    print("  🔍 Пробуем поиск в зоне кнопок лобби...")
                    
                    # Создаем область вокруг ожидаемого места FIND
                    search_x = int(screen_width * 0.60)  # Примерно 60% от ширины
                    search_y = int(screen_height * 0.70) # Примерно 70% от высоты
                    
                    lobby_region = (
                        search_x - 200,
                        search_y - 100,
                        400,
                        200
                    )
                    
                    print(f"  📍 Зона кнопок лобби: {lobby_region}")
                    
                    try:
                        lobby_screenshot = pyautogui.screenshot(region=lobby_region)
                        lobby_filename = f"debug/find_reliable/lobby_area_{attempt}_{timestamp}.png"
                        lobby_screenshot.save(lobby_filename)
                        print(f"  📸 Зона лобби: {lobby_filename}")
                        
                        # Ищем белый текст в этой области
                        if lobby_screenshot.mode != 'L':
                            lobby_gray = lobby_screenshot.convert('L')
                        else:
                            lobby_gray = lobby_screenshot.copy()
                        
                        lobby_white = lobby_gray.point(lambda x: 255 if x > 190 else 0)
                        
                        data = pytesseract.image_to_data(
                            lobby_white, 
                            output_type=pytesseract.Output.DICT,
                            config=r'--oem 3 --psm 6',
                            lang='eng'
                        )
                        
                        for i in range(len(data['text'])):
                            text = data['text'][i].strip().upper()
                            confidence = int(data['conf'][i])
                            
                            if text == "FIND" and confidence > 70:
                                x = data['left'][i] + lobby_region[0]
                                y = data['top'][i] + lobby_region[1]
                                w = data['width'][i]
                                h = data['height'][i]
                                
                                center_x = x + w // 2
                                center_y = y + h // 2
                                
                                print(f"    ✅ FIND найден в зоне лобби! {confidence}%")
                                
                                best_result = {
                                    'text': text,
                                    'position': (center_x, center_y),
                                    'confidence': confidence,
                                    'method': 'lobby_zone',
                                    'bbox': (x, y, w, h),
                                    'screenshot': lobby_filename
                                }
                                break
                                
                    except Exception as e:
                        print(f"    ⚠️ Ошибка поиска в зоне лобби: {e}")
                
                if best_result:
                    print(f"\n🎯 FIND НАЙДЕН НАДЕЖНО!")
                    print(f"📊 Уверенность: {best_result['confidence']}%")
                    print(f"📍 Координаты: {best_result['position']}")
                    print(f"🧪 Метод: {best_result['method']}")
                    
                    # 🔥 СОХРАНЯЕМ ОБЛАСТЬ ДЛЯ ВЕРИФИКАЦИИ
                    try:
                        x, y, w, h = best_result['bbox']
                        find_area = (
                            max(0, x - 30),
                            max(0, y - 30),
                            w + 60,
                            h + 60
                        )
                        find_screenshot = pyautogui.screenshot(region=find_area)
                        found_filename = f"debug/find_reliable/FIND_VERIFIED_{attempt}_{timestamp}.png"
                        
                        # Добавляем рамку и текст
                        from PIL import ImageDraw, ImageFont
                        draw = ImageDraw.Draw(find_screenshot)
                        draw.rectangle([30, 30, 30+w, 30+h], outline="green", width=3)
                        
                        # Подпись
                        draw.text((10, 10), f"FIND {best_result['confidence']}%", 
                                fill="green", stroke_width=2, stroke_fill="black")
                        
                        find_screenshot.save(found_filename)
                        print(f"✅ Верифицированная область: {found_filename}")
                        
                        best_result['verified_screenshot'] = found_filename
                        
                    except Exception as e:
                        print(f"⚠️ Не удалось сохранить верифицированную область: {e}")
                    
                    return best_result
                
                print(f"❌ FIND не найден в этой попытке")
                
            except Exception as e:
                print(f"⚠️ Ошибка при поиске FIND: {e}")
            
            print(f"⏳ Ждем 2 секунды...")
            time.sleep(2)
        
        print(f"\n❌ Кнопка FIND не найдена за {timeout} секунд")
        
        # 🔥 СОХРАНЯЕМ ПОСЛЕДНИЙ СКРИНШОТ ДЛЯ АНАЛИЗА
        try:
            final_screenshot = pyautogui.screenshot()
            final_filename = f"debug/find_reliable/LAST_SCREEN_{int(time.time())}.png"
            final_screenshot.save(final_filename)
            print(f"📸 Последний скриншот экрана: {final_filename}")
            
            # Также сохраняем область поиска
            region_screenshot = pyautogui.screenshot(region=region)
            region_filename = f"debug/find_reliable/SEARCH_AREA_{int(time.time())}.png"
            region_screenshot.save(region_filename)
            print(f"📸 Область поиска: {region_filename}")
            
        except Exception as e:
            print(f"⚠️ Не удалось сохранить скриншоты: {e}")
        
        return None

    def find_refresh_button(self, region=None, timeout=60):
        """
        Поиск кнопки REFRESH
        """
        print("🎯 ПОИСК КНОПКИ 'REFRESH'")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < timeout:
            # 🔥 ДОБАВИТЬ ЭТУ ПРОВЕРКУ:
            if not pause_handler.check_pause("Поиск FIND"):
                return None  # Прерываем поиск если запрошен перезапуск
            
            # Проверка паузы
            if not pause_handler.check_pause("Поиск REFRESH"):
                return None
                
            attempt += 1
            print(f"🔍 Попытка {attempt} поиска REFRESH...")
            
            try:
                if region:
                    screenshot = pyautogui.screenshot(region=region)
                else:
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
                    
                    if text == "REFRESH" and confidence > 40:
                        x = data['left'][i]
                        y = data['top'][i]
                        w = data['width'][i]
                        h = data['height'][i]
                        
                        center_x = x + w // 2
                        center_y = y + h // 2
                        
                        print(f"✅ REFRESH найден! Уверенность: {confidence}%")
                        
                        return {
                            'text': text,
                            'position': (center_x, center_y),
                            'confidence': confidence,
                            'method': 'original_PSM_6',
                            'bbox': (x, y, w, h)
                        }
                
                print(f"❌ REFRESH не найден в попытке {attempt}")
                
            except Exception as e:
                print(f"⚠️ Ошибка при поиске REFRESH: {e}")
            
            print(f"⏳ Ждем 2 секунды...")
            time.sleep(2)
        
        print(f"❌ Кнопка REFRESH не найдена за {timeout} секунд")
        return None

    def find_dotaland_button(self, region=None, timeout=60):
        """
        Поиск кнопки DOTALAND
        """
        print("🎯 ПОИСК КНОПКИ 'DOTALAND'")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < timeout:
            # Проверка паузы
            if not pause_handler.check_pause("Поиск DOTALAND"):
                return None
                
            attempt += 1
            print(f"🔍 Попытка {attempt} поиска DOTALAND...")
            
            try:
                if region:
                    screenshot = pyautogui.screenshot(region=region)
                else:
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
                            'method': 'original_PSM_6',
                            'bbox': (x, y, w, h)
                        }
                
                print(f"❌ DOTALAND не найден в попытке {attempt}")
                
            except Exception as e:
                print(f"⚠️ Ошибка при поиске DOTALAND: {e}")
            
            print(f"⏳ Ждем 2 секунды...")
            time.sleep(2)
        
        print(f"❌ Кнопка DOTALAND не найдена за {timeout} секунд")
        return None
    
    def reliable_click(self, x, y, clicks=1, interval=0.1):
        """
        Надежный клик с указанием количества кликов
        """
        try:
            # Убираем мышь с пути (используем существующий метод)
            #self.safe_move_away()  # Или создаем новый метод
            time.sleep(0.1)
            
            # Перемещаемся к цели
            pyautogui.moveTo(x, y, duration=0.2)
            time.sleep(0.05)
            
            # Выполняем клик(и)
            pyautogui.click(clicks=clicks, interval=interval)
            
            print(f"🖱️ {'ТРОЙНОЙ' if clicks == 3 else 'Обычный'} клик в позицию ({x}, {y})")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка клика: {e}")
            return False

    def find_and_click_ok_button(self, timeout=90):
        pause_handler.set_current_operation("Поиск кнопки OK после DOTALAND")
        """
        Упрощенный поиск и клик по кнопке OK
        """
        print("🎯 ПОИСК КНОПКИ OK")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < timeout:
            if not pause_handler.check_pause("Поиск OK"):
                return False
                
            attempt += 1
            print(f"🔍 Попытка {attempt} поиска OK...")
            
            try:
                screenshot = pyautogui.screenshot()
                
                # Простая обработка для OK (белый текст на зеленом)
                if screenshot.mode != 'L':
                    processed = screenshot.convert('L')
                else:
                    processed = screenshot.copy()
                
                # Бинаризация для белого текста
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
                    
                    if text == "OK" and confidence > 30:
                        x = data['left'][i]
                        y = data['top'][i]
                        w = data['width'][i]
                        h = data['height'][i]
                        
                        center_x = x + w // 2
                        center_y = y + h // 2
                        
                        print(f"✅ OK найден! Уверенность: {confidence}%")
                        print(f"📍 Позиция: ({center_x}, {center_y})")
                        
                        # Клик по OK
                        if self.reliable_click(center_x, center_y):
                            print("✅ Успешный клик по OK!")
                            return True
                        else:
                            print("❌ Не удалось кликнуть по OK")
                            return False
                
                print(f"❌ OK не найден в попытке {attempt}")
                
            except Exception as e:
                print(f"⚠️ Ошибка при поиске OK: {e}")
            
            time.sleep(2)  # Ждем 2 секунды между попытками
        
        print(f"❌ Кнопка OK не найдена за {timeout} секунд")
        return False

    def find_and_click_refresh_button(self, timeout=60):
        """
        Основной метод поиска и клика по кнопке REFRESH
        """
        print("🎯 ПОИСК КНОПКИ REFRESH")
        
        result = self.find_refresh_button(timeout=timeout)
        
        if result:
            x, y = result['position']
            print(f"🎯 Кнопка REFRESH найдена!")
            print(f"📍 Позиция: ({x}, {y})")
            print(f"🎯 Уверенность: {result['confidence']}%")
            
            if self.reliable_click(x, y):
                print("✅ Успешный клик по REFRESH!")
                time.sleep(3)
                return True
            else:
                print("❌ Не удалось кликнуть по REFRESH")
                return False
        else:
            print("❌ Кнопка REFRESH не найдена")
            return False

    def find_and_click_dotaland_button(self, timeout=60):
        """
        Основной метод поиска и клика по кнопке DOTALAND
        """
        print("🎯 ПОИСК КНОПКИ DOTALAND")
        
        result = self.find_dotaland_button(timeout=timeout)
        
        if result:
            x, y = result['position']
            print(f"🎯 Кнопка DOTALAND найдена!")
            print(f"📍 Позиция: ({x}, {y})")
            print(f"🎯 Уверенность: {result['confidence']}%")
            
            if self.reliable_click(x, y, clicks=3):  # 🔥 Меняем на 3 клика
                print("✅ Успешный ТРОЙНОЙ клик по DOTALAND!")
                return True
            else:
                print("❌ Не удалось кликнуть по DOTALAND")
                return False
        else:
            print("❌ Кнопка DOTALAND не найдена")
            return False

    def find_and_click_find_button(self, timeout=60):
        """
        Основной метод поиска и клика по кнопке FIND
        """
        print("🎯 ПОИСК КНОПКИ FIND")
        
        result = self.find_find_button_fast(timeout=timeout)
        
        if result:
            x, y = result['position']
            print(f"🎯 Кнопка FIND найдена!")
            print(f"📍 Позиция: ({x}, {y})")
            print(f"🎯 Уверенность: {result['confidence']}%")
            
            if self.reliable_click(x, y):
                print("✅ Успешный клик по FIND!")
                time.sleep(3)
                return True
            else:
                print("❌ Не удалось кликнуть по FIND")
                return False
        else:
            print("❌ Кнопка FIND не найдена")
            return False