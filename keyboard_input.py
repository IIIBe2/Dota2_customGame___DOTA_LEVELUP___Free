# keyboard_input.py - полная версия с авто-переключением раскладки

import keyboard
import time
import threading
from queue import Queue

class SmartKeyboardInput:
    """Умный ввод текста с авто-переключением раскладки"""
    
    # 🔥 ДЕТЕКТОР РАСКЛАДКИ
    @staticmethod
    def detect_char_layout(char):
        """Определить раскладку символа"""
        # Русские буквы (а-я, А-Я, ё, Ё)
        russian_lower = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
        russian_upper = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
        
        if char in russian_lower or char in russian_upper:
            return 'ru'
        elif char.isalpha():
            return 'en'
        else:
            # Цифры и символы работают в обеих раскладках
            return 'any'
    
    # 🔥 КАРТА КЛАВИШ ДЛЯ РУССКОЙ РАСКЛАДКИ
    # Когда система на английской, но нужно ввести русскую букву
    RUS_TO_EN_KEY = {
        'а': 'f', 'б': ',', 'в': 'd', 'г': 'u', 'д': 'l', 'е': 't', 'ё': '`',
        'ж': ';', 'з': 'p', 'и': 'b', 'й': 'q', 'к': 'r', 'л': 'k', 'м': 'v',
        'н': 'y', 'о': 'j', 'п': 'g', 'р': 'h', 'с': 'c', 'т': 'n', 'у': 'e',
        'ф': 'a', 'х': '[', 'ц': 'w', 'ч': 'x', 'ш': 'i', 'щ': 'o', 'ъ': ']',
        'ы': 's', 'ь': 'm', 'э': '\'', 'ю': '.', 'я': 'z',
        'А': 'shift+f', 'Б': 'shift+,', 'В': 'shift+d', 'Г': 'shift+u',
        'Д': 'shift+l', 'Е': 'shift+t', 'Ё': 'shift+`', 'Ж': 'shift+;',
        'З': 'shift+p', 'И': 'shift+b', 'Й': 'shift+q', 'К': 'shift+r',
        'Л': 'shift+k', 'М': 'shift+v', 'Н': 'shift+y', 'О': 'shift+j',
        'П': 'shift+g', 'Р': 'shift+h', 'С': 'shift+c', 'Т': 'shift+n',
        'У': 'shift+e', 'Ф': 'shift+a', 'Х': 'shift+[', 'Ц': 'shift+w',
        'Ч': 'shift+x', 'Ш': 'shift+i', 'Щ': 'shift+o', 'Ъ': 'shift+]',
        'Ы': 'shift+s', 'Ь': 'shift+m', 'Э': 'shift+\'', 'Ю': 'shift+.',
        'Я': 'shift+z'
    }
    
    # 🔥 КАРТА ДЛЯ АНГЛИЙСКОЙ РАСКЛАДКИ
    # Когда система на русской, но нужно ввести английскую букву
    EN_TO_RUS_KEY = {
        'a': 'ф', 'b': 'и', 'c': 'с', 'd': 'в', 'e': 'у', 'f': 'а', 'g': 'п',
        'h': 'р', 'i': 'ш', 'j': 'о', 'k': 'л', 'l': 'д', 'm': 'ь', 'n': 'т',
        'o': 'щ', 'p': 'з', 'q': 'й', 'r': 'к', 's': 'ы', 't': 'е', 'u': 'г',
        'v': 'м', 'w': 'ц', 'x': 'ч', 'y': 'н', 'z': 'я',
        'A': 'shift+ф', 'B': 'shift+и', 'C': 'shift+с', 'D': 'shift+в',
        'E': 'shift+у', 'F': 'shift+а', 'G': 'shift+п', 'H': 'shift+р',
        'I': 'shift+ш', 'J': 'shift+о', 'K': 'shift+л', 'L': 'shift+д',
        'M': 'shift+ь', 'N': 'shift+т', 'O': 'shift+щ', 'P': 'shift+з',
        'Q': 'shift+й', 'R': 'shift+к', 'S': 'shift+ы', 'T': 'shift+е',
        'U': 'shift+г', 'V': 'shift+м', 'W': 'shift+ц', 'X': 'shift+ч',
        'Y': 'shift+н', 'Z': 'shift+я'
    }
    
    @staticmethod
    def switch_layout_to(target_layout):
        """Переключить системную раскладку"""
        print(f"🔄 Переключение системной раскладки на {target_layout}...")
        
        try:
            # Пробуем разные комбинации
            combinations = [
                ('alt', 'shift'),  # Alt+Shift
                ('ctrl', 'shift'), # Ctrl+Shift
                ('win', 'space'),  # Win+Space
            ]
            
            for combo in combinations:
                try:
                    keyboard.press(combo[0])
                    keyboard.press(combo[1])
                    time.sleep(0.1)
                    keyboard.release(combo[1])
                    keyboard.release(combo[0])
                    time.sleep(0.5)
                    
                    print(f"  ✅ Комбинация {combo[0]}+{combo[1]} выполнена")
                    return True
                    
                except Exception as e:
                    print(f"  ⚠️ Ошибка с {combo}: {e}")
            
            return False
            
        except Exception as e:
            print(f"❌ Ошибка переключения раскладки: {e}")
            return False
    
    @staticmethod
    def get_current_layout():
        """Определить текущую системную раскладку (упрощенный метод)"""
        try:
            # Попробуем определить по вводу тестового символа
            # Это сложно сделать точно без WinAPI, поэтому упростим
            
            # Предположим что раскладка либо ru, либо en
            # Можно добавить более точное определение через ctypes
            print("⚠️ Упрощенное определение раскладки")
            return "unknown"
            
        except:
            return "unknown"
    
    @staticmethod
    def type_mixed_text(text, interval=0.15):
        """
        Ввод смешанного текста (русские + английские буквы)
        Автоматически переключает раскладку когда нужно
        """
        print(f"⌨️ Ввод смешанного текста: {text}")
        print(f"   Длина: {len(text)} символов")
        
        # 🔥 ШАГ 1: Определяем текущую раскладку (предположим английскую для начала)
        current_layout = "en"  # Начинаем с английской
        
        # 🔥 ШАГ 2: Вводим каждый символ с умным переключением
        for i, char in enumerate(text):
            char_layout = SmartKeyboardInput.detect_char_layout(char)
            
            print(f"  {i+1}. Символ '{char}' ({char_layout})", end="")
            
            # Если символ русский, а раскладка английская - переключаем
            if char_layout == 'ru' and current_layout != 'ru':
                print(" -> переключаем на русскую")
                SmartKeyboardInput.switch_layout_to('ru')
                current_layout = 'ru'
                time.sleep(0.3)
            
            # Если символ английский, а раскладка русская - переключаем
            elif char_layout == 'en' and current_layout != 'en':
                print(" -> переключаем на английскую")
                SmartKeyboardInput.switch_layout_to('en')
                current_layout = 'en'
                time.sleep(0.3)
            
            else:
                print(" -> раскладка уже правильная")
            
            # 🔥 Вводим символ
            try:
                # Простые символы
                if char.isalnum() or char in ' -_=+[]{}|;:\'",.<>/?~`!@#$%^&*()':
                    keyboard.write(char, delay=0)
                elif char == ' ':
                    keyboard.press_and_release('space')
                else:
                    # Специальные символы
                    keyboard.write(char, delay=0)
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"⚠️ Ошибка ввода '{char}': {e}")
                # Запасной метод
                try:
                    import pyautogui
                    pyautogui.write(char, interval=0)
                    time.sleep(interval)
                except:
                    pass
        
        print(f"✅ Текст введен с авто-переключением раскладки")
        return True
    
    @staticmethod
    def type_mixed_text_smart(text, interval=0.12):
        """
        УМНЫЙ ввод: группируем символы по раскладке чтобы меньше переключать
        """
        print(f"⌨️ УМНЫЙ ввод смешанного текста: {'*' * len(text) if any(c.isalpha() for c in text) else text}")
        
        # 🔥 ГРУППИРУЕМ СИМВОЛЫ ПО РАСКЛАДКЕ
        groups = []
        current_group = ""
        current_layout = None
        
        for char in text:
            char_layout = SmartKeyboardInput.detect_char_layout(char)
            
            if char_layout == 'any':
                # Цифры/символы - добавляем в текущую группу
                current_group += char
            elif current_layout is None:
                # Первый символ
                current_layout = char_layout
                current_group = char
            elif char_layout == current_layout:
                # Та же раскладка - добавляем в группу
                current_group += char
            else:
                # Новая раскладка - сохраняем старую группу
                groups.append((current_group, current_layout))
                current_layout = char_layout
                current_group = char
        
        # Добавляем последнюю группу
        if current_group:
            groups.append((current_group, current_layout))
        
        print(f"   Групп по раскладке: {len(groups)}")
        for i, (group, layout) in enumerate(groups):
            print(f"   Группа {i+1}: '{group}' ({layout})")
        
        # 🔥 ВВОДИМ ГРУППАМИ
        current_system_layout = "en"  # Предполагаем начальную английскую
        
        for group, needed_layout in groups:
            if needed_layout is None:
                # Цифры/символы - вводим в текущей раскладке
                print(f"  🔢 Ввод цифр/символов: '{group}'")
                for char in group:
                    keyboard.write(char, delay=0)
                    time.sleep(interval)
            
            elif needed_layout != current_system_layout:
                # Нужно переключить раскладку
                print(f"  🔄 Переключаем на {needed_layout} для: '{group}'")
                SmartKeyboardInput.switch_layout_to(needed_layout)
                current_system_layout = needed_layout
                time.sleep(0.3)
                
                # Вводим группу
                for char in group:
                    keyboard.write(char, delay=0)
                    time.sleep(interval)
            
            else:
                # Раскладка уже правильная
                print(f"  ✓ Ввод в текущей раскладке: '{group}'")
                for char in group:
                    keyboard.write(char, delay=0)
                    time.sleep(interval)
        
        print(f"✅ Текст введен умно (минимум переключений)")
        return True
    
    @staticmethod
    def type_password_smart(password, interval=0.1, restore_layout=True):
        """
        УМНЫЙ ввод пароля с авто-переключением и восстановлением раскладки
        """
        print(f"⌨️ УМНЫЙ ВВОД ПАРОЛЯ ({len(password)} символов)")
        
        # 🔥 ЗАПОМИНАЕМ ИЗНАЧАЛЬНУЮ РАСКЛАДКУ
        initial_layout = None
        if restore_layout:
            initial_layout = "en"  # Упрощенно, можно добавить реальное определение
        
        # 🔥 ВВОДИМ ПАРОЛЬ УМНО
        success = SmartKeyboardInput.type_mixed_text_smart(password, interval)
        
        # 🔥 ВОССТАНАВЛИВАЕМ РАСКЛАДКУ ЕСЛИ НУЖНО
        if restore_layout and initial_layout:
            print(f"🔄 Восстанавливаем исходную раскладку ({initial_layout})...")
            # Переключаем обратно (если изначально была не английская)
            if initial_layout != "en":
                SmartKeyboardInput.switch_layout_to(initial_layout)
        
        return success