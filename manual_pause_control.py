# manual_pause_control.py
import keyboard
from pause_handler import pause_handler
import time

def main():
    print("=== РУЧНОЕ УПРАВЛЕНИЕ ПАУЗОЙ ===")
    print("Горячие клавиши:")
    print("  Ctrl+Shift+P - пауза/продолжение")
    print("  Ctrl+Shift+Q - выход из скрипта")
    print("=" * 40)
    
    # Горячие клавиши для ручного управления
    keyboard.add_hotkey('ctrl+shift+p', pause_handler.toggle_pause)
    keyboard.add_hotkey('ctrl+shift+q', lambda: exit(0))
    
    print("Скрипт управления паузой запущен...")
    print("Нажмите Ctrl+Shift+Q для выхода")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nЗавершение работы...")

if __name__ == "__main__":
    main()