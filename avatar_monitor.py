# avatar_monitor.py
import pyautogui
import pytesseract
import time
import os
from PIL import Image, ImageOps, ImageDraw, ImageEnhance, ImageFilter
from pause_handler import pause_handler
from config import ENABLE_DEBUG_SCREENSHOTS, FRAME_MONITOR_INTERVAL, RED_COLOR_THRESHOLD
from PIL import ImageEnhance, ImageFilter
# avatar_monitor.py (исправления)

class AvatarMonitor:
    def __init__(self, logger):
        self.logger = logger
        self.arrow_position = None
        self.avatar_frame_position = None
        self.avatar_frame_size = None
        self.setup_tesseract()
        self.debug_screenshot_count = 0
        self.last_frame_color = None

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

    def find_greater_than_symbol_fast(self):
        pause_handler.set_current_operation("Поиск стрелки '>'")
        """
        УСИЛЕННЫЙ метод поиска стрелки '>' на черном фоне
        """
        print("🎯 УСИЛЕННЫЙ ПОИСК СТРЕЛКИ '>' НА ЧЕРНОМ ФОНЕ")
        
        try:
            screen_width, screen_height = pyautogui.size()
            
            # 🔥 ОБЛАСТЬ ПОИСКА: левый верхний угол (10% ширины, 30% высоты)
            search_region = (
                0,  # левый край
                int(screen_height * 0.05),  # верхний край  
                int(screen_width * 0.10),   # 10% ширины
                int(screen_height * 0.30)   # 30% высоты
            )
            
            print(f"📐 Разрешение экрана: {screen_width}x{screen_height}")
            print(f"🔍 Область поиска стрелки: {search_region}")
            
            screenshot = pyautogui.screenshot(region=search_region)
            
            # 🔥 УСИЛЕННЫЕ ФИЛЬТРЫ ДЛЯ БЕЛОГО ТЕКСТА НА ЧЕРНОМ ФОНЕ
            if screenshot.mode != 'L':
                gray = screenshot.convert('L')
            else:
                gray = screenshot.copy()
            
            # 🔥 МЕТОД 1: Высокий контраст для белого на черном
            binary_high = gray.point(lambda x: 255 if x > 200 else 0)
            
            # 🔥 МЕТОД 2: Инверсия (черный текст на белом фоне)
            inverted = ImageOps.invert(gray)
            binary_inverted = inverted.point(lambda x: 255 if x > 150 else 0)
            
            # 🔥 МЕТОД 3: Адаптивный порог
            from PIL import ImageFilter
            enhanced = gray.filter(ImageFilter.SHARPEN)
            binary_adaptive = enhanced.point(lambda x: 255 if x > 180 else 0)
            
            # 🔥 МЕТОД 4: Усиление краев
            edges = gray.filter(ImageFilter.FIND_EDGES)
            binary_edges = edges.point(lambda x: 255 if x > 50 else 0)
            
            methods = [
                ("high_contrast", binary_high),
                ("inverted", binary_inverted), 
                ("adaptive", binary_adaptive),
                ("edges", binary_edges)
            ]
            
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=>'
            
            for method_name, processed_image in methods:
                print(f"  🧪 Метод: {method_name}")
                
                try:
                    data = pytesseract.image_to_data(
                        processed_image, 
                        output_type=pytesseract.Output.DICT,
                        config=custom_config,
                        lang='eng'
                    )
                    
                    for i in range(len(data['text'])):
                        text = data['text'][i].strip()
                        confidence = int(data['conf'][i])
                        
                        if text == '>' and confidence > 5:  # 🔥 Понижаем порог уверенности
                            x = data['left'][i] + search_region[0]
                            y = data['top'][i] + search_region[1]
                            w = data['width'][i]
                            h = data['height'][i]
                            
                            print(f"    ✅ Стрелка '>' найдена методом {method_name}! Уверенность: {confidence}%")
                            print(f"    📍 Позиция: ({x}, {y})")
                            
                            # 🔥 СОХРАНЯЕМ СКРИНШОТЫ ДЛЯ ОТЛАДКИ
                            #self.save_debug_screenshot(screenshot, "arrow_original")
                            #self.save_debug_screenshot(processed_image, f"arrow_{method_name}")
                            
                            self.arrow_position = (x, y)
                            return True
                            
                except Exception as e:
                    print(f"    ⚠️ Ошибка в методе {method_name}: {e}")
            
            # 🔥 ЕСЛИ НЕ НАШЛИ, ПРОБУЕМ ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ
            print("🔍 Пробуем дополнительные методы...")
            
            # 🔥 МЕТОД 5: Масштабирование изображения
            scaled = gray.resize((gray.width * 2, gray.height * 2), Image.Resampling.LANCZOS)
            binary_scaled = scaled.point(lambda x: 255 if x > 190 else 0)
            
            # 🔥 МЕТОД 6: Комбинация фильтров
            contrast_enhancer = ImageEnhance.Contrast(gray)
            high_contrast = contrast_enhancer.enhance(3.0)
            binary_combined = high_contrast.point(lambda x: 255 if x > 150 else 0)
            
            additional_methods = [
                ("scaled", binary_scaled),
                ("combined", binary_combined)
            ]
            
            for method_name, processed_image in additional_methods:
                print(f"  🧪 Дополнительный метод: {method_name}")
                
                try:
                    data = pytesseract.image_to_data(
                        processed_image, 
                        output_type=pytesseract.Output.DICT,
                        config=custom_config,
                        lang='eng'
                    )
                    
                    for i in range(len(data['text'])):
                        text = data['text'][i].strip()
                        confidence = int(data['conf'][i])
                        
                        if text == '>' and confidence > 5:
                            # Для масштабированных изображений корректируем координаты
                            if method_name == "scaled":
                                x = (data['left'][i] // 2) + search_region[0]
                                y = (data['top'][i] // 2) + search_region[1]
                            else:
                                x = data['left'][i] + search_region[0]
                                y = data['top'][i] + search_region[1]
                                
                            w = data['width'][i]
                            h = data['height'][i]
                            
                            print(f"    ✅ Стрелка '>' найдена методом {method_name}! Уверенность: {confidence}%")
                            print(f"    📍 Позиция: ({x}, {y})")
                            
                            self.save_debug_screenshot(processed_image, f"arrow_{method_name}_found")
                            self.arrow_position = (x, y)
                            return True
                            
                except Exception as e:
                    print(f"    ⚠️ Ошибка в дополнительном методе {method_name}: {e}")
            
            # 🔥 ЕСЛИ ВСЕ МЕТОДЫ НЕ СРАБОТАЛИ, СОХРАНЯЕМ СКРИНШОТЫ ДЛЯ АНАЛИЗА
            print("❌ Стрелка '>' не найдена ни одним методом")
            self.save_debug_screenshot(screenshot, "arrow_search_area")
            
            # Сохраняем все обработанные изображения для анализа
            for method_name, processed_image in methods + additional_methods:
                self.save_debug_screenshot(processed_image, f"arrow_processed_{method_name}")
            
            return False
            
        except Exception as e:
            print(f"❌ Ошибка при поиске стрелки: {e}")
            return False

    def debug_arrow_search_enhanced(self):
        """
        Усиленная дебаг-функция для тестирования поиска стрелки
        """
        print("🐛 УСИЛЕННЫЙ ДЕБАГ ПОИСКА СТРЕЛКИ")
        print("=" * 50)
        
        screen_width, screen_height = pyautogui.size()
        search_region = (0, 0, int(screen_width * 0.10), int(screen_height * 0.30))
        
        print(f"📐 Экран: {screen_width}x{screen_height}")
        print(f"🔍 Область поиска: {search_region}")
        
        # Делаем скриншот
        screenshot = pyautogui.screenshot(region=search_region)
        #self.save_debug_screenshot(screenshot, "debug_arrow_area")
        print("✅ Скриншот сохранен: debug_arrow_area.png")
        
        # Показываем что видит Tesseract во всех методах
        methods = [
            ("original", screenshot),
            ("high_contrast", screenshot.convert('L').point(lambda x: 255 if x > 200 else 0)),
            ("inverted", ImageOps.invert(screenshot.convert('L')).point(lambda x: 255 if x > 150 else 0)),
        ]
        
        for method_name, image in methods:
            print(f"\n📝 Метод {method_name}:")
            custom_config = r'--oem 3 --psm 6'
            try:
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config=custom_config, lang='eng')
                
                found_anything = False
                for i in range(len(data['text'])):
                    text = data['text'][i].strip()
                    confidence = int(data['conf'][i])
                    if text and confidence > 5:
                        x = data['left'][i]
                        y = data['top'][i]
                        print(f"   '{text}' - уверенность: {confidence}% - позиция: ({x}, {y})")
                        found_anything = True
                
                if not found_anything:
                    print("   ❌ Ничего не найдено")
                    
            except Exception as e:
                print(f"   ⚠️ Ошибка: {e}")
        
        return self.find_greater_than_symbol_fast()

    def click_arrow(self):
        """
        Клик по найденной стрелке с последующим убиранием мыши
        """
        if not self.arrow_position:
            print("❌ Позиция стрелки не определена")
            return False
        
        x, y = self.arrow_position
        print(f"🖱️ Кликаем по стрелке: ({x}, {y})")
        
        try:
            pyautogui.moveTo(x, y, duration=0.1)
            time.sleep(0.1)
            pyautogui.click()
            print("✅ Клик по стрелке выполнен!")
            
            # 🔥 ВАЖНО: Убираем мышь в сторону после клика!
            self.move_mouse_away_from_frame()
            
            time.sleep(2)  # Ждем открытия панели
            return True
        except Exception as e:
            print(f"❌ Ошибка клика по стрелке: {e}")
            return False

    def move_mouse_away_from_frame(self):
        """
        Убирает указатель мыши от области рамки чтобы не мешал определению
        """
        try:
            screen_width, screen_height = pyautogui.size()
            
            # 🔥 ПРОВЕРЯЕМ: правильные ли координаты?
            safe_x = screen_width - 100
            safe_y = screen_height - 100
            
            print(f"🖱️ Убираем мышь в безопасную зону: ({safe_x}, {safe_y})")
            pyautogui.moveTo(safe_x, safe_y, duration=0.2)
            
            time.sleep(0.5)  # Даем время на исчезновение курсора
            return True
            
        except Exception as e:
            print(f"⚠️ Не удалось убрать мышь: {e}")
            return False

    def find_avatar_frame_near_arrow(self):
        """
        Поиск серой рамки аватарки рядом с позицией стрелки (погрешность 100px)
        """
        print("🎯 ПОИСК СЕРОЙ РАМКИ РЯДОМ СО СТРЕЛКОЙ")
        
        if not self.arrow_position:
            print("❌ Позиция стрелки не определена, ищем по всей области")
            return self.find_avatar_frame_with_debug()
        
        arrow_x, arrow_y = self.arrow_position
        print(f"📍 Стрелка найдена в: ({arrow_x}, {arrow_y})")
        
        try:
            screen_width, screen_height = pyautogui.size()
            target_color = (100, 101, 105)  # HEX #646569
            color_tolerance = 20
            
            # 🔥 ОБЛАСТЬ ПОИСКА: вокруг стрелки с погрешностью 100px
            search_margin = 100
            search_region = (
                max(0, arrow_x - search_margin),
                max(0, arrow_y - search_margin),
                min(screen_width - (arrow_x - search_margin), search_margin * 2),
                min(screen_height - (arrow_y - search_margin), search_margin * 2)
            )
            
            print(f"🔍 Область поиска рамки вокруг стрелки: {search_region}")
            
            # Сохраняем скриншот области поиска
            search_screenshot = pyautogui.screenshot(region=search_region)
            #self.save_debug_screenshot(search_screenshot, "frame_search_near_arrow")
            
            screenshot = pyautogui.screenshot(region=search_region)
            
            if screenshot.mode != 'RGB':
                rgb_screenshot = screenshot.convert('RGB')
            else:
                rgb_screenshot = screenshot
            
            pixels = rgb_screenshot.load()
            width, height = rgb_screenshot.size
            
            # Ищем области целевого цвета
            gray_areas = []
            for y in range(height):
                for x in range(width):
                    current_color = pixels[x, y]
                    if (abs(current_color[0] - target_color[0]) <= color_tolerance and
                        abs(current_color[1] - target_color[1]) <= color_tolerance and
                        abs(current_color[2] - target_color[2]) <= color_tolerance):
                        gray_areas.append((x, y))
            
            if not gray_areas:
                print("❌ Серая рамка не найдена рядом со стрелкой")
                # Пробуем поискать во всей области
                return self.find_avatar_frame_with_debug()
            
            # Группируем в прямоугольники
            rectangles = self.group_areas_into_rectangles(gray_areas)
            
            # Сохраняем скриншот с найденными областями
            found_screenshot = screenshot.copy()
            from PIL import ImageDraw
            draw = ImageDraw.Draw(found_screenshot)
            
            for rect in rectangles:
                x, y, w, h = rect
                draw.rectangle([x, y, x+w, y+h], outline="green", width=2)
            
            # Отмечаем позицию стрелки на скриншоте
            arrow_rel_x = arrow_x - search_region[0]
            arrow_rel_y = arrow_y - search_region[1]
            draw.ellipse([arrow_rel_x-5, arrow_rel_y-5, arrow_rel_x+5, arrow_rel_y+5], 
                        outline="red", width=2)
            
            #self.save_debug_screenshot(found_screenshot, "frame_candidates_near_arrow")
            
            # Ищем подходящую рамку (квадратную)
            best_rectangle = None
            best_score = 0
            
            for rect in rectangles:
                x, y, w, h = rect
                
                # Критерии для рамки аватарки
                size_ok = 40 <= w <= 120 and 40 <= h <= 120
                square_ratio = min(w, h) / max(w, h)  # Коэффициент "квадратности"
                
                if size_ok and square_ratio > 0.7:  # Довольно квадратная
                    score = square_ratio * 100
                    if score > best_score:
                        best_score = score
                        best_rectangle = rect
            
            if best_rectangle:
                x, y, w, h = best_rectangle
                abs_x = x + search_region[0]
                abs_y = y + search_region[1]
                
                self.avatar_frame_position = (abs_x, abs_y)
                self.avatar_frame_size = (w, h)
                
                print(f"✅ Рамка аватарки найдена рядом со стрелкой!")
                print(f"📍 Позиция: ({abs_x}, {abs_y})")
                print(f"📏 Размер: {w}x{h} (квадратность: {best_score:.1f}%)")
                print(f"🎯 Расстояние от стрелки: {abs(arrow_x - abs_x)}px по X, {abs(arrow_y - abs_y)}px по Y")
                pause_handler.set_current_operation("Идёт игра, ожидаем красную рамку")
                # Сохраняем скриншот выбранной рамки
                frame_screenshot = pyautogui.screenshot(region=(abs_x, abs_y, w, h))
                #self.save_debug_screenshot(frame_screenshot, "selected_frame_near_arrow")
                
                return True
            
            print("❌ Подходящая квадратная рамка не найдена рядом со стрелкой")
            return self.find_avatar_frame_with_debug()
            
        except Exception as e:
            print(f"❌ Ошибка при поиске рамки рядом со стрелкой: {e}")
            return self.find_avatar_frame_with_debug()

    def find_avatar_frame_with_debug(self):
        """
        Поиск серой рамки аватарки по всей области (резервный метод)
        """
        print("🎯 ПОИСК СЕРОЙ РАМКИ ПО ВСЕЙ ОБЛАСТИ (РЕЗЕРВНЫЙ МЕТОД)")
        
        try:
            screen_width, screen_height = pyautogui.size()
            target_color = (100, 101, 105)  # HEX #646569
            color_tolerance = 20
            
            # Область поиска - левая часть экрана где обычно находится панель
            search_region = (
                0,
                int(screen_height * 0.1),
                int(screen_width * 0.35),
                int(screen_height * 0.6)
            )
            
            print(f"🔍 Резервный поиск по области: {search_region}")
            
            screenshot = pyautogui.screenshot(region=search_region)
            
            if screenshot.mode != 'RGB':
                rgb_screenshot = screenshot.convert('RGB')
            else:
                rgb_screenshot = screenshot
            
            pixels = rgb_screenshot.load()
            width, height = rgb_screenshot.size
            
            # Ищем области целевого цвета
            gray_areas = []
            for y in range(height):
                for x in range(width):
                    current_color = pixels[x, y]
                    if (abs(current_color[0] - target_color[0]) <= color_tolerance and
                        abs(current_color[1] - target_color[1]) <= color_tolerance and
                        abs(current_color[2] - target_color[2]) <= color_tolerance):
                        gray_areas.append((x, y))
            
            if not gray_areas:
                print("❌ Серая рамка не найдена")
                return False
            
            # Группируем в прямоугольники
            rectangles = self.group_areas_into_rectangles(gray_areas)
            
            # Ищем самую квадратную рамку подходящего размера
            best_rectangle = None
            best_score = 0
            
            for rect in rectangles:
                x, y, w, h = rect
                
                # Критерии для рамки аватарки
                size_ok = 40 <= w <= 120 and 40 <= h <= 120
                square_ratio = min(w, h) / max(w, h)
                
                if size_ok and square_ratio > 0.7:
                    score = square_ratio * 100
                    if score > best_score:
                        best_score = score
                        best_rectangle = rect
            
            if best_rectangle:
                x, y, w, h = best_rectangle
                abs_x = x + search_region[0]
                abs_y = y + search_region[1]
                
                self.avatar_frame_position = (abs_x, abs_y)
                self.avatar_frame_size = (w, h)
                
                print(f"✅ Рамка аватарки найдена резервным методом!")
                print(f"📍 Позиция: ({abs_x}, {abs_y})")
                print(f"📏 Размер: {w}x{h} (квадратность: {best_score:.1f}%)")
                pause_handler.set_current_operation("Идёт игра, ожидаем красную рамку")
                return True
            
            print("❌ Подходящая рамка не найдена резервным методом")
            return False
            
        except Exception as e:
            print(f"❌ Ошибка при резервном поиске рамки: {e}")
            return False

    def save_debug_screenshot(self, image, description):
        """
        Сохраняет скриншот для отладки с временной меткой и описанием
        """
        try:
            if not ENABLE_DEBUG_SCREENSHOTS:
                #print(f"📸 Скриншот отладки пропущен: {description} (отключено в конфиге)")  # Опционально
                return None
            self.debug_screenshot_count += 1
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"debug/debug_{timestamp}_{self.debug_screenshot_count:03d}_{description}.png"
            
            # Создаем папку debug если не существует
            import os
            os.makedirs("debug", exist_ok=True)
            
            image.save(filename)
            print(f"📸 Скриншот сохранен: {filename}")
            return filename
        except Exception as e:
            print(f"⚠️ Не удалось сохранить скриншот: {e}")
            return None

    def check_frame_color_with_info(self):
        """
        УПРОЩЕННАЯ проверка цвета рамки - только исправления для серого/красного
        """
        result = {
            'death_detected': False,
            'color_info': 'Не определён',
            'red_percentage': 0,
            'gray_percentage': 0,
            'screenshot_saved': False
        }
        
        if not self.avatar_frame_position:
            result['color_info'] = '❌ Позиция рамки не определена'
            return result
        
        try:
            x, y = self.avatar_frame_position
            w, h = self.avatar_frame_size
            
            # Область рамки
            region = (x, y, w, h)
            screenshot = pyautogui.screenshot(region=region)
            
            if screenshot.mode != 'RGB':
                rgb_screenshot = screenshot.convert('RGB')
            else:
                rgb_screenshot = screenshot
            
            pixels = rgb_screenshot.load()
            width, height = rgb_screenshot.size
            
            # 🔥 ПРОСТОЙ АНАЛИЗ ЦВЕТА - на основе реальных данных
            red_count = 0
            gray_count = 0
            total_pixels = 0
            
            # Анализируем только границы (1 пиксель от края)
            for x_pos in range(width):
                # Верхняя граница
                r, g, b = pixels[x_pos, 0]
                total_pixels += 1
                if self._is_red_color(r, g, b):
                    red_count += 1
                elif self._is_gray_color(r, g, b):
                    gray_count += 1
                
                # Нижняя граница
                r, g, b = pixels[x_pos, height-1]
                total_pixels += 1
                if self._is_red_color(r, g, b):
                    red_count += 1
                elif self._is_gray_color(r, g, b):
                    gray_count += 1
            
            for y_pos in range(1, height-1):  # Исключаем углы чтобы не дублировать
                # Левая граница
                r, g, b = pixels[0, y_pos]
                total_pixels += 1
                if self._is_red_color(r, g, b):
                    red_count += 1
                elif self._is_gray_color(r, g, b):
                    gray_count += 1
                
                # Правая граница
                r, g, b = pixels[width-1, y_pos]
                total_pixels += 1
                if self._is_red_color(r, g, b):
                    red_count += 1
                elif self._is_gray_color(r, g, b):
                    gray_count += 1
            
            # Рассчитываем проценты
            if total_pixels > 0:
                red_ratio = red_count / total_pixels
                gray_ratio = gray_count / total_pixels
            else:
                red_ratio = 0
                gray_ratio = 0
                
            result['red_percentage'] = red_ratio * 100
            result['gray_percentage'] = gray_ratio * 100
            
            print(f"🔍 Анализ цвета: красных {red_count}/{total_pixels} ({result['red_percentage']:.1f}%), "
                f"серых {gray_count}/{total_pixels} ({result['gray_percentage']:.1f}%)")
            
            # 🔥 ПРОСТОЕ ОПРЕДЕЛЕНИЕ ЦВЕТА
            if red_ratio > 0.3:  # 30% красных
                current_color = "red"
                result['death_detected'] = True
                result['color_info'] = f"🔴 КРАСНЫЙ ({result['red_percentage']:.1f}%) - СМЕРТЬ ХОСТА"
                # Запись статистики смерти хоста по красной рамке

                try:
                    from statistics import stats
                    stats.record_host_death('red_frame', 
                        f"Красная рамка обнаружена: {result['red_percentage']:.1f}% красных пикселей")
                    print(f"📊 СТАТИСТИКА: Смерть хоста (красная рамка) записана!")
                except Exception as e:
                    print(f"⚠️ Ошибка записи статистики смерти: {e}")
                    
            elif gray_ratio > 0.6:  # 60% серых
                current_color = "gray"
                result['color_info'] = f"⚫ СЕРЫЙ ({result['gray_percentage']:.1f}%) - НОРМА"
            else:
                current_color = "unknown"
                result['color_info'] = f"❓ СМЕШАННЫЙ (красный: {result['red_percentage']:.1f}%, серый: {result['gray_percentage']:.1f}%)"
            
            # Сохраняем скриншот при изменении цвета
            if self.last_frame_color != current_color:
                print(f"🎨 ИЗМЕНЕНИЕ ЦВЕТА РАМКИ: {self.last_frame_color} → {current_color}")
                self.last_frame_color = current_color
            
            return result
            
        except Exception as e:
            result['color_info'] = f'❌ Ошибка проверки: {e}'
            print(f"⚠️ Ошибка при анализе цвета: {e}")
            return result

    def _is_red_color(self, r, g, b):
        """Простая проверка красного цвета"""
        return r > 160 and g < 110 and b < 110

    def _is_gray_color(self, r, g, b):
        """Простая проверка серого цвета на основе реальных данных (100, 101, 105)"""
        return (90 <= r <= 110 and 
                90 <= g <= 110 and 
                90 <= b <= 110 and
                abs(r - g) <= 10 and 
                abs(r - b) <= 10)
    def create_color_analysis_debug_image(self, original_image, border_thickness):
        """
        Создает отладочное изображение с выделением цветов
        """
        try:
            from PIL import ImageDraw
            
            debug_image = original_image.copy()
            draw = ImageDraw.Draw(debug_image)
            width, height = debug_image.size
            
            # Анализируем пиксели и рисуем их цвет
            for y in range(height):
                for x in range(width):
                    r, g, b = debug_image.getpixel((x, y))
                    
                    # Определяем цвет пикселя
                    if (r > 180 and g < 120 and b < 120 and r > g * 1.5 and r > b * 1.5):
                        # Красный пиксель - рисуем красную точку
                        draw.rectangle([x, y, x, y], fill="red")
                    elif (80 <= r <= 120 and 80 <= g <= 120 and 80 <= b <= 120 and
                        abs(r - g) < 20 and abs(r - b) < 20 and abs(g - b) < 20):
                        # Серый пиксель - рисуем серую точку
                        draw.rectangle([x, y, x, y], fill="gray")
            
            # Рисуем границы области анализа
            draw.rectangle([0, 0, width-1, height-1], outline="yellow", width=1)
            draw.rectangle([border_thickness, border_thickness, 
                        width-border_thickness-1, height-border_thickness-1], 
                        outline="blue", width=1)
            
            return debug_image
            
        except Exception as e:
            print(f"⚠️ Ошибка при создании отладочного изображения: {e}")
            return original_image
        
    def test_color_detection(self):
        """
        Тестирует определение цветов на текущей рамке
        """
        print("🎨 ТЕСТИРОВАНИЕ ОПРЕДЕЛЕНИЯ ЦВЕТОВ")
        
        if not self.avatar_frame_position:
            print("❌ Рамка не найдена")
            return
        
        x, y = self.avatar_frame_position
        w, h = self.avatar_frame_size
        
        # Делаем скриншот рамки
        screenshot = pyautogui.screenshot(region=(x, y, w, h))
        #self.save_debug_screenshot(screenshot, "color_test_original")
        
        rgb_screenshot = screenshot.convert('RGB')
        pixels = rgb_screenshot.load()
        width, height = rgb_screenshot.size
        
        print(f"📏 Размер рамки: {width}x{height}")
        print("🔍 Анализ пикселей по углам и центру:")
        
        # Анализируем ключевые точки
        test_points = [
            (0, 0, "левый верхний"),
            (width-1, 0, "правый верхний"),
            (0, height-1, "левый нижний"),
            (width-1, height-1, "правый нижний"),
            (width//2, height//2, "центр")
        ]
        
        for x_pos, y_pos, description in test_points:
            r, g, b = pixels[x_pos, y_pos]
            print(f"  📍 {description} ({x_pos}, {y_pos}): RGB({r}, {g}, {b})")
            
            # Определяем цвет
            if (r > 180 and g < 120 and b < 120 and r > g * 1.5 and r > b * 1.5):
                print(f"    🔴 КРАСНЫЙ (R доминирует)")
            elif (80 <= r <= 120 and 80 <= g <= 120 and 80 <= b <= 120 and
                abs(r - g) < 20 and abs(r - b) < 20 and abs(g - b) < 20):
                print(f"    ⚫ СЕРЫЙ (все каналы примерно равны)")
            else:
                print(f"    ❓ ДРУГОЙ (R:{r}, G:{g}, B:{b})")
        
        # Тестируем границы
        print("\n🔍 Анализ границ:")
        border_samples = 5
        
        for border in ['top', 'bottom', 'left', 'right']:
            print(f"  📍 {border} граница:")
            
            if border == 'top':
                for i in range(border_samples):
                    x_sample = i * width // border_samples
                    r, g, b = pixels[x_sample, 0]
                    print(f"    ({x_sample}, 0): RGB({r}, {g}, {b})")
            
            elif border == 'bottom':
                for i in range(border_samples):
                    x_sample = i * width // border_samples
                    r, g, b = pixels[x_sample, height-1]
                    print(f"    ({x_sample}, {height-1}): RGB({r}, {g}, {b})")
            
            elif border == 'left':
                for i in range(border_samples):
                    y_sample = i * height // border_samples
                    r, g, b = pixels[0, y_sample]
                    print(f"    (0, {y_sample}): RGB({r}, {g}, {b})")
            
            elif border == 'right':
                for i in range(border_samples):
                    y_sample = i * height // border_samples
                    r, g, b = pixels[width-1, y_sample]
                    print(f"    ({width-1}, {y_sample}): RGB({r}, {g}, {b})")

    # Обновляем основной метод
    def find_avatar_frame(self):
        """
        Основной метод поиска рамки - сначала рядом со стрелкой, потом везде
        """
        return self.find_avatar_frame_near_arrow()

    # Остальные методы остаются без изменений
    def group_areas_into_rectangles(self, areas, max_gap=5):
        """
        Группирует пиксели в прямоугольники
        """
        rectangles = []
        used_areas = set()
        
        for area in areas:
            if area in used_areas:
                continue
                
            x, y = area
            min_x, max_x = x, x
            min_y, max_y = y, y
            used_areas.add(area)
            
            changed = True
            while changed:
                changed = False
                for check_x in range(min_x - max_gap, max_x + max_gap + 1):
                    for check_y in range(min_y - max_gap, max_y + max_gap + 1):
                        if (check_x, check_y) in areas and (check_x, check_y) not in used_areas:
                            used_areas.add((check_x, check_y))
                            min_x = min(min_x, check_x)
                            max_x = max(max_x, check_x)
                            min_y = min(min_y, check_y)
                            max_y = max(max_y, check_y)
                            changed = True
            
            width = max_x - min_x + 1
            height = max_y - min_y + 1
            
            if width >= 10 and height >= 10:
                rectangles.append((min_x, min_y, width, height))
        
        return rectangles
        """
        Группирует пиксели в прямоугольники
        """
        rectangles = []
        used_areas = set()
        
        for area in areas:
            if area in used_areas:
                continue
                
            x, y = area
            min_x, max_x = x, x
            min_y, max_y = y, y
            used_areas.add(area)
            
            changed = True
            while changed:
                changed = False
                for check_x in range(min_x - max_gap, max_x + max_gap + 1):
                    for check_y in range(min_y - max_gap, max_y + max_gap + 1):
                        if (check_x, check_y) in areas and (check_x, check_y) not in used_areas:
                            used_areas.add((check_x, check_y))
                            min_x = min(min_x, check_x)
                            max_x = max(max_x, check_x)
                            min_y = min(min_y, check_y)
                            max_y = max(max_y, check_y)
                            changed = True
            
            width = max_x - min_x + 1
            height = max_y - min_y + 1
            
            if width >= 10 and height >= 10:
                rectangles.append((min_x, min_y, width, height))
        
        return rectangles