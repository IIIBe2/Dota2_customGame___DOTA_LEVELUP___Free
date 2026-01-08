# pet_manager.py
import json
import os
import time
import pyautogui
from config import PET_CONFIG_FILE
from pause_handler import pause_handler

class PetManager:
    def __init__(self, logger):
        self.logger = logger
        self.config_file = PET_CONFIG_FILE
        self.pets = self.load_pets()
        self.current_pet = None
        
    def load_pets(self):
        """Загрузка конфигурации питомцев из файла"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    pets = json.load(f)
                    print(f"✅ Конфигурация питомцев загружена: {len(pets)} питомцев")
                    
                    # 🔥 ДОБАВЛЯЕМ ПАРАМЕТРЫ ПО УМОЛЧАНИЮ ДЛЯ СОВМЕСТИМОСТИ
                    for pet_id, pet_data in pets.items():
                        if 'click_delay' not in pet_data:
                            pet_data['click_delay'] = 2.0  # 🔥 УВЕЛИЧИВАЕМ ЗАДЕРЖКУ ДО 2 СЕКУНД
                        if 'infinite_triggers' not in pet_data:
                            pet_data['infinite_triggers'] = []
                    
                    return pets
        except Exception as e:
            print(f"⚠️ Ошибка загрузки конфигурации питомцев: {e}")
        
        # Конфигурация по умолчанию
        default_pets = {
            "pet1": {
                "name": "Питомец 1",
                "click_delay": 2.0,  # 🔥 УВЕЛИЧИВАЕМ ДО 2 СЕКУНД
                "infinite_triggers": [],  # 🔥 ТРИГГЕРЫ ДЛЯ БЕСКОНЕЧКИ
                "clicks": [
                    {"x": 100, "y": 100, "description": "Клик 1"},
                    {"x": 200, "y": 100, "description": "Клик 2"},
                    {"x": 300, "y": 100, "description": "Клик 3"},
                    {"x": 400, "y": 100, "description": "Клик 4"},
                    {"x": 500, "y": 100, "description": "Клик 5"}
                ]
            }
        }
        return default_pets
    
    def save_pets(self):
        """Сохранение конфигурации питомцев"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.pets, f, indent=2, ensure_ascii=False)
            print(f"✅ Конфигурация питомцев сохранена")
            return True
        except Exception as e:
            print(f"⚠️ Ошибка сохранения конфигурации питомцев: {e}")
            return False
    
    def add_pet(self, pet_id, pet_name):
        """Добавление нового питомца"""
        if pet_id in self.pets:
            return False, f"Питомец с ID '{pet_id}' уже существует"
        
        self.pets[pet_id] = {
            "name": pet_name,
            "click_delay": 2.0,  # 🔥 УВЕЛИЧИВАЕМ ДО 2 СЕКУНД ПО УМОЛЧАНИЮ
            "infinite_triggers": [],  # 🔥 ТРИГГЕРЫ ДЛЯ БЕСКОНЕЧКИ
            "clicks": []
        }
        self.save_pets()
        return True, f"Питомец '{pet_name}' добавлен"
    
    def update_pet_settings(self, pet_id, settings):
        """Обновление настроек питомца"""
        if pet_id not in self.pets:
            return False, f"Питомец с ID '{pet_id}' не найден"
        
        # Обновляем настройки
        for key, value in settings.items():
            self.pets[pet_id][key] = value
        
        self.save_pets()
        return True, f"Настройки питомца обновлены"
    
    def add_infinite_trigger(self, pet_id, cycles_count, enabled=True):
        """Добавление триггера переключения при достижении определенного количества циклов бесконечки"""
        if pet_id not in self.pets:
            return False, f"Питомец с ID '{pet_id}' не найден"
        
        # Проверяем, не существует ли уже такой триггер
        for trigger in self.pets[pet_id].get('infinite_triggers', []):
            if trigger.get('cycles') == cycles_count:
                return False, f"Триггер для {cycles_count} циклов уже существует"
        
        # Добавляем триггер
        trigger = {
            "cycles": cycles_count,
            "enabled": enabled
        }
        
        if 'infinite_triggers' not in self.pets[pet_id]:
            self.pets[pet_id]['infinite_triggers'] = []
        
        self.pets[pet_id]['infinite_triggers'].append(trigger)
        
        # Сортируем триггеры по количеству циклов
        self.pets[pet_id]['infinite_triggers'].sort(key=lambda x: x['cycles'])
        
        self.save_pets()
        return True, f"Триггер добавлен: переключение при {cycles_count} циклах бесконечки"
    
    def remove_infinite_trigger(self, pet_id, cycles_count):
        """Удаление триггера"""
        if pet_id not in self.pets:
            return False, f"Питомец с ID '{pet_id}' не найден"
        
        if 'infinite_triggers' not in self.pets[pet_id]:
            return False, f"У питомца нет триггеров"
        
        # Удаляем триггер
        initial_count = len(self.pets[pet_id]['infinite_triggers'])
        self.pets[pet_id]['infinite_triggers'] = [
            t for t in self.pets[pet_id]['infinite_triggers']
            if t.get('cycles') != cycles_count
        ]
        
        if len(self.pets[pet_id]['infinite_triggers']) < initial_count:
            self.save_pets()
            return True, f"Триггер для {cycles_count} циклов удален"
        else:
            return False, f"Триггер для {cycles_count} циклов не найден"
    
    # AFK_lobby.py - метод check_infinite_triggers

    def reload_pets_config(self):
        """Принудительная перезагрузка конфигурации питомцев из файла"""
        old_count = len(self.pets)
        self.pets = self.load_pets()
        new_count = len(self.pets)
        print(f"🔄 Конфигурация питомцев перезагружена: {old_count} -> {new_count} питомцев")
        return new_count

    def deactivate_trigger(self, pet_id, cycles):
        """Деактивация триггера после срабатывания"""
        if pet_id not in self.pets:
            return False, f"Питомец с ID '{pet_id}' не найден"
        
        if 'infinite_triggers' not in self.pets[pet_id]:
            return False, f"У питомца нет триггеров"
        
        # Находим и деактивируем триггер
        trigger_found = False
        for trigger in self.pets[pet_id]['infinite_triggers']:
            if trigger.get('cycles') == cycles:
                trigger['enabled'] = False
                trigger_found = True
                break
        
        if trigger_found:
            # 🔥 ГАРАНТИРУЕМ СОХРАНЕНИЕ И СИНХРОНИЗАЦИЮ
            success = self.save_pets()
            if success:
                # 🔥 ПЕРЕЗАГРУЖАЕМ КОНФИГУРАЦИЮ ИЗ ФАЙЛА
                self.pets = self.load_pets()
                return True, f"Триггер для {cycles} циклов деактивирован"
            else:
                return False, "Ошибка сохранения триггера"
        
        return False, f"Триггер для {cycles} циклов не найден"

    def check_infinite_triggers(self, current_cycles):
        """
        Проверка триггеров бесконечки и возврат списка сработавших триггеров
        Только для АКТИВНЫХ триггеров
        """
        triggered_pets = []
        
        # Проверяем всех питомцев на наличие сработавших триггеров
        for pet_id, pet_data in self.pets.items():
            triggers = pet_data.get('infinite_triggers', [])
            
            for trigger in triggers:
                cycles_needed = trigger.get('cycles', 0)
                enabled = trigger.get('enabled', True)
                
                # 🔥 ПРОВЕРЯЕМ ТОЛЬКО АКТИВНЫЕ ТРИГГЕРЫ
                if enabled and current_cycles >= cycles_needed:
                    triggered_pets.append({
                        'pet_id': pet_id,
                        'pet_name': pet_data.get('name', 'Неизвестный'),
                        'trigger_cycles': cycles_needed,
                        'current_cycles': current_cycles
                    })
        
        # Сортируем по количеству циклов (от меньшего к большему)
        triggered_pets.sort(key=lambda x: x['trigger_cycles'])
        
        return triggered_pets
    
    def switch_to_pet_with_delay(self, pet_id, delay=None):
        """Переключение на питомца с увеличенной задержкой между кликами"""
        if pet_id not in self.pets:
            return False, f"Питомец с ID '{pet_id}' не найден"
        
        pet = self.pets[pet_id]
        clicks = pet.get("clicks", [])
        
        if not clicks:
            return False, f"У питомца '{pet['name']}' нет настроенных кликов"
        
        # 🔥 ИСПОЛЬЗУЕМ НАСТРАИВАЕМУЮ ЗАДЕРЖКУ ИЛИ ПО УМОЛЧАНИЮ
        click_delay = delay if delay is not None else pet.get('click_delay', 2.0)
        
        print(f"🐾 Переключение на питомца: {pet['name']}")
        print(f"🔢 Количество кликов: {len(clicks)}")
        print(f"⏱ Задержка между кликами: {click_delay} сек")
        
        try:
            for i, click in enumerate(clicks, 1):
                x = click.get("x", 0)
                y = click.get("y", 0)
                description = click.get("description", f"Клик {i}")
                
                print(f"  {i}. {description}: ({x}, {y}) - ждем {click_delay} сек")
                
                pyautogui.moveTo(x, y, duration=0.2)
                time.sleep(0.1)
                pyautogui.click()
                time.sleep(1)
                # 🔥 ДЕЛАЕМ СКРИНШОТ НА 2-ОМ ШАГЕ
                if i == 2:
                    print(f"📸 Делаем скриншот после 2-го шага...")
                    screenshot_success = self.take_step_screenshot(pet_id, i, pet['name'])
                    if screenshot_success:
                        print(f"✅ Скриншот после 2-го шага сделан и отправлен")
                    else:
                        print(f"⚠️ Не удалось сделать скриншот")
                        
                # 🔥 ДЕЛАЕМ СКРИНШОТ НА 4-ОМ ШАГЕ
                if i == 4:
                    print(f"📸 Делаем скриншот после 4-го шага...")
                    screenshot_success = self.take_step_screenshot(pet_id, i, pet['name'])
                    if screenshot_success:
                        print(f"✅ Скриншот после 4-го шага сделан и отправлен")
                    else:
                        print(f"⚠️ Не удалось сделать скриншот")

                # 🔥 УВЕЛИЧИВАЕМ ЗАДЕРЖКУ МЕЖДУ КЛИКАМИ
                if i < len(clicks):  # Не ждем после последнего клика
                    time.sleep(click_delay)
            
            self.current_pet = pet_id
            print(f"✅ Успешно переключились на питомца '{pet['name']}'")
            return True, f"Переключились на питомца '{pet['name']}'"
            
        except Exception as e:
            print(f"❌ Ошибка при переключении питомца: {e}")
            return False, f"Ошибка при переключении: {str(e)}"
    
    def take_step_screenshot(self, pet_id, step_number, pet_name):
        """Сделать скриншот на определенном шаге и отправить в Telegram"""
        try:
            import pyautogui
            from PIL import Image
            import io
            import datetime
            import os
            
            # Делаем скриншот
            screenshot = pyautogui.screenshot()
            
            # Создаем папку для скриншотов шагов если нет
            screenshots_dir = "screenshots/pet_steps"
            os.makedirs(screenshots_dir, exist_ok=True)
            
            # Сохраняем файл с временной меткой
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{screenshots_dir}/pet_{pet_id}_step_{step_number}_{timestamp}.png"
            screenshot.save(filename)
            
            # Получаем информацию о скриншоте
            screen_width, screen_height = pyautogui.size()
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            
            # 🔥 ОТПРАВЛЯЕМ В TELEGRAM
            try:
                from telegram_bot import get_bot_manager
                bot_manager = get_bot_manager()
                
                if bot_manager and hasattr(bot_manager, 'bot'):
                    from config import TELEGRAM_ADMIN_IDS
                    
                    if TELEGRAM_ADMIN_IDS:
                        chat_id = TELEGRAM_ADMIN_IDS[0]
                        
                        with open(filename, 'rb') as photo:
                            caption = (
                                f"📸 *Скриншот переключения питомца*\n\n"
                                f"🐾 *Питомец:* {pet_name}\n"
                                f"🔢 *Шаг:* {step_number}/5\n"
                                f"🕐 *Время:* {current_time}\n"
                                f"📏 *Разрешение:* {screen_width}x{screen_height}\n"
                                f"💾 *Размер файла:* {os.path.getsize(filename) // 1024} KB\n"
                                f"📁 *Путь:* `{filename}`"
                            )
                            
                            bot_manager.bot.send_photo(
                                chat_id,
                                photo,
                                caption=caption,
                                parse_mode='Markdown'
                            )
                        
                        print(f"✅ Скриншот шага {step_number} отправлен в Telegram")
                        return True
                        
            except Exception as e:
                print(f"⚠️ Не удалось отправить скриншот в Telegram: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка при создании скриншота: {str(e)}")
            return False

    def switch_to_pet(self, pet_id):
        """Стандартное переключение (для обратной совместимости)"""
        return self.switch_to_pet_with_delay(pet_id, delay=2.0)  # 🔥 УВЕЛИЧИВАЕМ ДО 2 СЕКУНД
    
    def execute_triggered_switch(self, pet_id, current_cycles, trigger_cycles):
        """Выполнение переключения по триггеру с логированием"""
        if pet_id not in self.pets:
            return False, f"Питомец {pet_id} не найден"
        
        pet = self.pets[pet_id]
        pet_name = pet.get('name', 'Неизвестный')
        
        print(f"\n" + "="*50)
        print(f"🎯 ВЫПОЛНЯЕМ ПЕРЕКЛЮЧЕНИЕ ПО ТРИГГЕРУ!")
        print(f"   Питомец: {pet_name}")
        print(f"   Триггер: {trigger_cycles} циклов")
        print(f"   Текущие: {current_cycles} циклов")
        print(f"   Кликов: {len(pet.get('clicks', []))}/5")
        print(f"   Задержка: {pet.get('click_delay', 2.0)} сек")
        print("="*50)
        
        # 🔥 ВЫПОЛНЯЕМ ПЕРЕКЛЮЧЕНИЕ С НАСТРОЕННОЙ ЗАДЕРЖКОЙ
        success, message = self.switch_to_pet_with_delay(pet_id)
        
        if success:
            # 🔥 ДЕАКТИВИРУЕМ ТРИГГЕР ПОСЛЕ УСПЕШНОГО СРАБАТЫВАНИЯ
            self.deactivate_trigger(pet_id, trigger_cycles)
            print(f"✅ Триггер для {trigger_cycles} циклов деактивирован")
            
            print(f"\n✅ ПЕРЕКЛЮЧЕНИЕ ВЫПОЛНЕНО УСПЕШНО!")
            print(f"   {message}")
        else:
            print(f"\n❌ ОШИБКА ПЕРЕКЛЮЧЕНИЯ!")
            print(f"   {message}")
        
        return success, message
    
    def get_pet_list(self):
        """Получить список всех питомцев"""
        return self.pets
    
    def get_pet_details(self, pet_id):
        """Получить детальную информацию о питомце"""
        if pet_id not in self.pets:
            return None
        
        pet = self.pets[pet_id].copy()
        
        # Добавляем информацию о триггерах
        pet['triggers_count'] = len(pet.get('infinite_triggers', []))
        pet['clicks_count'] = len(pet.get('clicks', []))
        
        return pet
    
    def set_click_delay(self, pet_id, delay):
        """Установка задержки между кликами для питомца"""
        if pet_id not in self.pets:
            return False, f"Питомец с ID '{pet_id}' не найден"
        
        if delay < 0.1 or delay > 10:
            return False, f"Задержка должна быть между 0.1 и 10 секундами"
        
        self.pets[pet_id]['click_delay'] = float(delay)
        self.save_pets()
        return True, f"Задержка установлена: {delay} сек"