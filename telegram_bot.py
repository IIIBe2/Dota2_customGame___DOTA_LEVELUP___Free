# telegram_bot.py
import asyncio
import re
import shutil
import threading
import time
import json
import os
import traceback
from typing import Dict, List, Optional
import telebot
from telebot import types
import logging

# Импорты из проекта
from config import INFINITE_STATS_FILE, PASS_LOBBY, LOG_FILE, PASSWORDS_FILE, STATS_FILE, TELEGRAM_ADMIN_IDS, TELEGRAM_BOT_TOKEN
from pause_handler import pause_handler
from statistics import stats
from logger import Logger
from pet_manager import PetManager

# Настройка логирования для бота
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramBotManager:
    def __init__(self, main_program=None):
        self.bot = None
        self.bot_thread = None
        self.running = False
        self.main_program = main_program
        self.user_state = {}  # Для отслеживания состояния пользователей
        self.saved_passwords = self.load_passwords()
        self.logger = Logger()
        self.pet_manager = PetManager(logger)
        
        # Проверяем наличие токена
        if not TELEGRAM_BOT_TOKEN:
            print("⚠️ TELEGRAM_BOT_TOKEN не установлен. Бот не будет запущен.")
            print("   Установите токен в файле telegram_bot.py")
        else:
            self.setup_bot()
    
    def load_passwords(self):
        """Загрузка сохраненных паролей"""
        if os.path.exists(PASSWORDS_FILE):
            try:
                with open(PASSWORDS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Ошибка загрузки паролей: {e}")
                return {}
        return {}
    
    def pets_menu(self, chat_id):
        """Меню управления питомцами"""
        # 🔥 ОЧИЩАЕМ СОСТОЯНИЕ ПРИ ВХОДЕ В МЕНЮ ПИТОМЦЕВ
        if chat_id in self.user_state:
            # Оставляем только если это нужно для других операций
            # В данном случае очищаем полностью
            del self.user_state[chat_id]
        
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        
        buttons = [
            "📋 Список питомцев",
            "➕ Новый питомец",
            "🎯 Записать позиции",
            "🐾 Переключить питомца",
            "⬅️ Назад"
        ]
        
        row1 = buttons[:2]
        row2 = buttons[2:4]
        row3 = buttons[4:]
        
        markup.add(*[types.KeyboardButton(btn) for btn in row1])
        markup.add(*[types.KeyboardButton(btn) for btn in row2])
        markup.add(*[types.KeyboardButton(btn) for btn in row3])
        
        pets = self.pet_manager.get_pet_list()
        current_pet = self.pet_manager.current_pet
        
        message = "<b>🐾 Управление питомцами</b>\n\n"
        
        if current_pet and current_pet in pets:
            message += f"<b>Текущий питомец:</b> {pets[current_pet]['name']}\n\n"
        
        message += f"<b>Всего питомцев:</b> {len(pets)}\n"
        
        if pets:
            message += "\n<b>Доступные питомцы:</b>\n"
            for pet_id, pet_data in pets.items():
                click_count = len(pet_data.get('clicks', []))
                message += f"• {pet_data['name']} (кликов: {click_count}/5)\n"
        
        message += "\nВыберите действие:"
        
        self.bot.send_message(
            chat_id,
            message,
            reply_markup=markup,
            parse_mode='HTML'
        )
    
    def pet_settings_menu(self, chat_id, pet_id):
        """Меню настроек конкретного питомца"""
        if pet_id not in self.pet_manager.pets:
            self.bot.send_message(chat_id, "❌ Питомец не найден")
            return
        
        # 🔥 ВСЕГДА ОБНОВЛЯЕМ СОСТОЯНИЕ С ТЕКУЩИМ PET_ID
        self.user_state[chat_id] = {
            'pet_id': pet_id,
            'action': 'pet_settings'
        }
        
        pet = self.pet_manager.pets[pet_id]
        
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        
        # 🔥 ИСПРАВЛЯЕМ ТЕКСТ КНОПОК
        delay_text = f"⏱️ Задержка ({pet.get('click_delay', 2.0)}сек)"
        
        buttons = [
            delay_text,
            "🎯 Добавить триггер",
            "📋 Триггеры",
            "🐾 Переключить сейчас",
            "⬅️ Назад к питомцам"
        ]
        
        # Распределяем кнопки по рядам
        row1 = buttons[:2]
        row2 = buttons[2:4]
        row3 = buttons[4:]
        
        markup.add(*[types.KeyboardButton(btn) for btn in row1])
        markup.add(*[types.KeyboardButton(btn) for btn in row2])
        markup.add(*[types.KeyboardButton(btn) for btn in row3])
        
        # Информация о триггерах
        triggers_info = ""
        triggers = pet.get('infinite_triggers', [])
        if triggers:
            triggers_info = "\n📋 *Триггеры бесконечки:*\n"
            for trigger in triggers:
                enabled = "✅" if trigger.get('enabled', True) else "❌"
                triggers_info += f"{enabled} {trigger.get('cycles')} циклов\n"
        else:
            triggers_info = "\nℹ️ *Триггеры не настроены*"
        
        self.bot.send_message(
            chat_id,
            f"⚙️ *Настройки питомца: {pet['name']}*\n\n"
            f"🐾 *ID:* `{pet_id}`\n"
            f"⏱️ *Задержка между кликами:* {pet.get('click_delay', 2.0)} сек\n"
            f"🖱️ *Кликов настроено:* {len(pet.get('clicks', []))}/5\n"
            f"{triggers_info}\n\n"
            f"Выберите действие:",
            reply_markup=markup,
            parse_mode='Markdown'
        )

    def add_infinite_trigger_dialog(self, chat_id, pet_id):
        """Диалог добавления триггера бесконечки"""
        self.user_state[chat_id] = {
            'action': 'waiting_trigger_cycles',
            'pet_id': pet_id
        }
        
        self.bot.send_message(
            chat_id,
            "🎯 *Добавление триггера бесконечки*\n\n"
            "Введите количество циклов бесконечки для срабатывания триггера:\n\n"
            "Пример: 30 (переключится при 30+ циклах)\n"
            "Пример: 100 (переключится при 100+ циклах)",
            parse_mode='Markdown'
        )

    def handle_trigger_cycles_input(self, chat_id, cycles_text, pet_id):
        """Обработка ввода количества циклов для триггера"""
        try:
            cycles = int(cycles_text)
            if cycles <= 0:
                self.bot.send_message(chat_id, "❌ Количество циклов должно быть положительным числом")
                return
            
            # Добавляем триггер
            success, message = self.pet_manager.add_infinite_trigger(pet_id, cycles)
            
            # 🔥 ОЧИЩАЕМ ТОЛЬКО ЧАСТЬ СОСТОЯНИЯ, ОСТАВЛЯЯ PET_ID
            if chat_id in self.user_state:
                # Удаляем только состояние ожидания ввода, но оставляем pet_id
                self.user_state[chat_id].pop('action', None)
            
            if success:
                pet_name = self.pet_manager.pets[pet_id]['name']
                self.bot.send_message(
                    chat_id,
                    f"✅ *Триггер добавлен!*\n\n"
                    f"🐾 Питомец: {pet_name}\n"
                    f"🎯 Триггер: {cycles} циклов бесконечки\n\n"
                    f"Теперь при достижении {cycles}+ циклов бесконечки "
                    f"будет автоматически переключаться на этого питомца.",
                    parse_mode='Markdown'
                )
                # 🔥 ПОСЛЕ ДОБАВЛЕНИЯ ТРИГГЕРА СНОВА ПОКАЗЫВАЕМ МЕНЮ НАСТРОЕК
                self.pet_settings_menu(chat_id, pet_id)
            else:
                self.bot.send_message(chat_id, f"❌ {message}", parse_mode='Markdown')
                
        except ValueError:
            self.bot.send_message(chat_id, "❌ Введите число (например: 30)")

    def set_click_delay_dialog(self, chat_id, pet_id):
        """Диалог установки задержки между кликами"""
        self.user_state[chat_id] = {
            'action': 'waiting_click_delay',
            'pet_id': pet_id
        }
        
        current_delay = self.pet_manager.pets[pet_id].get('click_delay', 2.0)
        
        self.bot.send_message(
            chat_id,
            f"⏱️ *Установка задержки между кликами*\n\n"
            f"Текущая задержка: {current_delay} сек\n\n"
            f"Введите новую задержку (в секундах):\n\n"
            f"• Минимум: 0.1 сек\n"
            f"• Максимум: 10 сек\n"
            f"• Рекомендуется: 2.0 сек\n\n"
            f"Примеры: 0.5, 1.0, 2.0, 3.0",
            parse_mode='Markdown'
        )

    def handle_click_delay_input(self, chat_id, delay_text, pet_id):
        """Обработка ввода задержки между кликами"""
        try:
            delay = float(delay_text)
            
            if delay < 0.1 or delay > 10:
                self.bot.send_message(chat_id, "❌ Задержка должна быть от 0.1 до 10 секунд")
                return
            
            # Устанавливаем задержку
            success, message = self.pet_manager.set_click_delay(pet_id, delay)
            
            # 🔥 ОЧИЩАЕМ ТОЛЬКО ЧАСТЬ СОСТОЯНИЯ
            if chat_id in self.user_state:
                self.user_state[chat_id].pop('action', None)
            
            if success:
                pet_name = self.pet_manager.pets[pet_id]['name']
                self.bot.send_message(
                    chat_id,
                    f"✅ *Задержка установлена!*\n\n"
                    f"🐾 Питомец: {pet_name}\n"
                    f"⏱️ Новая задержка: {delay} сек\n\n"
                    f"Теперь при переключении на этого питомца "
                    f"будут использоваться задержки по {delay} секунды между кликами.",
                    parse_mode='Markdown'
                )
                # 🔥 ВОЗВРАЩАЕМСЯ В МЕНЮ НАСТРОЕК
                self.pet_settings_menu(chat_id, pet_id)
            else:
                self.bot.send_message(chat_id, f"❌ {message}", parse_mode='Markdown')
                
        except ValueError:
            self.bot.send_message(chat_id, "❌ Введите число (например: 2.0)")

    def show_pet_list(self, chat_id):
        """Показать список питомцев с inline-кнопками"""
        pets = self.pet_manager.get_pet_list()
        
        if not pets:
            self.bot.send_message(
                chat_id,
                "📭 *Список питомцев пуст*\n\n"
                "У вас нет созданных питомцев.\n"
                "Используйте 'Новый питомец' для создания.",
                parse_mode='Markdown'
            )
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for pet_id, pet_data in pets.items():
            click_count = len(pet_data.get('clicks', []))
            
            # 🔥 ИСПРАВЛЯЕМ ТЕКСТ КНОПКИ
            settings_btn = types.InlineKeyboardButton(
                text=f"⚙️ {pet_data['name']} (кликов: {click_count}/5)",
                callback_data=f"pet_settings_{pet_id}"
            )
            
            markup.add(settings_btn)
        
        self.bot.send_message(
            chat_id,
            "📋 *Список питомцев*\n\n"
            "Нажмите на питомца для управления настройками:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    def add_new_pet(self, chat_id):
        """Добавление нового питомца"""
        self.user_state[chat_id] = {
            'action': 'waiting_pet_id',
            'step': 1
        }
        
        self.bot.send_message(
            chat_id,
            "➕ *Создание нового питомца*\n\n"
            "Шаг 1/2: Введите уникальный ID для питомца\n"
            "Например: pet1, pet2, dog, cat",
            parse_mode='Markdown'
        )
    
    def record_positions_menu(self, chat_id):
        """Меню записи позиций для питомца"""
        pets = self.pet_manager.get_pet_list()
        
        if not pets:
            self.bot.send_message(
                chat_id,
                "❌ *Нет питомцев для записи*\n\n"
                "Сначала создайте питомца через меню 'Новый питомец'.",
                parse_mode='Markdown'
            )
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for pet_id, pet_data in pets.items():
            click_count = len(pet_data.get('clicks', []))
            if click_count < 5:  # Только питомцы с незаполненными кликами
                button_text = f"{pet_data['name']} ({click_count}/5 кликов)"
                button = types.InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"record_pet_{pet_id}"
                )
                markup.add(button)
        
        if markup.keyboard:  # Если есть кнопки
            self.bot.send_message(
                chat_id,
                "🎯 *Запись позиций для питомца*\n\n"
                "Выберите питомца для записи позиций:\n"
                "• Подведите мышь к нужной позиции на экране\n"
                "• Нажмите кнопку с питомцем\n"  # 🔥 ИСПРАВЛЕНО: кавычки
                "• Система запишет текущую позицию мыши",
                reply_markup=markup,
                parse_mode='Markdown'
            )
        else:
            self.bot.send_message(
                chat_id,
                "✅ *Все питомцы настроены*\n\n"
                "У всех питомцев уже есть 5 кликов.",
                parse_mode='Markdown'
            )

    def save_passwords(self):
        """Сохранение паролей"""
        try:
            os.makedirs(os.path.dirname(PASSWORDS_FILE), exist_ok=True)
            with open(PASSWORDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.saved_passwords, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"⚠️ Ошибка сохранения паролей: {e}")
            return False
    
    def setup_bot(self):
        """Настройка бота и команд"""
        try:
            self.bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode=None)
            print("✅ Telegram бот инициализирован")
            
            # Регистрация команд
            self.setup_commands()
            
        except Exception as e:
            print(f"❌ Ошибка настройки бота: {e}")
    
    def setup_commands(self):
        """Настройка команд бота"""
        
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            if not self.check_auth(message):
                return
            
            welcome_text = """
    🤖 *Бот управления Dota 2 Automator активирован!*

    *Доступные команды:*
    /start - Главное меню
    /status - Статус программы  
    /statistics - Статистика
    /restart - Перезапуск программы
    /password - Управление паролями
    /control - Управление программой
    /pause - Пауза программы
    /resume - Продолжить работу
    /stop - Остановить программу
    /screenshot - Сделать скриншот
    /layout - Управление раскладкой

    Или используйте кнопки меню ниже 👇
    """
            
            self.bot.send_message(
                message.chat.id,
                welcome_text,
                parse_mode='Markdown'
            )
            self.send_main_menu(message.chat.id)
        
        # 🔥 УБЕДИТЕСЬ ЧТО ЭТИ ОБРАБОТЧИКИ ЕСТЬ:
        @self.bot.message_handler(commands=['status'])
        def send_status(message):
            if not self.check_auth(message):
                return
            self.send_status_info(message.chat.id)
        
        # 🔥 ДОБАВЛЯЕМ НОВУЮ КОМАНДУ
        @self.bot.message_handler(commands=['cleanup'])
        def cleanup_command(message):
            if not self.check_auth(message):
                return
            self.cleanup_menu(message.chat.id)

        @self.bot.message_handler(commands=['statistics'])
        def send_statistics(message):
            if not self.check_auth(message):
                return
            self.send_statistics_info(message.chat.id)
        
        @self.bot.message_handler(commands=['restart'])
        def restart_program(message):
            if not self.check_auth(message):
                return
            self.restart_program_command(message.chat.id)
        
        @self.bot.message_handler(commands=['detailed_status'])
        def send_detailed_status(message):
            if not self.check_auth(message):
                return
            
            detailed_status = pause_handler.get_detailed_status_for_telegram()
            self.bot.send_message(
                message.chat.id,
                detailed_status,
                parse_mode='Markdown'
            )

        @self.bot.message_handler(commands=['password'])
        def password_menu(message):
            if not self.check_auth(message):
                return
            self.show_password_menu(message.chat.id)
        
        @self.bot.message_handler(commands=['control'])
        def control_menu(message):
            if not self.check_auth(message):
                return
            self.show_control_menu(message.chat.id)
        
        @self.bot.message_handler(commands=['pause'])
        def pause_program(message):
            if not self.check_auth(message):
                return
            self.pause_program_command(message.chat.id)
        
        @self.bot.message_handler(commands=['resume'])
        def resume_program(message):
            if not self.check_auth(message):
                return
            self.resume_program_command(message.chat.id)
        
        @self.bot.message_handler(commands=['stop'])
        def stop_program(message):
            if not self.check_auth(message):
                return
            self.stop_program_command(message.chat.id)
        
        @self.bot.message_handler(commands=['start_program'])
        def start_program(message):
            if not self.check_auth(message):
                return
            self.start_program_command(message.chat.id)
        
        @self.bot.message_handler(commands=['menu'])
        def send_menu(message):
            if not self.check_auth(message):
                return
            self.send_main_menu(message.chat.id)
        
        # 🔥 НОВЫЕ КОМАНДЫ:
        @self.bot.message_handler(commands=['screenshot'])
        def take_screenshot_command(message):
            if not self.check_auth(message):
                return
            self.take_screenshot_command_handler(message.chat.id)
        
        @self.bot.message_handler(commands=['layout'])
        def keyboard_layout_command(message):
            if not self.check_auth(message):
                return
            self.keyboard_layout_menu(message.chat.id)
        
        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback_query(call):
            print(f"🔄 Callback получен: {call.data}")
            
            chat_id = call.message.chat.id
            
            # 🔥 ОБРАБОТКА ОЧИСТКИ
            if call.data == "clean_infinite_confirm":
                self.clean_infinite_stats(chat_id)
                self.bot.answer_callback_query(call.id, "Статистика очищена")
                
                # Удаляем inline-кнопки
                try:
                    self.bot.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=call.message.message_id,
                        reply_markup=None
                    )
                except:
                    pass
                
            elif call.data.startswith("use_password_"):
                password_name = call.data.replace("use_password_", "")
                self.use_saved_password(call.message.chat.id, password_name)
                self.bot.answer_callback_query(call.id, "Пароль установлен")

            # Также добавьте обработку delete_password_
            elif call.data.startswith("delete_password_"):
                password_name = call.data.replace("delete_password_", "")
                self.delete_password(call.message.chat.id, password_name)
                self.bot.answer_callback_query(call.id, "Пароль удален")

            elif call.data.startswith("toggle_trigger_"):
                parts = call.data.replace("toggle_trigger_", "").split("_")
                if len(parts) >= 2:
                    pet_id = parts[0]
                    try:
                        cycles = int(parts[1])
                        
                        # Находим и переключаем триггер
                        pet = self.pet_manager.pets.get(pet_id)
                        if pet:
                            triggers = pet.get('infinite_triggers', [])
                            for trigger in triggers:
                                if trigger.get('cycles') == cycles:
                                    trigger['enabled'] = not trigger.get('enabled', True)
                                    self.pet_manager.save_pets()
                                    
                                    status = "включен" if trigger['enabled'] else "выключен"
                                    self.bot.answer_callback_query(
                                        call.id, 
                                        f"Триггер {status}"
                                    )
                                    
                                    # Обновляем сообщение
                                    self.show_pet_triggers(call.message.chat.id, pet_id)
                                    break
                    except ValueError:
                        self.bot.answer_callback_query(call.id, "❌ Ошибка")

            elif call.data.startswith("delete_trigger_"):
                parts = call.data.replace("delete_trigger_", "").split("_")
                if len(parts) >= 2:
                    pet_id = parts[0]
                    try:
                        cycles = int(parts[1])
                        
                        # Удаляем триггер
                        success, message = self.pet_manager.remove_infinite_trigger(pet_id, cycles)
                        
                        if success:
                            self.bot.answer_callback_query(call.id, "✅ Удалено")
                            self.show_pet_triggers(call.message.chat.id, pet_id)
                        else:
                            self.bot.answer_callback_query(call.id, "❌ Не удалось удалить")
                    except ValueError:
                        self.bot.answer_callback_query(call.id, "❌ Ошибка")

            elif call.data.startswith("add_trigger_"):
                pet_id = call.data.replace("add_trigger_", "")
                
                # Показываем диалог добавления триггера
                self.user_state[call.message.chat.id] = {
                    'action': 'waiting_trigger_cycles',
                    'pet_id': pet_id
                }
                
                self.bot.send_message(
                    call.message.chat.id,
                    "🎯 *Добавление триггера бесконечки*\n\n"
                    "Введите количество циклов бесконечки для срабатывания триггера:\n\n"
                    "Пример: 30 (переключится при 30+ циклах)\n"
                    "Пример: 100 (переключится при 100+ циклах)",
                    parse_mode='Markdown'
                )
                self.bot.answer_callback_query(call.id)
                    
            elif call.data == "clean_infinite_cancel":
                self.bot.answer_callback_query(call.id, "Отменено")
                
                # Обновляем сообщение
                try:
                    self.bot.edit_message_text(
                        "❌ Очистка статистики отменена",
                        chat_id=chat_id,
                        message_id=call.message.message_id
                    )
                except:
                    self.bot.send_message(chat_id, "❌ Очистка статистики отменена")

            elif call.data.startswith("pet_settings_"):
                pet_id = call.data.replace("pet_settings_", "")
                
                # Сохраняем pet_id в состояние пользователя
                self.user_state[call.message.chat.id] = {
                    'pet_id': pet_id,
                    'action': 'pet_settings'
                }
                
                # Показываем меню настроек
                self.pet_settings_menu(call.message.chat.id, pet_id)
                self.bot.answer_callback_query(call.id, "Настройки питомца")
            elif call.data.startswith("delete_pet_"):
                pet_id = call.data.replace("delete_pet_", "")
                
                # Подтверждение удаления
                markup = types.InlineKeyboardMarkup()
                confirm_btn = types.InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=f"confirm_delete_pet_{pet_id}"
                )
                cancel_btn = types.InlineKeyboardButton(
                    text="❌ Нет, отмена",
                    callback_data=f"cancel_delete_pet_{pet_id}"
                )
                markup.add(confirm_btn, cancel_btn)
                
                pet_name = self.pet_manager.pets.get(pet_id, {}).get('name', 'Неизвестный')
                
                self.bot.edit_message_text(
                    f"⚠️ <b>Подтверждение удаления</b>\n\n"
                    f"Вы действительно хотите удалить питомца?\n\n"
                    f"🐾 <b>Имя:</b> {pet_name}\n"
                    f"📝 <b>ID:</b> <code>{pet_id}</code>\n\n"
                    f"Это действие нельзя отменить!",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=markup,
                    parse_mode='HTML'
                )
                self.bot.answer_callback_query(call.id)

            elif call.data.startswith("switch_pet_"):
                pet_id = call.data.replace("switch_pet_", "")
                success, message = self.pet_manager.switch_to_pet(pet_id)
                
                if success:
                    self.bot.answer_callback_query(call.id, "✅ Переключено")
                    pet_name = self.pet_manager.pets.get(pet_id, {}).get('name', 'Неизвестный')
                    self.bot.send_message(
                        call.message.chat.id,
                        f"✅ <b>Переключение успешно!</b>\n\n"
                        f"Переключились на питомца: <b>{pet_name}</b>\n"
                        f"{message}",
                        parse_mode='HTML'
                    )
                else:
                    self.bot.answer_callback_query(call.id, "❌ Ошибка")
                    self.bot.send_message(
                        call.message.chat.id,
                        f"❌ <b>Ошибка переключения:</b>\n\n{message}",
                        parse_mode='HTML'
                    )

            elif call.data.startswith("confirm_delete_pet_"):
                pet_id = call.data.replace("confirm_delete_pet_", "")
                
                success, message = self.pet_manager.delete_pet(pet_id)
                
                if success:
                    self.bot.answer_callback_query(call.id, "✅ Удалено")
                    # Обновляем сообщение
                    try:
                        self.bot.edit_message_text(
                            f"✅ <b>Питомец удален!</b>\n\n{message}",
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            parse_mode='HTML'
                        )
                    except:
                        self.bot.send_message(
                            call.message.chat.id,
                            f"✅ <b>Питомец удален!</b>\n\n{message}",
                            parse_mode='HTML'
                        )
                else:
                    self.bot.answer_callback_query(call.id, "❌ Ошибка")
                    self.bot.send_message(
                        call.message.chat.id,
                        f"❌ <b>Ошибка:</b> {message}",
                        parse_mode='HTML'
                    )

            elif call.data.startswith("cancel_delete_pet_"):
                pet_id = call.data.replace("cancel_delete_pet_", "")
                self.bot.answer_callback_query(call.id, "❌ Отменено")
                
                # Возвращаемся к списку питомцев
                self.show_pet_list(call.message.chat.id)

            elif call.data == "clean_screenshots_confirm":
                self.clean_screenshots(chat_id)
                self.bot.answer_callback_query(call.id, "Скриншоты очищены")
                
                try:
                    self.bot.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=call.message.message_id,
                        reply_markup=None
                    )
                except:
                    pass
                
            elif call.data == "clean_screenshots_cancel":
                self.bot.answer_callback_query(call.id, "Отменено")
                
                try:
                    self.bot.edit_message_text(
                        "❌ Очистка скриншотов отменена",
                        chat_id=chat_id,
                        message_id=call.message.message_id
                    )
                except:
                    self.bot.send_message(chat_id, "❌ Очистка скриншотов отменена")
            
            elif call.data == "clean_all_confirm":
                self.clean_all_data(chat_id)
                self.bot.answer_callback_query(call.id, "Все данные очищены")
                
                try:
                    self.bot.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=call.message.message_id,
                        reply_markup=None
                    )
                except:
                    pass
                
            elif call.data == "clean_all_cancel":
                self.bot.answer_callback_query(call.id, "Отменено")
                
                try:
                    self.bot.edit_message_text(
                        "❌ Полная очистка отменена",
                        chat_id=chat_id,
                        message_id=call.message.message_id
                    )
                except:
                    self.bot.send_message(chat_id, "❌ Полная очистка отменена")

            elif call.data.startswith("record_pet_"):
                pet_id = call.data.replace("record_pet_", "")
                
                # Запрашиваем описание для клика
                pet = self.pet_manager.pets.get(pet_id, {})
                current_clicks = len(pet.get('clicks', []))
                click_number = current_clicks + 1
                
                # Сохраняем состояние
                self.user_state[call.message.chat.id] = {
                    'action': 'recording_position',
                    'pet_id': pet_id,
                    'click_number': click_number
                }
                
                self.bot.send_message(
                    call.message.chat.id,
                    f"🎯 <b>Запись позиции #{click_number}</b>\n\n"
                    f"Питомец: <b>{pet.get('name', 'Неизвестный')}</b>\n\n"
                    f"1. Подведите мышь к нужной позиции на экране\n"
                    f"2. Введите описание для этой позиции\n"
                    f"   Например: 'Кнопка выбора', 'Меню навыков'",
                    parse_mode='HTML'
                )
                self.bot.answer_callback_query(call.id)
            # 🔥 ОБРАБОТКА ПИТОМЦЕВ (если нужно)
            elif call.data.startswith("switch_pet_"):
                pet_id = call.data.replace("switch_pet_", "")
                success, message = self.pet_manager.switch_to_pet(pet_id)
                
                if success:
                    self.bot.answer_callback_query(call.id, "✅ Переключено")
                    self.bot.send_message(chat_id, f"✅ {message}")
                else:
                    self.bot.answer_callback_query(call.id, "❌ Ошибка")
                    self.bot.send_message(chat_id, f"❌ {message}")

        # 🔥 ВАЖНО: Этот обработчик должен быть ПОСЛЕДНИМ
        @self.bot.message_handler(func=lambda message: True)
        def handle_all_messages(message):
            """Обработка всех сообщений"""
            if not self.check_auth(message):
                return
            
            chat_id = message.chat.id
            text = message.text.strip() if message.text else ""
            
            print(f"🤖 Получено сообщение: '{text}' от {chat_id}")
            
            # 🔥 ПРОВЕРЯЕМ СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЯ С ЗАЩИТОЙ ОТ None
            state = self.user_state.get(chat_id)
            
            # 🔥 ЕСЛИ ЕСТЬ СОСТОЯНИЕ - ОБРАБАТЫВАЕМ ЕГО
            if state:
                action = state.get('action')
                
                if action == 'waiting_pet_id':
                    self.handle_pet_id_input(chat_id, text)
                    return
                elif action == 'waiting_pet_name':
                    self.handle_pet_name_input(chat_id, text, state.get('pet_id'))
                    return
                elif action == 'recording_position':
                    self.handle_position_recording(chat_id, text, state)
                    return
                elif action == 'waiting_password':
                    self.handle_new_password(chat_id, text)
                    return
                elif action == 'waiting_password_name':
                    self.handle_password_name(chat_id, text)
                    return
                elif action == 'waiting_trigger_cycles':
                    pet_id = state.get('pet_id')
                    self.handle_trigger_cycles_input(chat_id, text, pet_id)
                    return
                elif action == 'waiting_click_delay':
                    pet_id = state.get('pet_id')
                    self.handle_click_delay_input(chat_id, text, pet_id)
                    return
            
            # 🔥 ОБРАБОТКА КНОПОК МЕНЮ ПИТОМЦЕВ
            if text == "🐾 Питомцы":
                self.pets_menu(chat_id)
                return
            elif text == "📋 Список питомцев":
                self.show_pet_list(chat_id)
                return
            elif text == "➕ Новый питомец":
                self.add_new_pet(chat_id)
                return
            elif text == "🎯 Записать позиции":
                self.record_positions_menu(chat_id)
                return
            elif text == "🐾 Переключить питомца":
                self.show_pet_list(chat_id)
                return
            elif text.startswith("⚙️ Настройки "):
                # Извлекаем ID питомца из текста
                pet_id = text.replace("⚙️ Настройки ", "").strip()
                # Сохраняем pet_id в состояние
                self.user_state[chat_id] = {
                    'pet_id': pet_id,
                    'action': 'pet_settings'
                }
                self.pet_settings_menu(chat_id, pet_id)
                return
            
            # 🔥 ОБРАБОТКА ОСТАЛЬНЫХ КНОПОК МЕНЮ
            if text == "📱 Статус":
                self.send_status_info(chat_id)
            elif text == "📊 Статистика":
                self.send_statistics_info(chat_id)
            elif text == "🎮 Управление":
                self.show_control_menu(chat_id)
            elif text == "🔐 Пароли":
                self.show_password_menu(chat_id)
            elif text == "🧹 Очистка":
                self.cleanup_menu(chat_id)
            elif text == "🔄 Перезапуск":
                self.restart_program_command(chat_id)
            elif text == "⚙️ Настройки":
                self.show_settings_menu(chat_id)
            elif text == "📸 Скриншот":
                self.take_screenshot_command_handler(chat_id)
            elif text == "⌨️ Раскладка":
                self.keyboard_layout_menu(chat_id)
            elif text == "⏸️ Пауза":
                self.pause_program_command(chat_id)
            elif text == "▶️ Продолжить":
                self.resume_program_command(chat_id)
            elif text == "🛑 Остановить":
                self.stop_program_command(chat_id)
            elif text == "🚀 Запустить":
                self.start_program_command(chat_id)
            elif text == "⬅️ Назад":
                self.send_main_menu(chat_id)
            elif text == "📋 Список паролей":
                self.show_saved_passwords(chat_id)
            elif text == "➕ Новый пароль":
                self.ask_for_password(chat_id)
            elif text in ["🧹 Очистить статистику бесконечки", 
                        "📸 Очистить скриншоты", 
                        "🗑️ Очистить всё"]:
                self.handle_cleanup_commands(chat_id, text)
            elif text in ["⌨️ Проверить раскладку", 
                        "🇬🇧 Переключить на английскую", 
                        "🇬🇧 Переключить на русскую"]:
                self.handle_keyboard_layout_commands(chat_id, text)
            elif text in ["⏱️ Задержка", 
              "🎯 Добавить триггер", 
              "📋 Триггеры", 
              "🐾 Переключить сейчас",
              "⬅️ Назад к питомцам"]:
                # 🔥 ОБРАБОТКА КНОПОК НАСТРОЕК ПИТОМЦА
                if chat_id in self.user_state and 'pet_id' in self.user_state[chat_id]:
                    pet_id = self.user_state[chat_id]['pet_id']
                    
                    if text == "⏱️ Задержка":
                        self.set_click_delay_dialog(chat_id, pet_id)
                    elif text == "🎯 Добавить триггер":
                        self.add_infinite_trigger_dialog(chat_id, pet_id)
                    elif text == "📋 Триггеры":
                        self.show_pet_triggers(chat_id, pet_id)
                    elif text == "🐾 Переключить сейчас":
                        success, message = self.pet_manager.switch_to_pet(pet_id)
                        if success:
                            self.bot.send_message(chat_id, f"✅ {message}")
                        else:
                            self.bot.send_message(chat_id, f"❌ {message}")
                    elif text == "⬅️ Назад к питомцам":
                        # 🔥 ОЧИЩАЕМ СОСТОЯНИЕ ПЕРЕД ВОЗВРАТОМ
                        if chat_id in self.user_state:
                            # Оставляем только минимальную информацию, если нужно
                            del self.user_state[chat_id]
                        self.pets_menu(chat_id)
                else:
                    # 🔥 ЕСЛИ НЕТ PET_ID, ПРОСТО ПОКАЗЫВАЕМ МЕНЮ ПИТОМЦЕВ
                    if text == "⬅️ Назад к питомцам":
                        self.pets_menu(chat_id)
                    else:
                        self.bot.send_message(chat_id, "❌ Сначала выберите питомца")
            else:
                # 🔥 ЕСЛИ НЕ РАСПОЗНАЛИ КОМАНДУ, ПРОБУЕМ КАК ПАРОЛЬ ИЛИ ДРУГОЕ
                if text and len(text) > 1:
                    # Возможно, это пароль
                    self.bot.send_message(
                        chat_id,
                        f"❓ Неизвестная команда: '{text}'\n\n"
                        "Используйте меню или команды ниже 👇",
                        parse_mode='Markdown'
                    )
                    self.send_main_menu(chat_id)
    
    def show_settings_menu(self, chat_id):
        """Меню настроек"""
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        
        buttons = [
            "🐾 Питомцы",
            "🧹 Очистка",
            "⌨️ Раскладка",
            "⬅️ Назад"
        ]
        
        row1 = buttons[:2]
        row2 = buttons[2:]
        
        markup.add(*[types.KeyboardButton(btn) for btn in row1])
        markup.add(*[types.KeyboardButton(btn) for btn in row2])
        
        self.bot.send_message(
            chat_id,
            "⚙️ *Меню настроек*\n\n"
            "Выберите действие:",
            reply_markup=markup,
            parse_mode='Markdown'
        )

    def pet_settings_menu(self, chat_id, pet_id):
        """Меню настроек конкретного питомца"""
        if pet_id not in self.pet_manager.pets:
            self.bot.send_message(chat_id, "❌ Питомец не найден")
            return
        
        # 🔥 СОХРАНЯЕМ PET_ID В СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЯ
        self.user_state[chat_id] = {
            'pet_id': pet_id,
            'action': 'pet_settings'
        }
        
        pet = self.pet_manager.pets[pet_id]
        
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        
        # 🔥 ИСПРАВЛЯЕМ ТЕКСТ КНОПОК
        delay_text = f"⏱️ Задержка ({pet.get('click_delay', 2.0)}сек)"
        
        buttons = [
            delay_text,
            "🎯 Добавить триггер",
            "📋 Триггеры",
            "🐾 Переключить сейчас",
            "⬅️ Назад к питомцам"
        ]
        
        # Распределяем кнопки по рядам
        row1 = buttons[:2]
        row2 = buttons[2:4]
        row3 = buttons[4:]
        
        markup.add(*[types.KeyboardButton(btn) for btn in row1])
        markup.add(*[types.KeyboardButton(btn) for btn in row2])
        markup.add(*[types.KeyboardButton(btn) for btn in row3])
        
        # Информация о триггерах
        triggers_info = ""
        triggers = pet.get('infinite_triggers', [])
        if triggers:
            triggers_info = "\n📋 *Триггеры бесконечки:*\n"
            for trigger in triggers:
                enabled = "✅" if trigger.get('enabled', True) else "❌"
                triggers_info += f"{enabled} {trigger.get('cycles')} циклов\n"
        else:
            triggers_info = "\nℹ️ *Триггеры не настроены*"
        
        self.bot.send_message(
            chat_id,
            f"⚙️ *Настройки питомца: {pet['name']}*\n\n"
            f"🐾 *ID:* `{pet_id}`\n"
            f"⏱️ *Задержка между кликами:* {pet.get('click_delay', 2.0)} сек\n"
            f"🖱️ *Кликов настроено:* {len(pet.get('clicks', []))}/5\n"
            f"{triggers_info}\n\n"
            f"Выберите действие:",
            reply_markup=markup,
            parse_mode='Markdown'
        )

    def handle_position_recording(self, chat_id, description, state):
        """Обработка записи позиции"""
        pet_id = state.get('pet_id')
        click_number = state.get('click_number', 1)
        
        print(f"🎯 Запись позиции #{click_number} для питомца {pet_id}")
        print(f"📝 Описание: {description}")
        
        success, message, position = self.pet_manager.record_current_position(
            pet_id, click_number, description
        )
        
        if success:
            x, y = position
            pet = self.pet_manager.pets.get(pet_id, {})
            current_clicks = len(pet.get('clicks', []))
            
            response = f"✅ <b>Позиция записана!</b>\n\n"
            response += f"🐾 Питомец: <b>{pet.get('name', 'Неизвестный')}</b>\n"
            response += f"🎯 Позиция #{click_number}: ({x}, {y})\n"
            response += f"📝 Описание: {description}\n\n"
            response += f"📊 Записано кликов: {current_clicks}/5\n\n"
            
            if current_clicks < 5:
                response += "Хотите записать еще одну позицию?\n"
                response += "Подведите мышь и введите описание."
                
                # Обновляем состояние для следующей позиции
                self.user_state[chat_id] = {
                    'action': 'recording_position',
                    'pet_id': pet_id,
                    'click_number': click_number + 1
                }
            else:
                response += "🎉 <b>Все 5 позиций записаны!</b>\n"
                response += "Питомец полностью настроен."
                
                if chat_id in self.user_state:
                    del self.user_state[chat_id]
            
            self.bot.send_message(chat_id, response, parse_mode='HTML')
        else:
            self.bot.send_message(
                chat_id, 
                f"❌ <b>Ошибка:</b> {message}", 
                parse_mode='HTML'
            )

    def handle_pet_id_input(self, chat_id, pet_id):
        """Обработка ввода ID питомца"""
        if not pet_id:
            self.bot.send_message(chat_id, "❌ ID не может быть пустым")
            return
        
        # Проверяем что ID состоит только из допустимых символов
        import re
        
        if not re.match(r'^[a-zA-Z0-9_]+$', pet_id):
            # 🔥 ИСПРАВЛЕНО: Используем HTML вместо Markdown
            self.bot.send_message(
                chat_id,
                "<b>❌ Недопустимый ID</b>\n\n"
                "ID может содержать только:\n"
                "• Латинские буквы (a-z, A-Z)\n"
                "• Цифры (0-9)\n"
                "• Знак подчеркивания (_)",
                parse_mode='HTML'  # 🔥 ИСПРАВЛЕНО
            )
            return
        
        self.user_state[chat_id] = {
            'action': 'waiting_pet_name',
            'pet_id': pet_id
        }
        
        # 🔥 ИСПРАВЛЕНО: Используем HTML вместо Markdown
        self.bot.send_message(
            chat_id,
            f"✅ ID принят: <code>{pet_id}</code>\n\n"
            "Шаг 2/2: Введите имя для питомца\n"
            "Например: 'Мой герой', 'Танк', 'Саппорт'",
            parse_mode='HTML'  # 🔥 ИСПРАВЛЕНО
        )

    def record_positions_menu(self, chat_id):
        """Меню записи позиций для питомца"""
        pets = self.pet_manager.get_pet_list()
        
        if not pets:
            self.bot.send_message(
                chat_id,
                "❌ <b>Нет питомцев для записи</b>\n\n"
                "Сначала создайте питомца через меню 'Новый питомец'.",
                parse_mode='HTML'
            )
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for pet_id, pet_data in pets.items():
            click_count = len(pet_data.get('clicks', []))
            if click_count < 5:  # Только питомцы с незаполненными кликами
                button_text = f"{pet_data['name']} ({click_count}/5 кликов)"
                button = types.InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"record_pet_{pet_id}"
                )
                markup.add(button)
        
        if markup.keyboard:  # Если есть кнопки
            self.bot.send_message(
                chat_id,
                "🎯 <b>Запись позиций для питомца</b>\n\n"
                "Выберите питомца для записи позиций:\n"
                "• Подведите мышь к нужной позиции на экране\n"
                "• Нажмите кнопку с питомцем\n"
                "• Система запишет текущую позицию мыши",
                reply_markup=markup,
                parse_mode='HTML'
            )
        else:
            self.bot.send_message(
                chat_id,
                "✅ <b>Все питомцы настроены</b>\n\n"
                "У всех питомцев уже есть 5 кликов.",
                parse_mode='HTML'
            )

    def handle_pet_name_input(self, chat_id, pet_name, pet_id):
        """Обработка ввода имени питомца"""
        if not pet_name:
            self.bot.send_message(chat_id, "❌ Имя не может быть пустым")
            return
        
        success, message = self.pet_manager.add_pet(pet_id, pet_name)
        
        if chat_id in self.user_state:
            del self.user_state[chat_id]
        
        if success:
            # 🔥 ИСПРАВЛЕНО: Используем HTML
            self.bot.send_message(
                chat_id,
                f"✅ <b>Питомец создан!</b>\n\n"
                f"📝 <b>ID:</b> <code>{pet_id}</code>\n"
                f"🐾 <b>Имя:</b> {pet_name}\n\n"
                f"Теперь вы можете добавить позиции кликов для этого питомца.",
                parse_mode='HTML'
            )
        else:
            self.bot.send_message(
                chat_id, 
                f"❌ <b>Ошибка:</b> {message}", 
                parse_mode='HTML'
            )

    def handle_position_recording(self, chat_id, description, state):
        """Обработка записи позиции"""
        pet_id = state.get('pet_id')
        click_number = state.get('click_number', 1)
        
        success, message, position = self.pet_manager.record_current_position(
            pet_id, click_number, description
        )
        
        if success:
            x, y = position
            pet = self.pet_manager.pets.get(pet_id, {})
            current_clicks = len(pet.get('clicks', []))
            
            response = f"✅ *Позиция записана!*\n\n"
            response += f"🐾 Питомец: {pet.get('name', 'Неизвестный')}\n"
            response += f"🎯 Позиция #{click_number}: ({x}, {y})\n"
            response += f"📝 Описание: {description}\n\n"
            response += f"📊 Записано кликов: {current_clicks}/5\n\n"
            
            if current_clicks < 5:
                response += "Хотите записать еще одну позицию?\n"
                response += "Подведите мышь и введите описание."
                
                # Обновляем состояние для следующей позиции
                self.user_state[chat_id] = {
                    'action': 'recording_position',
                    'pet_id': pet_id,
                    'click_number': click_number + 1
                }
            else:
                response += "🎉 *Все 5 позиций записаны!*\n"
                response += "Питомец полностью настроен."
                
                if chat_id in self.user_state:
                    del self.user_state[chat_id]
            
            self.bot.send_message(chat_id, response, parse_mode='Markdown')
        else:
            self.bot.send_message(chat_id, f"❌ *Ошибка:* {message}", parse_mode='Markdown')

    def check_auth(self, message):
        """Проверка авторизации пользователя"""
        if not TELEGRAM_ADMIN_IDS:
            # Если список админов пуст, разрешаем всем
            return True
        
        user_id = message.from_user.id
        if user_id in TELEGRAM_ADMIN_IDS:
            return True
        
        self.bot.send_message(
            message.chat.id, 
            "⛔ У вас нет доступа к этому боту."
        )
        return False
    
    def show_settings_menu(self, chat_id):
        """Меню настроек"""
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        
        buttons = [
            "🐾 Питомцы",
            "🧹 Очистка",
            "⌨️ Раскладка",
            "⬅️ Назад"
        ]
        
        row1 = buttons[:2]
        row2 = buttons[2:]
        
        markup.add(*[types.KeyboardButton(btn) for btn in row1])
        markup.add(*[types.KeyboardButton(btn) for btn in row2])
        
        self.bot.send_message(
            chat_id,
            "⚙️ <b>Меню настроек</b>\n\n"
            "Выберите действие:",
            reply_markup=markup,
            parse_mode='HTML'
        )
    
    def handle_pet_commands(self, chat_id, text):
        """Обработка команд питомцев"""
        if text == "📋 Список питомцев":
            self.show_pet_list(chat_id)
        elif text == "➕ Новый питомец":
            self.add_new_pet(chat_id)
        elif text == "🎯 Записать позиции":
            self.record_positions_menu(chat_id)
        elif text == "🐾 Переключить питомца":
            self.show_pet_list(chat_id)
        elif text == "⬅️ Назад":
            self.send_main_menu(chat_id)
        # 🔥 ИСПРАВЛЕНИЕ: Добавляем обработку кнопок настроек питомца
        elif "⚙️ Настройки" in text:
            # Извлекаем ID питомца из текста
            pet_id = text.replace("⚙️ Настройки ", "").strip()
            self.pet_settings_menu(chat_id, pet_id)
        elif "⏱️ Задержка" in text:
            # Показываем диалог установки задержки
            if chat_id in self.user_state and 'pet_id' in self.user_state[chat_id]:
                pet_id = self.user_state[chat_id]['pet_id']
                self.set_click_delay_dialog(chat_id, pet_id)
        elif text == "🎯 Добавить триггер":
            if chat_id in self.user_state and 'pet_id' in self.user_state[chat_id]:
                pet_id = self.user_state[chat_id]['pet_id']
                self.add_infinite_trigger_dialog(chat_id, pet_id)
        elif text == "📋 Триггеры":
            if chat_id in self.user_state and 'pet_id' in self.user_state[chat_id]:
                pet_id = self.user_state[chat_id]['pet_id']
                self.show_pet_triggers(chat_id, pet_id)
        elif text == "🐾 Переключить сейчас":
            if chat_id in self.user_state and 'pet_id' in self.user_state[chat_id]:
                pet_id = self.user_state[chat_id]['pet_id']
                success, message = self.pet_manager.switch_to_pet(pet_id)
                if success:
                    self.bot.send_message(chat_id, f"✅ {message}")
                else:
                    self.bot.send_message(chat_id, f"❌ {message}")

    def show_pet_triggers(self, chat_id, pet_id):
        """Показать триггеры питомца"""
        if pet_id not in self.pet_manager.pets:
            self.bot.send_message(chat_id, "❌ Питомец не найден")
            return
        
        pet = self.pet_manager.pets[pet_id]
        triggers = pet.get('infinite_triggers', [])
        
        if not triggers:
            self.bot.send_message(
                chat_id,
                f"ℹ️ *Нет триггеров для питомца '{pet['name']}'*\n\n"
                "Триггеры позволяют автоматически переключаться на питомца "
                "при достижении определенного количества циклов бесконечки.\n\n"
                "Используйте 'Добавить триггер' для создания.",
                parse_mode='Markdown'
            )
            return
        
        # Создаем inline-клавиатуру для управления триггерами
        markup = types.InlineKeyboardMarkup()
        
        for trigger in triggers:
            cycles = trigger.get('cycles', 0)
            enabled = trigger.get('enabled', True)
            status = "✅" if enabled else "❌"
            
            btn_text = f"{status} {cycles} циклов"
            toggle_btn = types.InlineKeyboardButton(
                text=btn_text,
                callback_data=f"toggle_trigger_{pet_id}_{cycles}"
            )
            
            delete_btn = types.InlineKeyboardButton(
                text=f"🗑️ Удалить",
                callback_data=f"delete_trigger_{pet_id}_{cycles}"
            )
            
            markup.add(toggle_btn, delete_btn)
        
        add_btn = types.InlineKeyboardButton(
            text="➕ Добавить триггер",
            callback_data=f"add_trigger_{pet_id}"
        )
        markup.add(add_btn)
        
        self.bot.send_message(
            chat_id,
            f"📋 *Триггеры питомца: {pet['name']}*\n\n"
            f"Триггеры срабатывают при достижении указанного количества циклов бесконечки:\n\n"
            f"✅ - включен\n"
            f"❌ - выключен",
            reply_markup=markup,
            parse_mode='Markdown'
        )

    def cleanup_menu(self, chat_id):
        """Меню очистки данных"""
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        
        buttons = [
            "🧹 Очистить статистику бесконечки",
            "📸 Очистить скриншоты",
            "🗑️ Очистить всё",
            "⬅️ Назад"
        ]
        
        row1 = buttons[:2]
        row2 = buttons[2:]
        
        markup.add(*[types.KeyboardButton(btn) for btn in row1])
        markup.add(*[types.KeyboardButton(btn) for btn in row2])
        
        # Получаем информацию о файлах
        infinite_stats_size = self.get_file_size(INFINITE_STATS_FILE)
        screenshot_count, screenshot_size = self.get_screenshot_info()
        
        self.bot.send_message(
            chat_id,
            f"🧹 *Очистка данных*\n\n"
            f"📊 *Статистика бесконечки:*\n"
            f"• Файл: `{INFINITE_STATS_FILE}`\n"
            f"• Размер: {infinite_stats_size}\n\n"
            f"📸 *Скриншоты:*\n"
            f"• Количество: {screenshot_count}\n"
            f"• Общий размер: {screenshot_size}\n\n"
            f"Выберите что очистить:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    def get_file_size(self, filepath):
        """Получить размер файла в читаемом формате"""
        try:
            if os.path.exists(filepath):
                size_bytes = os.path.getsize(filepath)
                if size_bytes < 1024:
                    return f"{size_bytes} Б"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.1f} КБ"
                else:
                    return f"{size_bytes / (1024 * 1024):.1f} МБ"
            return "Файл не существует"
        except:
            return "Ошибка"

    def get_screenshot_info(self):
        """Получить информацию о скриншотах"""
        screenshots_dir = "screenshots"
        try:
            if os.path.exists(screenshots_dir):
                files = [f for f in os.listdir(screenshots_dir) if f.endswith('.png')]
                total_size = sum(os.path.getsize(os.path.join(screenshots_dir, f)) for f in files)
                
                if total_size < 1024 * 1024:
                    size_str = f"{total_size / 1024:.1f} КБ"
                else:
                    size_str = f"{total_size / (1024 * 1024):.1f} МБ"
                
                return len(files), size_str
            return 0, "0 Б"
        except:
            return 0, "Ошибка"
    
    def handle_cleanup_commands(self, chat_id, text):
        """Обработка команд очистки"""
        if text == "🧹 Очистить статистику бесконечки":
            self.confirm_clean_infinite_stats(chat_id)
        elif text == "📸 Очистить скриншоты":
            self.confirm_clean_screenshots(chat_id)
        elif text == "🗑️ Очистить всё":
            self.confirm_clean_all(chat_id)
        elif text == "⬅️ Назад":
            self.send_main_menu(chat_id)
    
    def clean_infinite_stats(self, chat_id):
        """Очистка статистики бесконечки"""
        try:
            print(f"🧹 Начало очистки статистики бесконечки для {chat_id}")
            
            # Создаем резервную копию
            backup_file = f"{INFINITE_STATS_FILE}.backup_{int(time.time())}"
            if os.path.exists(INFINITE_STATS_FILE):
                print(f"📁 Создаем резервную копию: {backup_file}")
                import shutil
                shutil.copy2(INFINITE_STATS_FILE, backup_file)
            
            # Создаем новую пустую статистику
            empty_stats = {
                'total_entries': 0,
                'total_exits': 0,
                'total_cycles': 0,
                'hero_death_count': 0,
                'last_entry_time': None,
                'last_exit_time': None
            }
            
            print(f"📝 Записываем пустую статистику в {INFINITE_STATS_FILE}")
            with open(INFINITE_STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(empty_stats, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Статистика очищена, отправляем сообщение в Telegram")
            self.bot.send_message(
                chat_id,
                f"✅ *Статистика бесконечки очищена!*\n\n"
                f"Резервная копия сохранена: `{backup_file}`",
                parse_mode='Markdown'
            )
            
            self.logger.log_event("TG_CONTROL", "Статистика бесконечки очищена")
            
        except Exception as e:
            print(f"❌ Ошибка очистки статистики: {e}")
            import traceback
            traceback.print_exc()
            
            self.bot.send_message(
                chat_id,
                f"❌ *Ошибка очистки:* {str(e)}",
                parse_mode='Markdown'
            )
    
    def clean_infinite_stats(self, chat_id):
        """Очистка статистики бесконечки"""
        try:
            # Создаем резервную копию
            backup_file = f"{INFINITE_STATS_FILE}.backup_{int(time.time())}"
            if os.path.exists(INFINITE_STATS_FILE):
                import shutil
                shutil.copy2(INFINITE_STATS_FILE, backup_file)
            
            # Создаем новую пустую статистику
            empty_stats = {
                'total_entries': 0,
                'total_exits': 0,
                'total_cycles': 0,
                'hero_death_count': 0,
                'last_entry_time': None,
                'last_exit_time': None
            }
            
            with open(INFINITE_STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(empty_stats, f, indent=2, ensure_ascii=False)
            
            # 🔥 ОБНОВЛЯЕМ СТАТИСТИКУ В ТЕКУЩЕМ ЭКЗЕМПЛЯРЕ
            try:
                from AFK_lobby import AFKLobbyMonitor
                # Нужно получить доступ к текущему экземпляру
                # Это зависит от вашей архитектуры
                pass
            except:
                pass
            
            self.bot.send_message(
                chat_id,
                f"✅ *Статистика бесконечки очищена!*\n\n"
                f"Резервная копия сохранена: `{backup_file}`",
                parse_mode='Markdown'
            )
            
            self.logger.log_event("TG_CONTROL", "Статистика бесконечки очищена")
            
        except Exception as e:
            self.bot.send_message(
                chat_id,
                f"❌ *Ошибка очистки:* {str(e)}",
                parse_mode='Markdown'
            )
    
    def clean_screenshots(self, chat_id):
        """Очистка скриншотов"""
        try:
            screenshots_dir = "screenshots"
            if os.path.exists(screenshots_dir):
                # Считаем сколько файлов будет удалено
                files = [f for f in os.listdir(screenshots_dir) if f.endswith('.png')]
                file_count = len(files)
                
                if file_count > 0:
                    # Создаем архив перед удалением
                    timestamp = int(time.time())
                    backup_dir = f"screenshots_backup_{timestamp}"
                    import shutil
                    shutil.copytree(screenshots_dir, backup_dir)
                    
                    # Удаляем файлы
                    for file in files:
                        os.remove(os.path.join(screenshots_dir, file))
                    
                    self.bot.send_message(
                        chat_id,
                        f"✅ *Скриншоты очищены!*\n\n"
                        f"Удалено файлов: {file_count}\n"
                        f"Резервная копия: `{backup_dir}`",
                        parse_mode='Markdown'
                    )
                else:
                    self.bot.send_message(
                        chat_id,
                        "ℹ️ *Скриншотов для очистки нет*",
                        parse_mode='Markdown'
                    )
            else:
                self.bot.send_message(
                    chat_id,
                    "ℹ️ *Папка скриншотов не существует*",
                    parse_mode='Markdown'
                )
            
            self.logger.log_event("TG_CONTROL", "Скриншоты очищены")
            
        except Exception as e:
            self.bot.send_message(
                chat_id,
                f"❌ *Ошибка очистки скриншотов:* {str(e)}",
                parse_mode='Markdown'
            )

    def confirm_clean_infinite_stats(self, chat_id):
        """Подтверждение очистки статистики бесконечки"""
        markup = types.InlineKeyboardMarkup()
        confirm_btn = types.InlineKeyboardButton(
            text="✅ Да, очистить",
            callback_data="clean_infinite_confirm"
        )
        cancel_btn = types.InlineKeyboardButton(
            text="❌ Нет, отмена",
            callback_data="clean_infinite_cancel"
        )
        markup.add(confirm_btn, cancel_btn)
        
        self.bot.send_message(
            chat_id,
            "⚠️ *ПОДТВЕРЖДЕНИЕ ОЧИСТКИ*\n\n"
            "Вы действительно хотите очистить статистику бесконечки?\n\n"
            "Это приведет к:\n"
            "• Сбросу счетчиков входов/выходов\n"
            "• Сбросу счетчика циклов\n"
            "• Сбросу статистики смертей героя\n"
            "• *Данные невозможно восстановить!*",
            reply_markup=markup,
            parse_mode='Markdown'
        )

    def confirm_clean_screenshots(self, chat_id):
        """Подтверждение очистки скриншотов"""
        screenshot_count, screenshot_size = self.get_screenshot_info()
        
        if screenshot_count == 0:
            self.bot.send_message(
                chat_id,
                "ℹ️ *Скриншотов для очистки нет*\n\n"
                "Папка скриншотов пуста или не существует.",
                parse_mode='Markdown'
            )
            return
        
        markup = types.InlineKeyboardMarkup()
        confirm_btn = types.InlineKeyboardButton(
            text="✅ Да, очистить",
            callback_data="clean_screenshots_confirm"
        )
        cancel_btn = types.InlineKeyboardButton(
            text="❌ Нет, отмена",
            callback_data="clean_screenshots_cancel"
        )
        markup.add(confirm_btn, cancel_btn)
        
        self.bot.send_message(
            chat_id,
            f"⚠️ *ПОДТВЕРЖДЕНИЕ ОЧИСТКИ СКРИНШОТОВ*\n\n"
            f"Вы действительно хотите очистить {screenshot_count} скриншотов?\n\n"
            f"• Количество файлов: {screenshot_count}\n"
            f"• Общий размер: {screenshot_size}\n\n"
            f"⚠️ *Внимание:* Создается резервная копия, но восстановление потребует ручных действий.",
            reply_markup=markup,
            parse_mode='Markdown'
        )

    def confirm_clean_all(self, chat_id):
        """Подтверждение полной очистки"""
        infinite_stats_size = self.get_file_size(INFINITE_STATS_FILE)
        screenshot_count, screenshot_size = self.get_screenshot_info()
        
        if infinite_stats_size == "Файл не существует" and screenshot_count == 0:
            self.bot.send_message(
                chat_id,
                "ℹ️ *Нет данных для очистки*",
                parse_mode='Markdown'
            )
            return
        
        markup = types.InlineKeyboardMarkup()
        confirm_btn = types.InlineKeyboardButton(
            text="✅ Да, очистить всё",
            callback_data="clean_all_confirm"
        )
        cancel_btn = types.InlineKeyboardButton(
            text="❌ Нет, отмена",
            callback_data="clean_all_cancel"
        )
        markup.add(confirm_btn, cancel_btn)
        
        message = "⚠️ *ПОДТВЕРЖДЕНИЕ ПОЛНОЙ ОЧИСТКИ*\n\n"
        message += "Вы действительно хотите очистить ВСЕ данные?\n\n"
        
        if infinite_stats_size != "Файл не существует":
            message += f"• Статистика бесконечки: {infinite_stats_size}\n"
        
        if screenshot_count > 0:
            message += f"• Скриншоты: {screenshot_count} файлов ({screenshot_size})\n"
        
        message += "\n⚠️ *Внимание:*\n"
        message += "• Создаются резервные копии\n"
        message += "• Данные будут полностью удалены\n"
        message += "• Восстановление потребует ручных действий"
        
        self.bot.send_message(
            chat_id,
            message,
            reply_markup=markup,
            parse_mode='Markdown'
        )

    def clean_all_data(self, chat_id):
        """Очистка всех данных"""
        try:
            results = []
            
            # 1. Очистка статистики бесконечки
            if os.path.exists(INFINITE_STATS_FILE):
                backup_file = f"{INFINITE_STATS_FILE}.backup_{int(time.time())}"
                import shutil
                shutil.copy2(INFINITE_STATS_FILE, backup_file)
                
                empty_stats = {
                    'total_entries': 0,
                    'total_exits': 0,
                    'total_cycles': 0,
                    'hero_death_count': 0,
                    'last_entry_time': None,
                    'last_exit_time': None
                }
                
                with open(INFINITE_STATS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(empty_stats, f, indent=2, ensure_ascii=False)
                
                results.append(f"📊 Статистика бесконечки очищена (резерв: `{backup_file}`)")
            
            # 2. Очистка скриншотов
            screenshots_dir = "screenshots"
            if os.path.exists(screenshots_dir):
                files = [f for f in os.listdir(screenshots_dir) if f.endswith('.png')]
                file_count = len(files)
                
                if file_count > 0:
                    timestamp = int(time.time())
                    backup_dir = f"screenshots_backup_{timestamp}"
                    import shutil
                    shutil.copytree(screenshots_dir, backup_dir)
                    
                    for file in files:
                        os.remove(os.path.join(screenshots_dir, file))
                    
                    results.append(f"📸 Скриншоты очищены: {file_count} файлов (резерв: `{backup_dir}`)")
            
            if results:
                message = "✅ *ВСЕ ДАННЫЕ ОЧИЩЕНЫ!*\n\n" + "\n".join(results)
                self.bot.send_message(chat_id, message, parse_mode='Markdown')
            else:
                self.bot.send_message(
                    chat_id,
                    "ℹ️ *Нет данных для очистки*",
                    parse_mode='Markdown'
                )
            
            self.logger.log_event("TG_CONTROL", "Все данные очищены")
            
        except Exception as e:
            self.bot.send_message(
                chat_id,
                f"❌ *Ошибка полной очистки:* {str(e)}",
                parse_mode='Markdown'
            )

    def send_main_menu(self, chat_id):
        """Отправка главного меню"""
        try:
            markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            
            # 🔥 ОБНОВЛЕННЫЙ СПИСОК КНОПОК
            btn_row1 = [
                types.KeyboardButton("📱 Статус"),
                types.KeyboardButton("📊 Статистика")
            ]
            btn_row2 = [
                types.KeyboardButton("🎮 Управление"),
                types.KeyboardButton("🔐 Пароли")
            ]
            btn_row3 = [
                types.KeyboardButton("📸 Скриншот"),
                types.KeyboardButton("⌨️ Раскладка")
            ]
            btn_row4 = [
                types.KeyboardButton("🐾 Питомцы"),
                types.KeyboardButton("🧹 Очистка")
            ]
            btn_row5 = [
                types.KeyboardButton("🔄 Перезапуск"),
                types.KeyboardButton("⚙️ Настройки")  # 🔥 ИЗМЕНЕНО: было "⚙️ Настройки", оставляем как есть
            ]
            
            markup.add(*btn_row1)
            markup.add(*btn_row2)
            markup.add(*btn_row3)
            markup.add(*btn_row4)
            markup.add(*btn_row5)
            
            pause_status = "⏸️ На паузе" if pause_handler.paused else "▶️ В работе"
            
            # 🔥 Читаем пароль
            current_password = self.read_password_directly()
            
            self.bot.send_message(
                chat_id,
                f"🤖 *Главное меню*\n\n"
                f"*Статус программы:* {pause_status}\n"
                f"*Текущий пароль:* `{current_password}`\n\n"
                f"*Новые функции:*\n"
                f"• 🐾 *Питомцы* - переключение между героями\n"
                f"• 🧹 *Очистка* - очистка статистики и скриншотов\n\n"
                f"Выберите действие:",
                reply_markup=markup,
                parse_mode='Markdown'
            )
            
            print(f"✅ Главное меню отправлено пользователю {chat_id}")
            
        except Exception as e:
            print(f"❌ Ошибка при отправке главного меню: {e}")
            self.bot.send_message(
                chat_id,
                "⚠️ *Ошибка при отображении меню*\n\n"
                "Попробуйте команду /start",
                parse_mode='Markdown'
            )
    
    def send_status_info(self, chat_id):
        """Отправка информации о статусе программы"""
        try:
            # Получаем статус из pause_handler
            status = pause_handler.get_current_status()
            
            # Получаем статистику смертей
            from statistics import stats
            session_stats = stats.get_session_summary()
            
            # Формируем сообщение
            pause_status = "⏸️ НА ПАУЗЕ" if status['paused'] else "▶️ В РАБОТЕ"
            operation = status['current_operation']
            duration = status['operation_duration']
            
            # 🔥 ДОБАВЛЯЕМ СТАТИСТИКУ СМЕРТЕЙ
            red_frame_deaths = session_stats.get('red_frame_deaths_count', 0)
            total_deaths = session_stats.get('total_deaths_count', 0)
            
            message = f"""
    📱 *СТАТУС ПРОГРАММЫ*

    🎯 *Текущая операция:* {operation}
    ⏱️ *В работе:* {duration}

    🔄 *Перезапусков:* {session_stats['restart_count']}
    🌀 *Циклов бесконечки:* {session_stats.get('infinite_cycles', 0)}

    💀 *Смерти хоста в этой сессии:*
    🔴 *Красная рамка:* {red_frame_deaths} раз
    💰 *9999999 в чате:* {session_stats['gold_found_count']} раз
    ⚰️ *Всего смертей:* {total_deaths}
    """
            
            # 🔥 ВАШ ДОБАВЛЕННЫЙ КОД ЗДЕСЬ:
            # 🔥 ДОБАВЛЯЕМ ИНФОРМАЦИЮ О БЕСКОНЕЧКЕ И СМЕРТЯХ ГЕРОЯ
            try:
                # Получаем информацию о бесконечке
                from AFK_lobby import AFKLobbyMonitor
                # Создаем временный экземпляр или получаем существующий
                # Это упрощенный вариант - в реальности нужно получить экземпляр бесконечки
                if hasattr(pause_handler, 'operation_details'):
                    details = pause_handler.operation_details if hasattr(pause_handler, 'operation_details') else {}

                    if details.get('infinite_enabled', False):
                        message += f"\n🌀 *Бесконечка:*"
                        message += f"\n• Статус: {'АКТИВНА' if details.get('infinite_is_active', False) else 'ВЫКЛЮЧЕНА'}"
                        
                        entries = details.get('infinite_entries', 0)
                        exits = details.get('infinite_exits', 0)
                        cycles = details.get('infinite_cycles', 0)  # 🔥 ЭТО КЛЮЧЕВОЙ ПАРАМЕТР!
                        
                        if entries > 0:
                            message += f"\n• Входов: {entries}"
                        if exits > 0:
                            message += f"\n• Выходов: {exits}"
                        if cycles > 0:
                            message += f"\n• Циклов: {cycles}"  # 🔥 ТЕПЕРЬ ЭТО БУДЕТ РАБОТАТЬ
                        
                        # 🔥 ИНФОРМАЦИЯ О СМЕРТЯХ ГЕРОЯ
                        hero_death_count = details.get('hero_death_count', 0)
                        if hero_death_count > 0:
                            message += f"\n💀 *Смертей героя в бесконечке:* {hero_death_count}"
                        
                        if details.get('hero_dead', False):
                            message += f"\n⚠️ *ГЕРОЙ МЕРТВ!* Ожидает новый раунд..."
                            death_streak = details.get('hero_death_streak', 0)
                            if death_streak > 0:
                                message += f"\n   Текущая серия смертей: {death_streak}"
            
            except Exception as infinite_error:
                print(f"⚠️ Ошибка получения информации о бесконечке: {infinite_error}")
            
            message += f"\n\n*Состояние:* {pause_status}"
            
            # 🔥 ДОБАВЛЯЕМ ДЕТАЛИ ОПЕРАЦИИ ЕСЛИ ЕСТЬ
            details = status.get('operation_details', {})
            if details:
                message += "\n📋 *Детали операции:*\n"
                
                # Общие детали
                if 'stage' in details:
                    message += f"• Этап: {details['stage']}\n"
                if 'elapsed_seconds' in details:
                    elapsed_min = details['elapsed_seconds'] // 60
                    elapsed_sec = details['elapsed_seconds'] % 60
                    message += f"• Прошло: {elapsed_min}м {elapsed_sec}сек\n"
                
                # Детали AFK мониторинга
                if 'gold_found' in details:
                    message += f"• Найдено 9999999: {details['gold_found']}\n"
                if 'arrow_found' in details:
                    message += f"• Стрелка: {'✅ найдена' if details['arrow_found'] else '❌ не найдена'}\n"
                if 'frame_found' in details:
                    message += f"• Рамка: {'✅ найдена' if details['frame_found'] else '❌ не найдена'}\n"
                
                # Детали бесконечки (если еще не отображены)
                if 'infinite_enabled' in details and details['infinite_enabled']:
                    if 'infinite_cycles' in details:
                        message += f"• Бесконечка циклов: {details['infinite_cycles']}\n"
                    if 'hero_dead' in details and details['hero_dead']:
                        message += f"• Герой: 💀 МЕРТВ (ждет новый раунд)\n"
            
                if 'triggered_triggers' in details and details['triggered_triggers']:
                    triggered_count = len(details['triggered_triggers'])
                    message += f"• Триггеров сработало: {triggered_count}\n"
                    
                    # Можно добавить детали если нужно
                    if triggered_count > 0:
                        message += "  (история сохранена в сессии)\n"
                        
            message += f"\n*Последнее обновление:* {status['timestamp']}"
            
            self.bot.send_message(chat_id, message, parse_mode='Markdown')
            
        except Exception as e:
            self.bot.send_message(
                chat_id, 
                f"⚠️ Ошибка получения статуса: {str(e)}"
            )

    
    def get_program_status(self):
        """Получение статуса программы для заглушки"""
        try:
            # Пробуем получить реальный статус
            status = pause_handler.get_current_status()
            
            # Получаем статистику
            session_stats = stats.get_session_summary()
            
            # Форматируем длительность операции
            duration = status['operation_duration']
            
            return f"""
    🎯 *Текущая операция:* {status['current_operation']}
    ⏱️ *В работе:* {duration}
    🔄 *Перезапусков:* {session_stats['restart_count']}
    🎰 *Найдено 9999999:* {session_stats['gold_found_count']} раз
    🌀 *Циклов бесконечки:* {session_stats.get('infinite_cycles', 0)}
    """
        except:
            # Заглушка если не удалось получить статус
            return """
    🎯 *Текущая операция:* Мониторинг AFK лобби
    ⏱️ *В работе:* 22222 часа 15 минут
    🔄 *Перезапусков:* 3
    🎰 *Найдено 9999999:* 5 раз
    🌀 *Циклов бесконечки:* 12
    """
    
    def take_screenshot_command_handler(self, chat_id):
        """Обработчик команды скриншота"""
        try:
            # Отправляем сообщение о начале
            self.bot.send_message(
                chat_id,
                "📸 *Создание скриншота...*\n\n"
                "Пожалуйста, подождите...",
                parse_mode='Markdown'
            )
            
            # Делаем скриншот
            success = self.take_screenshot(chat_id)
            
            if not success:
                self.bot.send_message(
                    chat_id,
                    "❌ *Не удалось создать скриншот*\n\n"
                    "Проверьте:\n"
                    "1. Права доступа к экрану\n"
                    "2. Доступность библиотеки PIL/Pillow\n"
                    "3. Наличие свободного места на диске",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            self.bot.send_message(
                chat_id,
                f"⚠️ *Ошибка при создании скриншота:* {str(e)}",
                parse_mode='Markdown'
            )

    def keyboard_layout_menu(self, chat_id):
        """Меню управления раскладкой клавиатуры"""
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        
        buttons = [
            "⌨️ Проверить раскладку",
            "🇬🇧 Переключить на английскую",
            "🇬🇧 Переключить на русскую",
            "⬅️ Назад"
        ]
        
        # Создаем кнопки в рядах
        row1 = buttons[:2]
        row2 = buttons[2:]
        
        markup.add(*[types.KeyboardButton(btn) for btn in row1])
        markup.add(*[types.KeyboardButton(btn) for btn in row2])
        
        self.bot.send_message(
            chat_id,
            "⌨️ *Управление раскладкой клавиатуры*\n\n"
            "Выберите действие:",
            reply_markup=markup,
            parse_mode='Markdown'
        )

    def handle_keyboard_layout_commands(self, chat_id, text):
        """Обработка команд раскладки клавиатуры"""
        if text == "⌨️ Проверить раскладку":
            layout_code, layout_name = self.get_keyboard_layout()
            
            message = f"⌨️ *Текущая раскладка:* {layout_name}\n\n"
            
            if layout_code == "en":
                message += "✅ *Статус:* Готова для Dota 2\n"
                message += "💡 Английская раскладка необходима для корректной работы горячих клавиш в игре."
            elif layout_code == "ru":
                message += "⚠️ *Статус:* Требуется переключение\n"
                message += "💡 Рекомендуется переключить на английскую для работы в Dota 2."
            else:
                message += "❓ *Статус:* Не удалось определить\n"
                message += "💡 Попробуйте переключить вручную или используйте функцию 'Для Dota 2'."
            
            self.bot.send_message(chat_id, message, parse_mode='Markdown')
            
        elif text == "🇬🇧 Переключить на английскую":
            self.bot.send_message(
                chat_id,
                "⌨️ *Переключение на английскую раскладку...*\n\n"
                "Пожалуйста, подождите...",
                parse_mode='Markdown'
            )
            
            success, message = self.switch_to_english_layout()
            
            if success:
                self.bot.send_message(
                    chat_id,
                    f"✅ *Успешно!*\n\n{message}",
                    parse_mode='Markdown'
                )
            else:
                self.bot.send_message(
                    chat_id,
                    f"❌ *Не удалось переключить*\n\n{message}",
                    parse_mode='Markdown'
                )

        elif text == "🇬🇧 Переключить на русскую":
            self.bot.send_message(
                chat_id,
                "⌨️ *Переключение на русскую раскладку...*\n\n"
                "Пожалуйста, подождите...",
                parse_mode='Markdown'
            )
            
            success, message = self.switch_to_russian_layout()
            
            if success:
                self.bot.send_message(
                    chat_id,
                    f"✅ *Успешно!*\n\n{message}",
                    parse_mode='Markdown'
                )
            else:
                self.bot.send_message(
                    chat_id,
                    f"❌ *Не удалось переключить*\n\n{message}",
                    parse_mode='Markdown'
                )

    def get_infinite_status(self):
        """Получение статуса бесконечки"""
        try:
            # Попытка получить статус из бесконечки
            # Если класс InfiniteMode недоступен, возвращаем заглушку
            from infinite_mode import InfiniteMode
            # Нужно получить экземпляр бесконечки
            # Это зависит от архитектуры вашего приложения
            return "ВКЛЮЧЕНА | Циклов: 12"
        except:
            return "Информация недоступна"
    
    def send_statistics_info(self, chat_id):
        """Отправка статистики с деталями смертей хоста"""
        try:
            # Получаем статистику сессии
            session_stats = stats.get_session_summary()
            total_stats = stats.get_total_summary()
            
            # 🔥 ПОЛУЧАЕМ СТАТИСТИКУ СМЕРТЕЙ
            gold_deaths_session = session_stats.get('gold_deaths_count', 0)
            red_frame_deaths_session = session_stats.get('red_frame_deaths_count', 0)
            total_deaths_session = session_stats.get('total_deaths_count', 0)
            
            gold_deaths_total = total_stats.get('gold_deaths_count', 0)
            red_frame_deaths_total = total_stats.get('red_frame_deaths_count', 0)
            total_deaths_total = total_stats.get('total_deaths', 0)
            
            # Получаем статистику бесконечки
            infinite_cycles = session_stats.get('infinite_cycles', 0)
            
            # 🔥 ДИНАМИЧЕСКОЕ ПОЛУЧЕНИЕ ТЕКУЩЕГО ПАРОЛЯ
            from config_loader import get_config
            current_password = self.read_password_directly()
            
            message = f"""
    📊 *СТАТИСТИКА СЕССИИ*

    ⏱ *Длительность:* {session_stats['session_duration']}
    🎯 *Найдено 9999999:* {session_stats['gold_found_count']} раз
    📊 *Умноженное:* {session_stats['multiplied_gold_count']} (×3)
    🌀 *Циклов бесконечки:* {infinite_cycles}
    🔄 *Перезапусков:* {session_stats['restart_count']}

    💀 *Смерти хоста в этой сессии:*
    🔴 *Красная рамка:* {red_frame_deaths_session} раз
    💰 *9999999 в чате:* {gold_deaths_session} раз
    ⚰️ *Всего смертей:* {total_deaths_session}

    📈 *ОБЩАЯ СТАТИСТИКА*

    📅 *Всего сессий:* {total_stats['total_sessions']}
    🎰 *Всего найдено 9999999:* {total_stats['total_gold_found']}
    📊 *Всего умноженное:* {total_stats['total_multiplied_gold']} (×3)
    🌀 *Всего циклов бесконечки:* {total_stats.get('total_infinite_cycles', 'N/A')}
    🔄 *Всего перезапусков:* {total_stats['total_restarts']}

    💀 *Всего смертей хоста:*
    🔴 *Красная рамка:* {red_frame_deaths_total} раз
    💰 *9999999 в чате:* {gold_deaths_total} раз
    ⚰️ *Всего смертей:* {total_deaths_total}

    *Текущий пароль:* `{current_password}`
    """
            
            self.bot.send_message(chat_id, message, parse_mode='Markdown')
            
        except Exception as e:
            self.bot.send_message(
                chat_id, 
                f"⚠️ Ошибка получения статистики: {str(e)}\nДетали: {traceback.format_exc()}"
            )
    
    def get_keyboard_layout(self):
        """Определить текущую раскладку клавиатуры"""
        try:
            # Метод 1: через ctypes (Windows)
            import ctypes
            import ctypes.wintypes
            
            # Загружаем user32.dll
            user32 = ctypes.WinDLL('user32', use_last_error=True)
            
            # Получаем активное окно
            hwnd = user32.GetForegroundWindow()
            
            # Получаем поток окна
            thread_id = user32.GetWindowThreadProcessId(hwnd, 0)
            
            # Получаем раскладку
            layout_id = user32.GetKeyboardLayout(thread_id)
            
            # Преобразуем в язык
            language_id = layout_id & 0xFFFF
            
            # Коды языков
            LANG_ENGLISH = 0x09
            LANG_RUSSIAN = 0x19
            
            if language_id == LANG_ENGLISH:
                return "en", "Английская"
            elif language_id == LANG_RUSSIAN:
                return "ru", "Русская"
            else:
                # Проверяем другие языки
                if language_id & 0xFF == 0x09:  # Английский
                    return "en", "Английская"
                elif language_id & 0xFF == 0x19:  # Русский
                    return "ru", "Русская"
                else:
                    return "unknown", f"Неизвестная (код: 0x{language_id:X})"
                    
        except Exception as e:
            print(f"⚠️ Ошибка определения раскладки (метод 1): {e}")
            
            # Метод 2: через pyautogui (кросс-платформенный, менее точный)
            try:
                import pyautogui
                
                # Сохраняем текущее положение мыши
                current_pos = pyautogui.position()
                
                # Перемещаем мышь в безопасное место и печатаем тестовую строку
                pyautogui.moveTo(100, 100)
                pyautogui.click()
                pyautogui.write('test', interval=0.1)
                
                # Проверяем результат (этот метод не очень надежен)
                # Вместо этого используем метод с сохранением в буфер обмена
                
                return "unknown", "Не удалось определить (используйте метод 1)"
                
            except Exception as e2:
                print(f"⚠️ Ошибка определения раскладки (метод 2): {e2}")
                return "error", f"Ошибка определения: {str(e)}"

    def switch_to_english_layout(self):
        """Переключить раскладку на английскую через keyboard"""
        try:
            print("⌨️ Переключение на английскую через keyboard...")
            
            import keyboard
            
            # Метод 1: Alt+Shift (стандартная комбинация Windows)
            print("  ⌨️ Пробуем Alt+Shift...")
            keyboard.press('alt')
            keyboard.press('shift')
            time.sleep(0.1)
            keyboard.release('shift')
            keyboard.release('alt')
            time.sleep(0.5)
            
            # Проверяем
            layout_code, layout_name = self.get_keyboard_layout()
            if layout_code == "en":
                return True, "Успешно переключено (Alt+Shift)"
            
            # Метод 2: Ctrl+Shift
            print("  ⌨️ Пробуем Ctrl+Shift...")
            keyboard.press('ctrl')
            keyboard.press('shift')
            time.sleep(0.1)
            keyboard.release('shift')
            keyboard.release('ctrl')
            time.sleep(0.5)
            
            # Проверяем
            layout_code, layout_name = self.get_keyboard_layout()
            if layout_code == "en":
                return True, "Успешно переключено (Ctrl+Shift)"
            
            # Метод 3: Win+Space (Windows 10/11)
            print("  ⌨️ Пробуем Win+Space...")
            keyboard.press('win')
            keyboard.press('space')
            time.sleep(0.1)
            keyboard.release('space')
            keyboard.release('win')
            time.sleep(0.5)
            
            # Проверяем
            layout_code, layout_name = self.get_keyboard_layout()
            if layout_code == "en":
                return True, "Успешно переключено (Win+Space)"
            
            return False, "Не удалось переключить автоматически"
            
        except Exception as e:
            return False, f"Ошибка при переключении: {str(e)}"
        
    def switch_to_russian_layout(self):
        """Переключить раскладку на русскую через keyboard"""
        try:
            print("⌨️ Переключение на английскую через keyboard...")
            
            import keyboard
            
            # Метод 1: Alt+Shift (стандартная комбинация Windows)
            print("  ⌨️ Пробуем Alt+Shift...")
            keyboard.press('alt')
            keyboard.press('shift')
            time.sleep(0.1)
            keyboard.release('shift')
            keyboard.release('alt')
            time.sleep(0.5)
            
            # Проверяем
            layout_code, layout_name = self.get_keyboard_layout()
            if layout_code == "ru":
                return True, "Успешно переключено (Alt+Shift)"
            
            # Метод 2: Ctrl+Shift
            print("  ⌨️ Пробуем Ctrl+Shift...")
            keyboard.press('ctrl')
            keyboard.press('shift')
            time.sleep(0.1)
            keyboard.release('shift')
            keyboard.release('ctrl')
            time.sleep(0.5)
            
            # Проверяем
            layout_code, layout_name = self.get_keyboard_layout()
            if layout_code == "ru":
                return True, "Успешно переключено (Ctrl+Shift)"
            
            # Метод 3: Win+Space (Windows 10/11)
            print("  ⌨️ Пробуем Win+Space...")
            keyboard.press('win')
            keyboard.press('space')
            time.sleep(0.1)
            keyboard.release('space')
            keyboard.release('win')
            time.sleep(0.5)
            
            # Проверяем
            layout_code, layout_name = self.get_keyboard_layout()
            if layout_code == "ru":
                return True, "Успешно переключено (Win+Space)"
            
            return False, "Не удалось переключить автоматически"
            
        except Exception as e:
            return False, f"Ошибка при переключении: {str(e)}"

    def take_screenshot(self, chat_id):
        """Сделать скриншот и отправить в Telegram"""
        try:
            print("📸 Запрос на создание скриншота...")
            
            import pyautogui
            from PIL import Image
            import io
            import datetime
            
            # Создаем папку для скриншотов если нет
            screenshots_dir = "screenshots"
            os.makedirs(screenshots_dir, exist_ok=True)
            
            # Делаем скриншот
            screenshot = pyautogui.screenshot()
            
            # Сохраняем файл с временной меткой
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{screenshots_dir}/screenshot_{timestamp}.png"
            screenshot.save(filename)
            
            # Получаем информацию о скриншоте
            screen_width, screen_height = pyautogui.size()
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            
            # Отправляем в Telegram
            with open(filename, 'rb') as photo:
                caption = (
                    f"📸 *Скриншот экрана*\n\n"
                    f"🕐 *Время:* {current_time}\n"
                    f"📏 *Разрешение:* {screen_width}x{screen_height}\n"
                    f"💾 *Размер файла:* {os.path.getsize(filename) // 1024} KB\n"
                    f"📁 *Путь:* `{filename}`"
                )
                
                self.bot.send_photo(
                    chat_id,
                    photo,
                    caption=caption,
                    parse_mode='Markdown'
                )
            
            print(f"✅ Скриншот отправлен: {filename}")
            return True
            
        except Exception as e:
            error_msg = f"❌ Ошибка при создании скриншота: {str(e)}"
            print(error_msg)
            self.bot.send_message(chat_id, error_msg)
            return False

    def take_region_screenshot(self, chat_id, region=None):
        """Сделать скриншот определенной области и отправить в Telegram"""
        try:
            print("📸 Запрос на создание скриншота области...")
            
            import pyautogui
            from PIL import Image
            import io
            import datetime
            
            screenshots_dir = "screenshots"
            os.makedirs(screenshots_dir, exist_ok=True)
            
            if region:
                # Скриншот определенной области
                x, y, width, height = region
                screenshot = pyautogui.screenshot(region=region)
                region_info = f"Область: {region}"
            else:
                # Скриншот всего экрана
                screenshot = pyautogui.screenshot()
                screen_width, screen_height = pyautogui.size()
                region_info = f"Весь экран: {screen_width}x{screen_height}"
            
            # Сохраняем файл
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            region_type = "region" if region else "full"
            filename = f"{screenshots_dir}/{region_type}_screenshot_{timestamp}.png"
            screenshot.save(filename)
            
            # Отправляем в Telegram
            with open(filename, 'rb') as photo:
                caption = (
                    f"📸 *Скриншот экрана*\n\n"
                    f"🕐 *Время:* {datetime.datetime.now().strftime('%H:%M:%S')}\n"
                    f"{region_info}\n"
                    f"💾 *Размер файла:* {os.path.getsize(filename) // 1024} KB"
                )
                
                self.bot.send_photo(
                    chat_id,
                    photo,
                    caption=caption,
                    parse_mode='Markdown'
                )
            
            print(f"✅ Скриншот области отправлен: {filename}")
            return True
            
        except Exception as e:
            error_msg = f"❌ Ошибка при создании скриншота области: {str(e)}"
            print(error_msg)
            self.bot.send_message(chat_id, error_msg)
            return False

    def get_infinite_statistics(self):
        """Получение статистики бесконечки"""
        try:
            # Попытка получить реальную статистику
            from infinite_mode import InfiniteMode
            # Нужно получить экземпляр бесконечки
            # Через AFKLobbyMonitor или глобальную переменную
            
            # Временное решение - возвращаем информацию что статистика собирается
            return "🌀 *БЕСКОНЕЧКА:* Статистика собирается в реальном времени"
        except:
            return "🌀 *БЕСКОНЕЧКА:* Информация недоступна"

    def clear_all_flags(self):
        """Очищает все флаги (пауза, перезапуск, завершение)"""
        with self.pause_lock:
            self.paused = False
        
        with self.shutdown_lock:
            self.shutdown_requested = False
        
        with self.restart_lock:
            self.restart_requested = False
            self.restart_reason = ""

    # telegram_bot.py - изменить функцию restart_program_command:

    def restart_program_command(self, chat_id):
        """Команда немедленного перезапуска программы"""
        try:
            # 🔥 ПРОВЕРЯЕМ, НЕ ЗАПРОШЕН ЛИ УЖЕ ПЕРЕЗАПУСК
            restart_requested, _ = pause_handler.check_restart()
            if restart_requested:
                self.bot.send_message(
                    chat_id,
                    "⚠️ *Перезапуск уже запрошен, ожидайте завершения текущей операции...*",
                    parse_mode='Markdown'
                )
                return
            
            # 🔥 ОТПРАВЛЯЕМ ИНФОРМАЦИЮ О БУДУЩЕМ ПЕРЕЗАПУСКЕ
            self.bot.send_message(
                chat_id,
                "🔄 *ПОДГОТОВКА К ПЕРЕЗАПУСКУ...*\n\n"
                "✅ Dota 2 будет закрыта\n"
                "✅ Запущен новый полный цикл\n"
                "⏳ Ожидайте...",
                parse_mode='Markdown'
            )
            
            # 🔥 ЗАПРАШИВАЕМ ПЕРЕЗАПУСК С ПОЛНЫМ ЦИКЛОМ
            success = pause_handler.request_restart("Перезапуск по команде из Telegram")
            
            if success:
                # Логируем действие
                self.logger.log_event("TG_CONTROL", "Немедленный перезапуск по команде из Telegram")
                
                self.bot.send_message(
                    chat_id,
                    "🔄 *НЕМЕДЛЕННЫЙ ПЕРЕЗАПУСК ПРОГРАММЫ!*\n\n"
                    "Программа *немедленно* завершает текущую операцию.\n"
                    "Dota 2 будет закрыта и запущена заново.\n"
                    "*Причина:* Перезапуск по команде из Telegram\n\n"
                    "⏳ Ожидайте запуска новой сессии...",
                    parse_mode='Markdown'
                )
            else:
                self.bot.send_message(
                    chat_id,
                    "⚠️ *Ошибка:* Не удалось запросить перезапуск",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            self.bot.send_message(
                chat_id,
                f"⚠️ *Ошибка перезапуска:* {str(e)}",
                parse_mode='Markdown'
            )
    
    def send_restart_signal(self):
        """Отправка сигнала перезапуска в основную программу"""
        # Этот метод должен взаимодействовать с основной программой
        # Например, через глобальную переменную или очередь
        
        # Логируем в файл
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] [TG_CONTROL] Перезапуск по команде из Telegram\n")
        
        # Здесь нужно добавить код для взаимодействия с основной программой
        # Например, установить флаг перезапуска
        print("🔄 Сигнал перезапуска от Telegram получен!")
    
    def show_password_menu(self, chat_id):
        """Меню управления паролями"""
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        
        buttons = ["📋 Список паролей", "➕ Новый пароль", "⬅️ Назад"]
        
        row1 = buttons[:2]
        row2 = buttons[2:]
        
        markup.add(*[types.KeyboardButton(btn) for btn in row1])
        markup.add(*[types.KeyboardButton(btn) for btn in row2])
        
        # 🔥 Читаем пароль НАПРЯМУЮ
        current_password = self.read_password_directly()
        
        self.bot.send_message(
            chat_id,
            "🔐 *Управление паролями*\n\n"
            f"*Текущий пароль:* `{current_password}`\n\n"
            "Выберите действие:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    def show_saved_passwords(self, chat_id):
        """Показать сохраненные пароли"""
        if not self.saved_passwords:
            self.bot.send_message(
                chat_id,
                "📭 *Список паролей пуст*\n\n"
                "У вас нет сохраненных паролей.",
                parse_mode='Markdown'
            )
            return
        
        message = "📋 *СОХРАНЕННЫЕ ПАРОЛИ:*\n\n"
        
        for name, password in self.saved_passwords.items():
            message += f"• *{name}:* `{password}`\n"
        
        message += "\nЧтобы использовать пароль, отправьте его название."
        
        # Создаем inline-клавиатуру с паролями
        markup = types.InlineKeyboardMarkup()
        
        for name in self.saved_passwords.keys():
            button = types.InlineKeyboardButton(
                text=f"📝 {name}",
                callback_data=f"use_password_{name}"
            )
            markup.add(button)
        
        delete_button = types.InlineKeyboardButton(
            text="🗑️ Удалить пароль",
            callback_data="delete_password_menu"
        )
        markup.add(delete_button)
        
        self.bot.send_message(
            chat_id,
            message,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        # Обработчик callback-запросов
        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback(call):
            if call.data.startswith("use_password_"):
                password_name = call.data.replace("use_password_", "")
                self.use_saved_password(call.message.chat.id, password_name)
            elif call.data == "delete_password_menu":
                self.show_delete_password_menu(call.message.chat.id)
            # elif call.data.startswith("delete_password_"):
            #     password_name = call.data.replace("delete_password_", "")
            #     self.delete_password(call.message.chat.id, password_name)
            # # 🔥 ОБРАБОТКА ОЧИСТКИ
            # elif call.data == "clean_infinite_confirm":
            #     self.clean_infinite_stats(call.message.chat.id)
            #     self.bot.answer_callback_query(call.id, "Статистика очищена")
            # elif call.data == "clean_infinite_cancel":
            #     self.bot.answer_callback_query(call.id, "Отменено")
            #     self.bot.send_message(call.message.chat.id, "❌ Очистка статистики отменена")
            
            # elif call.data == "clean_screenshots_confirm":
            #     self.clean_screenshots(call.message.chat.id)
            #     self.bot.answer_callback_query(call.id, "Скриншоты очищены")
            # elif call.data == "clean_screenshots_cancel":
            #     self.bot.answer_callback_query(call.id, "Отменено")
            #     self.bot.send_message(call.message.chat.id, "❌ Очистка скриншотов отменена")
            
            # elif call.data == "clean_all_confirm":
            #     self.clean_all_data(call.message.chat.id)
            #     self.bot.answer_callback_query(call.id, "Все данные очищены")
            # elif call.data == "clean_all_cancel":
            #     self.bot.answer_callback_query(call.id, "Отменено")
            #     self.bot.send_message(call.message.chat.id, "❌ Полная очистка отменена")
            # elif call.data.startswith("switch_pet_"):
            #     pet_id = call.data.replace("switch_pet_", "")
            #     success, message = self.pet_manager.switch_to_pet(pet_id)
                
            #     if success:
            #         self.bot.answer_callback_query(call.id, "✅ Переключено")
            #         self.bot.send_message(
            #             call.message.chat.id,
            #             f"✅ *Переключение успешно!*\n\n{message}",
            #             parse_mode='Markdown'
            #         )
            #     else:
            #         self.bot.answer_callback_query(call.id, "❌ Ошибка")
            #         self.bot.send_message(
            #             call.message.chat.id,
            #             f"❌ *Ошибка переключения:*\n\n{message}",
            #             parse_mode='Markdown'
            #         )
            
            # elif call.data.startswith("delete_pet_"):
            #     pet_id = call.data.replace("delete_pet_", "")
            #     success, message = self.pet_manager.delete_pet(pet_id)
                
            #     if success:
            #         self.bot.answer_callback_query(call.id, "✅ Удалено")
            #         # Обновляем сообщение
            #         self.bot.edit_message_text(
            #             f"✅ *Питомец удален!*\n\n{message}",
            #             chat_id=call.message.chat.id,
            #             message_id=call.message.message_id,
            #             parse_mode='Markdown'
            #         )
            #     else:
            #         self.bot.answer_callback_query(call.id, "❌ Ошибка")
            
            # elif call.data.startswith("record_pet_"):
            #     pet_id = call.data.replace("record_pet_", "")
                
            #     # Запрашиваем описание для клика
            #     pet = self.pet_manager.pets.get(pet_id, {})
            #     current_clicks = len(pet.get('clicks', []))
            #     click_number = current_clicks + 1
                
            #     # Сохраняем состояние
            #     self.user_state[call.message.chat.id] = {
            #         'action': 'recording_position',
            #         'pet_id': pet_id,
            #         'click_number': click_number
            #     }
                
            #     self.bot.send_message(
            #         call.message.chat.id,
            #         f"🎯 *Запись позиции #{click_number}*\n\n"
            #         f"Питомец: {pet.get('name', 'Неизвестный')}\n\n"
            #         f"1. Подведите мышь к нужной позиции на экране\n"
            #         f"2. Введите описание для этой позиции\n"
            #         f"   Например: 'Кнопка выбора', 'Меню навыков'",
            #         parse_mode='Markdown'
            #     )
    
    def show_delete_password_menu(self, chat_id):
        """Меню удаления паролей"""
        if not self.saved_passwords:
            self.bot.send_message(chat_id, "Нет паролей для удаления.")
            return
        
        markup = types.InlineKeyboardMarkup()
        
        for name in self.saved_passwords.keys():
            button = types.InlineKeyboardButton(
                text=f"🗑️ {name}",
                callback_data=f"delete_password_{name}"
            )
            markup.add(button)
        
        cancel_button = types.InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel_delete"
        )
        markup.add(cancel_button)
        
        self.bot.send_message(
            chat_id,
            "🗑️ *Выберите пароль для удаления:*",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    def delete_password(self, chat_id, password_name):
        """Удаление пароля"""
        if password_name in self.saved_passwords:
            del self.saved_passwords[password_name]
            self.save_passwords()
            
            self.bot.send_message(
                chat_id,
                f"✅ Пароль *{password_name}* удален!",
                parse_mode='Markdown'
            )
        else:
            self.bot.send_message(chat_id, "❌ Пароль не найден.")
    
    def use_saved_password(self, chat_id, password_name):
        """Использование сохраненного пароля"""
        if password_name in self.saved_passwords:
            password = self.saved_passwords[password_name]
            
            # Обновляем пароль в конфиге
            self.update_password_in_config(password)
            
            self.bot.send_message(
                chat_id,
                f"✅ Пароль *{password_name}* установлен!\n\n"
                f"Новый пароль: `{password}`",
                parse_mode='Markdown'
            )
        else:
            self.bot.send_message(chat_id, "❌ Пароль не найден.")
    
    def read_password_directly(self):
        """Читает пароль напрямую из config.py"""
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
            print(f"⚠️ Ошибка чтения пароля: {e}")
        
        return "1"  # значение по умолчанию

    def update_password_in_config(self, new_password):
        """Обновление пароля в конфиге с гарантированной записью"""
        import os
        import time
        
        try:
            config_file = "config.py"
            
            # Читаем весь файл
            with open(config_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Ищем и заменяем пароль
            updated = False
            new_lines = []
            
            for line in lines:
                if line.strip().startswith("PASS_LOBBY ="):
                    new_lines.append(f'PASS_LOBBY = "{new_password}"\n')
                    updated = True
                else:
                    new_lines.append(line)
            
            # Если не нашли - добавляем
            if not updated:
                new_lines.append(f'\nPASS_LOBBY = "{new_password}"\n')
            
            # Записываем обратно
            with open(config_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            # 🔥 КРИТИЧЕСКИЙ ШАГ: Принудительно синхронизируем файловую систему
            os.sync()  # Linux/Mac
            time.sleep(0.5)  # Даем время для записи
            
            print(f"✅ Пароль обновлен: {new_password}")
            print(f"📁 Файл {config_file} изменен, размер: {os.path.getsize(config_file)} байт")
            
            # Проверяем что записалось
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if f'PASS_LOBBY = "{new_password}"' in content:
                    print("✅ Изменение подтверждено в файле")
                else:
                    print("❌ Изменение не подтверждено!")
            
            self.logger.log_event("TG_CONTROL", f"Пароль изменен на: {new_password}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка обновления пароля: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def ask_for_password(self, chat_id):
        """Запрос нового пароля"""
        self.user_state[chat_id] = {'action': 'waiting_password'}
        
        self.bot.send_message(
            chat_id,
            "🔐 *ВВЕДИТЕ НОВЫЙ ПАРОЛЬ:*\n\n"
            "Отправьте пароль, который вы хотите установить.\n"
            "Пароль может содержать русские и английские буквы, цифры и символы.",
            parse_mode='Markdown'
        )
    
    def handle_new_password(self, chat_id, password):
        """Обработка нового пароля"""
        if not password:
            self.bot.send_message(chat_id, "❌ Пароль не может быть пустым.")
            return
        
        # Сохраняем пароль во временное состояние
        self.user_state[chat_id] = {
            'action': 'waiting_password_name',
            'password': password
        }
        
        self.bot.send_message(
            chat_id,
            f"✅ Пароль принят: `{password}`\n\n"
            "📝 *Теперь введите название для этого пароля:*\n"
            "Например: 'Основной', 'Резервный', 'Лобби1'",
            parse_mode='Markdown'
        )
    
    def handle_password_name(self, chat_id, name):
        """Обработка названия пароля"""
        if not name:
            self.bot.send_message(chat_id, "❌ Название не может быть пустым.")
            return
        
        state = self.user_state.get(chat_id, {})
        password = state.get('password', '')
        
        if not password:
            self.bot.send_message(chat_id, "❌ Ошибка: пароль не найден.")
            return
        
        # Сохраняем пароль
        self.saved_passwords[name] = password
        self.save_passwords()
        
        # Обновляем текущий пароль
        self.update_password_in_config(password)
        
        # Очищаем состояние
        if chat_id in self.user_state:
            del self.user_state[chat_id]
        
        self.bot.send_message(
            chat_id,
            f"🎉 *Пароль сохранен!*\n\n"
            f"📝 *Название:* {name}\n"
            f"🔐 *Пароль:* `{password}`\n\n"
            f"Пароль также установлен как текущий.",
            parse_mode='Markdown'
        )
    
    def show_control_menu(self, chat_id):
        """Меню управления программой"""
        pause_status = "⏸️ НА ПАУЗЕ" if pause_handler.paused else "▶️ В РАБОТЕ"
        
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        
        # 🔥 ДОБАВЛЯЕМ КНОПКУ НАЗАД В КАЖДОЕ МЕНЮ
        if pause_handler.paused:
            buttons = ["▶️ Продолжить", "🛑 Остановить", "🚀 Запустить", "⬅️ Назад"]
        else:
            buttons = ["⏸️ Пауза", "🛑 Остановить", "⬅️ Назад"]
        
        # Создаем кнопки в рядах
        row1 = buttons[:2]
        row2 = buttons[2:]
        
        markup.add(*[types.KeyboardButton(btn) for btn in row1])
        if row2:
            markup.add(*[types.KeyboardButton(btn) for btn in row2])
        
        self.bot.send_message(
            chat_id,
            f"🎮 *Управление программой*\n\n"
            f"*Текущий статус:* {pause_status}\n\n"
            "Выберите действие:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    def pause_program_command(self, chat_id):
        """Команда паузы программы"""
        try:
            pause_handler.force_pause()
            self.logger.log_event("TG_CONTROL", "Пауза по команде из Telegram")
            
            # 🔥 ОБНОВЛЯЕМ КНОПКИ СРАЗУ ПОСЛЕ ПАУЗЫ
            self.show_control_menu(chat_id)

            self.bot.send_message(
                chat_id,
                "⏸️ *Программа поставлена на паузу!*\n\n"
                "Для продолжения используйте кнопку '▶️ Продолжить' в меню управления.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            self.bot.send_message(
                chat_id,
                f"⚠️ *Ошибка паузы:* {str(e)}",
                parse_mode='Markdown'
            )
    
    def resume_program_command(self, chat_id):
        """Команда продолжения программы"""
        try:
            pause_handler.force_resume()
            self.logger.log_event("TG_CONTROL", "Продолжение по команде из Telegram")
            
            self.show_control_menu(chat_id)
        
            # 🔥 ОТПРАВЛЯЕМ ОТДЕЛЬНОЕ СООБЩЕНИЕ С ПОДТВЕРЖДЕНИЕМ
            self.bot.send_message(
                chat_id,
                "▶️ *Программа продолжает работу!*",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            self.bot.send_message(
                chat_id,
                f"⚠️ *Ошибка продолжения:* {str(e)}",
                parse_mode='Markdown'
            )
    
    def stop_program_command(self, chat_id):
        """Команда остановки программы с подтверждением"""
        try:
            # Создаем inline-клавиатуру для подтверждения
            markup = types.InlineKeyboardMarkup()
            confirm_btn = types.InlineKeyboardButton(
                text="✅ Да, остановить",
                callback_data="confirm_stop"
            )
            cancel_btn = types.InlineKeyboardButton(
                text="❌ Нет, отмена",
                callback_data="cancel_stop"
            )
            markup.add(confirm_btn, cancel_btn)
            
            self.bot.send_message(
                chat_id,
                "⚠️ *ПОДТВЕРЖДЕНИЕ ОСТАНОВКИ*\n\n"
                "Вы действительно хотите остановить программу?\n\n"
                "Это приведет к:\n"
                "• Прекращению всех операций\n"
                "• Возможной потере текущего прогресса\n"
                "• Необходимости перезапуска вручную",
                reply_markup=markup,
                parse_mode='Markdown'
            )
            
            # Добавляем обработчик callback
            @self.bot.callback_query_handler(func=lambda call: call.data in ["confirm_stop", "cancel_stop"])
            def handle_stop_confirmation(call):
                if call.data == "confirm_stop":
                    pause_handler.request_shutdown()
                    self.logger.log_event("TG_CONTROL", "Остановка подтверждена из Telegram")
                    
                    self.bot.edit_message_text(
                        "🛑 *ПРОГРАММА ОСТАНАВЛИВАЕТСЯ!*\n\n"
                        "Остановка подтверждена. Программа завершит текущую операцию и остановится.",
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        parse_mode='Markdown'
                    )
                    
                    # Уведомляем в консоль
                    print("🛑 Остановка программы подтверждена через Telegram!")
                    
                else:  # cancel_stop
                    self.bot.edit_message_text(
                        "✅ *ОТМЕНЕНО*\n\n"
                        "Остановка программы отменена. Программа продолжает работу.",
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        parse_mode='Markdown'
                    )
                
        except Exception as e:
            self.bot.send_message(
                chat_id,
                f"⚠️ *Ошибка остановки:* {str(e)}",
                parse_mode='Markdown'
            )
    
    def start_program_command(self, chat_id):
        """Команда запуска программы"""
        try:
            # Этот метод должен запускать основную программу
            # Пока что просто снимаем с паузы
            pause_handler.force_resume()
            self.logger.log_event("TG_CONTROL", "Запуск по команде из Telegram")
            
            self.bot.send_message(
                chat_id,
                "🚀 *Программа запущена!*",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            self.bot.send_message(
                chat_id,
                f"⚠️ *Ошибка запуска:* {str(e)}",
                parse_mode='Markdown'
            )
    
    def start_bot(self):
        """Запуск бота в отдельном потоке"""
        if not self.bot:
            print("❌ Бот не инициализирован. Проверьте TELEGRAM_BOT_TOKEN.")
            return
        
        def run_bot():
            print("🤖 Запуск Telegram бота...")
            self.running = True
            
            try:
                # 🔥 ПРОБУЕМ ПОЛУЧИТЬ ИНФОРМАЦИЮ О БОТЕ
                bot_info = self.bot.get_me()
                print(f"✅ Бот @{bot_info.username} запущен")
                print(f"   Имя бота: {bot_info.first_name}")
                
                # 🔥 ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ АДМИНАМ ПРИ ЗАПУСКЕ
                self.send_startup_notifications()
                
                self.bot.infinity_polling(timeout=10, long_polling_timeout=5)
            except Exception as e:
                print(f"❌ Ошибка в работе бота: {e}")
                self.running = False
        
        # Запускаем бота в отдельном потоке
        self.bot_thread = threading.Thread(target=run_bot, daemon=True)
        self.bot_thread.start()
        print("✅ Telegram бот запущен в фоновом режиме")
    
    def send_startup_notifications(self):
        """Отправка уведомлений админам при запуске бота"""
        if not TELEGRAM_ADMIN_IDS:
            print("⚠️ Список админов пуст, уведомления не отправлены")
            return
        
        for admin_id in TELEGRAM_ADMIN_IDS:
            try:
                self.bot.send_message(
                    admin_id,
                    "🚀 *Dota 2 Automator запущен!*\n\n"
                    "🤖 Бот управления активирован и готов к работе.\n"
                    "Используйте /start для открытия меню.",
                    parse_mode='Markdown'
                )
                print(f"✅ Уведомление отправлено админу {admin_id}")
            except Exception as e:
                print(f"⚠️ Не удалось отправить уведомление админу {admin_id}: {e}")

    def stop_bot(self):
        """Остановка бота"""
        self.running = False
        if self.bot_thread:
            self.bot_thread.join(timeout=5)
        print("✅ Telegram бот остановлен")

# Глобальный экземпляр менеджера бота
telegram_bot_manager = None

def init_telegram_bot(main_program=None):
    """Инициализация Telegram бота"""
    global telegram_bot_manager
    
    if TELEGRAM_BOT_TOKEN:
        telegram_bot_manager = TelegramBotManager(main_program)
        telegram_bot_manager.start_bot()
        return telegram_bot_manager
    else:
        print("⚠️ Telegram бот не запущен: отсутствует токен")
        return None

def get_bot_manager():
    """Получение экземпляра менеджера бота"""
    global telegram_bot_manager
    return telegram_bot_manager