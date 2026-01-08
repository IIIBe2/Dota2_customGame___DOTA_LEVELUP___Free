# main.py
from config import RESTART_ON_CRITICAL_ERROR, TELEGRAM_BOT_ENABLED, TELEGRAM_BOT_TOKEN
import sys
from telegram_bot import init_telegram_bot, get_bot_manager
import time
import subprocess
import os
import traceback
from startGame import Dota2Launcher
from text_detector import TextDetector
from lobby_navigator import InviteModeNavigator, LobbyNavigator
from config import START_TIME_SEC, MAX_RESTARTS, START_FROM
from logger import Logger
from pause_handler import pause_handler
from AFK_lobby import AFKLobbyMonitor
from statistics import stats
from config import WORK_MODE
import importlib
from config_loader import get_config

def close_dota2():
    """
    Закрывает Dota 2 процесс
    """
    print("🔴 Закрываем Dota 2...")
    try:
        # Попытка закрыть через taskkill
        subprocess.run(["taskkill", "/f", "/im", "dota2.exe"], check=True, capture_output=True)
        print("✅ Dota 2 закрыта")
        return True
    except subprocess.CalledProcessError:
        print("⚠️ Не удалось закрыть Dota 2 через taskkill, пробуем альтернативные методы")
        try:
            subprocess.run(["wmic", "process", "where", "name='dota2.exe'", "delete"], check=True, capture_output=True)
            print("✅ Dota 2 закрыта через WMIC")
            return True
        except:
            print("❌ Не удалось закрыть Dota 2 автоматически")
            return False

def get_config(key, default=None):
    """Динамическое получение значения из config.py"""
    try:
        # Перезагружаем модуль config, чтобы получить актуальные значения
        import config
        importlib.reload(config)
        return getattr(config, key, default)
    except Exception as e:
        print(f"⚠️ Ошибка при чтении config.{key}: {e}")
        return default

def handle_critical_error(error, restart_count, logger, is_afk_monitoring=False):
    """
    Обработка критической ошибки
    """
    print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {error}")
    print("📋 Traceback:")
    traceback.print_exc()
    
    # Логируем ошибку
    logger.log_error(restart_count, "Критическая ошибка", str(error))
    
    # 🔥 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О РЕЖИМЕ ПЕРЕЗАПУСКА
    if not RESTART_ON_CRITICAL_ERROR:
        print("🎯 РЕЖИМ БЕЗ ПЕРЕЗАПУСКА АКТИВИРОВАН")
        print("🔧 Конфигурация: RESTART_ON_CRITICAL_ERROR = False")
        print("💡 Программа продолжит работу несмотря на ошибку")
        return False  # Не перезапускаем
    
    print("🎯 РЕЖИМ АВТОПЕРЕЗАПУСКА АКТИВИРОВАН") 
    print("🔧 Конфигурация: RESTART_ON_CRITICAL_ERROR = True")
    
    # Если ошибка произошла не во время AFK мониторинга, перезапускаем Dota 2
    if not is_afk_monitoring:
        print("🔄 Перезапускаем Dota 2 из-за критической ошибки...")
        
        # Закрываем Dota 2
        close_success = close_dota2()
        if close_success:
            logger.log_dota_close(restart_count, f"Критическая ошибка: {error}")
        else:
            logger.log_error(restart_count, "Закрытие Dota 2 при ошибке", "Не удалось закрыть")
        
        time.sleep(10)
        return True
    else:
        print("⚠️ Ошибка в AFK мониторинге - перезапуск не требуется")
        return False

def safe_run_attempt(launcher, attempt_number, logger, start_from, restart_count):
    """
    Безопасный запуск попытки с обработкой ошибок
    """
    try:
        # 🔥 ПРОВЕРЯЕМ ПЕРЕЗАПУСК ПЕРЕД НАЧАЛОМ
        restart_requested, telegram_reason = pause_handler.check_restart()
        if restart_requested:
            print(f"🔄 Прерываем запуск попытки - запрошен перезапуск из Telegram")
            return False, f"Прервано по запросу перезапуска: {telegram_reason}"
        
        return run_single_attempt(launcher, attempt_number, logger, start_from, restart_count)
    except Exception as e:
        # 🔥 ЭТО КРИТИЧЕСКАЯ ОШИБКА (ошибка в коде)
        if not RESTART_ON_CRITICAL_ERROR:
            print(f"🔧 РЕЖИМ БЕЗ ПЕРЕЗАПУСКА: Продолжаем работу несмотря на критическую ошибку")
            print(f"❌ Критическая ошибка: {e}")
            return False, f"Критическая ошибка (без перезапуска): {str(e)}"
        
        # Обрабатываем критическую ошибку с перезапуском
        should_restart = handle_critical_error(e, attempt_number, logger, is_afk_monitoring=False)
        return False, f"Критическая ошибка: {str(e)}" if should_restart else "Ошибка в AFK мониторинге"

def is_critical_error(error_reason):
    """
    Определяет, является ли ошибка критической (ошибка в коде)
    """
    critical_indicators = [
        "AttributeError",
        "TypeError", 
        "ValueError",
        "KeyError",
        "IndexError",
        "Exception:",
        "Error:",
        "ошибка:",
        "критическая"
    ]
    
    error_str = str(error_reason).lower()
    return any(indicator.lower() in error_str for indicator in critical_indicators)

def safe_afk_monitoring(afk_monitor, attempt_number, logger, restart_count):
    """
    Безопасный AFK мониторинг с обработкой ошибок
    """
    try:
        return afk_monitor.monitor_after_accept(restart_count)
    except Exception as e:
        # 🔥 ПРОВЕРЯЕМ НАСТРОЙКУ ДЛЯ AFK ОШИБОК
        if not RESTART_ON_CRITICAL_ERROR:
            print(f"🔧 РЕЖИМ БЕЗ ПЕРЕЗАПУСКА: Продолжаем AFK мониторинг")
            print(f"❌ Ошибка в AFK: {e}")
            return "CONTINUE", "Ошибка в AFK мониторинге (продолжаем)"
        
        # Ошибка во время AFK мониторинга - не перезапускаем Dota 2
        handle_critical_error(e, attempt_number, logger, is_afk_monitoring=True)
        return "RESTART", "Ошибка во время AFK мониторинга"

# main.py
def main():
    # 🔥 ВЫВОДИМ ИНФОРМАЦИЮ О ЗАПУСКЕ
    print("=" * 60)
    print("🤖 ЗАПУСК DOTA 2 AUTOMATOR С TELEGRAM БОТОМ")
    print("=" * 60)
    
    # 🔥 ИНИЦИАЛИЗИРУЕМ TELEGRAM БОТА
    from telegram_bot import init_telegram_bot
    
    # Проверяем настройки
    from config import TELEGRAM_BOT_ENABLED, TELEGRAM_BOT_TOKEN
    
    if TELEGRAM_BOT_ENABLED:
        if TELEGRAM_BOT_TOKEN:
            print("\n🤖 Инициализация Telegram бота...")
            bot_manager = init_telegram_bot()
            if bot_manager:
                print("✅ Telegram бот успешно инициализирован!")
                print("   Бот работает в фоновом режиме")
                print("   Используйте /start в Telegram для управления")
                
                # 🔥 ЖДЕМ 2 СЕКУНДЫ ДЛЯ ЗАПУСКА БОТА
                import time
                time.sleep(2)
            else:
                print("⚠️ Telegram бот не удалось запустить")
        else:
            print("⚠️ Telegram бот отключен: отсутствует токен в config.py")
            print("   Добавьте: TELEGRAM_BOT_TOKEN = 'ваш_токен'")
    else:
        print("ℹ️ Telegram бот отключен в настройках (TELEGRAM_BOT_ENABLED = False)")
    
    print("\n" + "=" * 60)
    print("🎮 ЗАПУСК ОСНОВНОЙ ПРОГРАММЫ")
    print("=" * 60)
    logger = Logger()
    stats.record_session_start()
    
    print("=== АВТОМАТИЧЕСКИЙ ВХОД В DOTA 2 ЛОББИ ===")
    print(f"🔧 Режим работы: { 'ОБЫЧНЫЙ' if WORK_MODE == 1 else 'ПО ПРИГЛАШЕНИЮ' }")
    
    if WORK_MODE == 2:
        print("📍 Режим 'По приглашению':")
        print("   - Ожидание первого ACCEPT: 5 минут")
        print("   - Ожидание второго ACCEPT: 4 минуты") 
        print("   - Затем стандартный AFK мониторинг")
    
    print(f"📍 Точка старта: {START_FROM}")
    print(f"Максимальное количество перезапусков: {MAX_RESTARTS}")
    print("=" * 60)
    
    dota_launcher = Dota2Launcher()
    restart_count = 0
    last_restart_reason = ""
    
    while restart_count < MAX_RESTARTS:
        # 🔥 ВАЖНО: Проверяем перезапуск из Telegram СНАЧАЛА, перед любыми другими действиями
        restart_requested, telegram_reason = pause_handler.check_restart()
        
        if restart_requested:
            print(f"\n🔄 ОБНАРУЖЕН ЗАПРОС ПЕРЕЗАПУСКА ИЗ TELEGRAM!")
            print(f"📋 Причина: {telegram_reason}")
            
            # 🔥 НЕМЕДЛЕННО ПРЕРЫВАЕМ ТЕКУЩУЮ ОПЕРАЦИЮ
            print("🛑 Немедленно прерываем текущую операцию...")
            
            # 🔥 ЗАКРЫВАЕМ DOTA 2 ПРИ ПЕРЕЗАПУСКЕ ИЗ TELEGRAM
            print("🔴 Закрываем Dota 2 для полного перезапуска...")
            close_success = close_dota2()
            if close_success:
                logger.log_dota_close(restart_count, f"Перезапуск из Telegram: {telegram_reason}")
            
            # Ждем чтобы процессы завершились
            time.sleep(10)
            
            # 🔥 ОЧИЩАЕМ ФЛАГ ПЕРЕЗАПУСКА
            pause_handler.clear_restart()
            
            # 🔥 СБРАСЫВАЕМ СЧЕТЧИК И НАЧИНАЕМ С ПОЛНОГО ЦИКЛА
            restart_count = 0
            
            # 🔥 ЗАПУСКАЕМ НОВЫЙ ПОЛНЫЙ ЦИКЛ (START_FROM = 1)
            print("🚀 ЗАПУСКАЕМ НОВЫЙ ПОЛНЫЙ ЦИКЛ (START_FROM = 1)")
            
            # Пропускаем обычную логику и запускаем полный цикл
            current_start_from = 1  # 🔥 ВСЕГДА ПОЛНЫЙ ЦИКЛ ДЛЯ TELEGRAM ПЕРЕЗАПУСКА
            
            # 🔥 ВЫБОР РЕЖИМА РАБОТЫ
            if WORK_MODE == 2:
                success, restart_reason = run_invite_mode_attempt(dota_launcher, restart_count + 1, logger, restart_count)
            else:
                success, restart_reason = safe_run_attempt(dota_launcher, restart_count + 1, logger, current_start_from, restart_count)
            
            # Обработка результата...
            if success:
                logger.log_success(restart_count + 1, "Перезапуск из Telegram выполнен успешно")
                print("🎉 ПЕРЕЗАПУСК ИЗ TELEGRAM УСПЕШНО ВЫПОЛНЕН!")
                break
            else:
                restart_count += 1
                continue  # Начинаем новый цикл
        
        # 🔥 ЕСЛИ НЕТ ЗАПРОСА ПЕРЕЗАПУСКА - ВЫПОЛНЯЕМ ОБЫЧНУЮ ЛОГИКУ
        print(f"\n🔄 ЗАПУСК #{restart_count + 1}")
        print("=" * 50)
        
        logger.log_dota_start(restart_count + 1)
        
        # 🔥 ТОЧКА СТАРТА: если это первый запуск - используем START_FROM, иначе полный цикл
        if restart_count == 0:
            current_start_from = START_FROM
        else:
            current_start_from = 1  # 🔥 ОБЫЧНЫЙ ПЕРЕЗАПУСК - ПОЛНЫЙ ЦИКЛ
        
        # 🔥 ВЫБОР РЕЖИМА РАБОТЫ
        if WORK_MODE == 2:
            success, restart_reason = run_invite_mode_attempt(dota_launcher, restart_count + 1, logger, restart_count)
        else:
            success, restart_reason = safe_run_attempt(dota_launcher, restart_count + 1, logger, current_start_from, restart_count)
        
        # 🔥 ПРОВЕРЯЕМ, НЕ БЫЛ ЛИ ЗАПРОШЕН ПЕРЕЗАПУСК ВО ВРЕМЯ ВЫПОЛНЕНИЯ
        restart_requested_during, telegram_reason_during = pause_handler.check_restart()
        if restart_requested_during:
            print(f"\n🔄 ОБНАРУЖЕН ЗАПРОС ПЕРЕЗАПУСКА ИЗ TELEGRAM ВО ВРЕМЯ ВЫПОЛНЕНИЯ!")
            # Не обрабатываем здесь - вернемся в начало цикла где обработаем
            
            # 🔥 ОЧИЩАЕМ ФЛАГ ПЕРЕЗАПУСКА (но сохраняем запрос для обработки в начале следующего цикла)
            # pause_handler.clear_restart()  # ❌ НЕ ОЧИЩАЕМ ЗДЕСЬ!
            
            # 🔥 СБРАСЫВАЕМ restart_count чтобы начать с начала
            restart_count = 0
            continue  # Возвращаемся в начало цикла
        
        # 🔥 ПРОВЕРЯЕМ ЗАВЕРШЕНИЕ
        if pause_handler.check_shutdown():
            print("\n🛑 Завершение программы по запросу пользователя...")
            pause_handler.graceful_shutdown()
        
        if success:
            logger.log_success(restart_count + 1, "Все операции завершены успешно")
            print("🎉 ВСЕ ОПЕРАЦИИ УСПЕШНО ЗАВЕРШЕНЫ!")
            break
        else:
            restart_count += 1
            
            # 🔥 ОПРЕДЕЛЯЕМ ТИП ОШИБКИ
            is_critical = is_critical_error(restart_reason)
            
            if is_critical and not RESTART_ON_CRITICAL_ERROR:
                # 🔧 КРИТИЧЕСКАЯ ОШИБКА В РЕЖИМЕ БЕЗ ПЕРЕЗАПУСКА
                print(f"🔧 КРИТИЧЕСКАЯ ОШИБКА (режим без перезапуска): {restart_reason}")
                print("💡 Продолжаем работу без перезапуска игры...")
                restart_count = 0  # Сбрасываем счетчик перезапусков
                time.sleep(5)  # Короткая пауза перед продолжением
            else:
                # 🎯 ЗАПИСЫВАЕМ ПЕРЕЗАПУСК В СТАТИСТИКУ
                stats.record_restart(restart_reason)
                
                # 🔥 ПРОВЕРЯЕМ, НЕ БЫЛ ЛИ ЭТО ПЕРЕЗАПУСК ИЗ TELEGRAM
                is_telegram_restart = "Telegram" in restart_reason or "ТГ" in restart_reason or "telegram" in restart_reason.lower()
                
                if is_telegram_restart:
                    print(f"\n🔄 ПЕРЕЗАПУСК ИЗ TELEGRAM ОБРАБОТАН!")
                    print(f"📋 Причина: {restart_reason}")
                    
                    # 🔥 ДЛЯ TELEGRAM ПЕРЕЗАПУСКА СБРАСЫВАЕМ restart_count
                    restart_count = 0
                else:
                    print(f"\n🔄 ОБЫЧНЫЙ ПЕРЕЗАПУСК ИГРЫ...")
                    print(f"📋 Причина: {restart_reason}")
                    print(f"🎯 Попытка {restart_count + 1}/{MAX_RESTARTS}")
                
                # 🔥 ПРОВЕРЯЕМ ЗАВЕРШЕНИЕ
                if pause_handler.check_shutdown():
                    print("\n🛑 Завершение программы по запросу пользователя...")
                    pause_handler.graceful_shutdown()
                
                if restart_count < MAX_RESTARTS:
                    # 🔥 ОБРАБОТКА ДЛЯ ОБЫЧНОГО ПЕРЕЗАПУСКА
                    if not is_telegram_restart:
                        logger.log_restart(restart_count, restart_reason)
                        
                        # Показываем текущую статистику
                        stats.print_current_stats()
                        
                        # Проверяем паузу перед закрытием игры
                        if not pause_handler.check_pause("Закрытие игры для перезапуска"):
                            if pause_handler.check_shutdown():
                                pause_handler.graceful_shutdown()
                            continue
                        
                        # Закрываем Dota 2 только для обычного перезапуска
                        close_success = close_dota2()
                        if close_success:
                            logger.log_dota_close(restart_count, restart_reason)
                        else:
                            logger.log_error(restart_count, "Закрытие Dota 2", "Не удалось закрыть автоматически")
                        
                        time.sleep(10)
                    else:
                        # 🔥 ДЛЯ TELEGRAM ПЕРЕЗАПУСКА - короткая пауза и продолжаем
                        print("⏳ Telegram перезапуск, продолжаем цикл...")
                        time.sleep(3)
                else:
                    logger.log_error(restart_count, "Достигнут лимит перезапусков")
                    print(f"\n❌ ДОСТИГНУТО МАКСИМАЛЬНОЕ КОЛИЧЕСТВО ПЕРЕЗАПУСКОВ ({MAX_RESTARTS})")
                    print("Скрипт завершает работу.")
    
    # Показываем финальную статистику
    print("\n" + "=" * 60)
    print("📊 ФИНАЛЬНАЯ СТАТИСТИКА СЕССИИ")
    print("=" * 60)
    stats.print_current_stats()
    
    print("\n🎯 Программа завершена!")
    input("Нажмите Enter для выхода...")

def run_single_attempt(launcher, attempt_number, logger, start_from, restart_count):
    """
    Запуск одной попытки выполнения скрипта с выбором точки старта
    """
    pause_handler.set_current_operation(f"Попытка #{attempt_number}", {
        'start_from': start_from,
        'restart_count': restart_count
    })
    detector = TextDetector()
    navigator = LobbyNavigator(detector, logger)
    
    print(f"🎯 ТОЧКА СТАРТА ДЛЯ ПОПЫТКИ #{attempt_number}: {start_from}")
    
    # 🔥 ПРОВЕРЯЕМ ПЕРЕЗАПУСК ПЕРЕД НАЧАЛОМ
    if not pause_handler.check_pause(f"Запуск попытки {attempt_number}"):
        restart_requested, telegram_reason = pause_handler.check_restart()
        if restart_requested:
            return False, f"Прервано по запросу перезапуска: {telegram_reason}"
        return False, "Завершение программы"
    
    # В зависимости от точки старта выполняем разные этапы
    if start_from == 1:
        return run_full_cycle(launcher, navigator, attempt_number, logger, restart_count)
    elif start_from == 2:
        return run_from_find(navigator, attempt_number, logger, restart_count)
    elif start_from == 3:
        return run_from_afk(attempt_number, logger, restart_count)
    else:
        print(f"❌ Неизвестная точка старта: {start_from}")
        return False, "Неизвестная точка старта"

def run_full_cycle(launcher, navigator, attempt_number, logger, restart_count):
    """
    Полный цикл: с запуска игры до AFK мониторинга
    """
    print("🎯 ЗАПУСК: Полный цикл (с начала)")
    
    if hasattr(navigator, 'afk_monitor') and hasattr(navigator.afk_monitor, 'infinite_mode'):
        navigator.afk_monitor.infinite_mode.reset_session_stats()
        
    if not pause_handler.check_pause("Запуск Dota 2"):
        return False, "Завершение программы"
    
    success, message = launcher.launch_dota2(["-novid", "-high"])
    
    if not success:
        logger.log_error(attempt_number, "Запуск Dota 2", message)
        print(f"❌ Не удалось запустить игру (попытка {attempt_number})")
        return False, "Не удалось запустить игру"
    
    logger.log_info(f"Dota 2 запущена успешно", attempt_number)
    print(f"🎯 Игра запущена! Ожидаем загрузку... (попытка {attempt_number})")
    
    # 🔥 СБРАСЫВАЕМ СЧЕТЧИКИ БЕСКОНЕЧКИ ПРИ ПЕРЕЗАПУСКЕ ИГРЫ
    # Это нужно сделать через navigator.afk_monitor.infinite_mode
    # Но сначала нужно убедиться что объект создан
    # Лучше сделать это позже, когда будет создан AFKLobbyMonitor
    
    for i in range(START_TIME_SEC):
        if not pause_handler.check_pause(f"Ожидание загрузки игры ({i+1}/{START_TIME_SEC} сек)"):
            return False, "Завершение программы"
        time.sleep(1)
    
    if not pause_handler.check_pause("Навигация к лобби"):
        return False, "Завершение программы"
        
    lobby_success = navigator.navigate_to_lobby()
    if not lobby_success:
        logger.log_error(attempt_number, "Навигация к лобби")
        print(f"❌ Не удалось перейти в лобби (попытка {attempt_number})")
        return False, "Не удалось перейти в лобби"
    
    logger.log_success(attempt_number, "Навигация к лобби")
    
    return run_from_find(navigator, attempt_number, logger, restart_count)

def run_from_find(navigator, attempt_number, logger, restart_count):
    """
    Запуск с момента поиска FIND
    """
    print("🎯 ЗАПУСК: С момента поиска FIND")
    
    if not pause_handler.check_pause("Вход в лобби по паролю"):
        return False, "Завершение программы"
        
    enter_success = navigator.find_and_enter_lobby()
    if not enter_success:
        logger.log_error(attempt_number, "Вход в лобби по паролю")
        print(f"❌ Не удалось войти в лобби (попытка {attempt_number})")
        return False, "Не удалось найти кнопку поиска"
    
    logger.log_success(attempt_number, "Вход в лобби по паролю")
    
    if not pause_handler.check_pause("Присоединение к игре"):
        return False, "Завершение программы"
        
    join_success, restart_reason = navigator.refresh_and_join_game(restart_count)
    if join_success == True:
        logger.log_success(attempt_number, "Присоединение к игре и нажатие ACCEPT")
        return True, ""
    elif join_success == "RESTART":
        # Улучшенное логирование причины перезапуска
        detailed_reason = restart_reason
        if "Не удалось найти ACCEPT" in restart_reason:
            detailed_reason = "Не удалось найти ACCEPT"
        elif "Не успел зайти в лобби" in restart_reason:
            detailed_reason = "Не успел зайти в лобби (найден OK)"
        elif "Не удалось найти DOTALAND" in restart_reason:
            detailed_reason = "Не удалось найти лобби"
        elif "Лобби AFK больше таймаута" in restart_reason:
            detailed_reason = "Лобби AFK больше таймаута"
        elif "Триггер сработал" in restart_reason:
            detailed_reason = "9999999 найден или красная рамка обнаружена"
        
        logger.log_error(attempt_number, "Присоединение к игре", detailed_reason)
        print(f"🔄 Требуется перезапуск (попытка {attempt_number}): {detailed_reason}")
        return False, detailed_reason
    else:
        logger.log_error(attempt_number, "Присоединение к игре", "Не удалось найти DOTALAND")
        print(f"❌ Не удалось присоединиться к игре (попытка {attempt_number})")
        return False, "Не удалось найти лобби"

def run_from_afk(attempt_number, logger, restart_count):
    """
    Запуск с AFK мониторинга
    """
    print("🎯 ЗАПУСК: С AFK мониторинга")
    
    # Создаем AFK монитор
    afk_monitor = AFKLobbyMonitor(logger)
    
    # Безопасный AFK мониторинг
    print("🚀 Запускаем AFK мониторинг...")
    monitor_result, monitor_reason = safe_afk_monitoring(afk_monitor, attempt_number, logger, restart_count)
    
    if monitor_result == "RESTART":
        logger.log_success(attempt_number, f"AFK мониторинг завершен: {monitor_reason}")
        return False, monitor_reason
    else:
        logger.log_error(attempt_number, "AFK мониторинг", "Неожиданный результат")
        return False, "Неожиданный результат AFK мониторинга"

def run_invite_mode_attempt(launcher, attempt_number, logger, restart_count=0):
    """
    Запуск попытки в режиме 'По приглашению'
    """
    print("🎯 ЗАПУСК РЕЖИМА 'ПО ПРИГЛАШЕНИЮ'")
    
    # Запускаем Dota 2
    if not pause_handler.check_pause("Запуск Dota 2 для режима приглашения"):
        return False, "Завершение программы"
    
    success, message = launcher.launch_dota2(["-novid", "-high"])
    
    if not success:
        logger.log_error(attempt_number, "Запуск Dota 2", message)
        print(f"❌ Не удалось запустить игру (попытка {attempt_number})")
        return False, "Не удалось запустить игру"
    
    logger.log_info(f"Dota 2 запущена для режима приглашения", attempt_number)
    print(f"🎯 Игра запущена! Ожидаем загрузку... (попытка {attempt_number})")
    
    # Ждем загрузку игры
    for i in range(START_TIME_SEC):
        if not pause_handler.check_pause(f"Ожидание загрузки игры ({i+1}/{START_TIME_SEC} сек)"):
            return False, "Завершение программы"
        time.sleep(1)
    
    # Запускаем навигатор режима приглашения
    detector = TextDetector()
    invite_navigator = InviteModeNavigator(detector, logger)
    
    print("🚀 НАЧИНАЕМ РЕЖИМ 'ПО ПРИГЛАШЕНИЮ'...")
    result, reason = invite_navigator.run_invite_mode()
    
    if result == True:
        logger.log_success(attempt_number, "Режим приглашения завершен успешно")
        return True, ""
    else:
        logger.log_error(attempt_number, "Режим приглашения", reason)
        return False, reason

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Программа прервана пользователем (Ctrl+C)")
        pause_handler.graceful_shutdown()
    except Exception as e:
        print(f"\n\n❌ Необработанная критическая ошибка: {e}")
        print("📋 Traceback:")
        traceback.print_exc()
        print("\n🔴 Аварийное завершение программы...")
        sys.exit(1)