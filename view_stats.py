# view_stats.py
import json
from statistics import stats

def main():
    print("=== ПРОСМОТР СТАТИСТИКИ ===")
    print("=" * 40)
    
    stats.print_current_stats()
    
    # Дополнительная информация из файла
    try:
        with open(stats.stats_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print("\n📋 ПОСЛЕДНИЕ СОБЫТИЯ:")
        print("-" * 40)
        
        events = data.get('current_session', {}).get('events', [])
        gold_events = [e for e in events if e.get('event_type') == 'gold_found']
        
        if gold_events:
            print("🎯 Находки 9999999:")
            for event in gold_events[-5:]:  # Последние 5 событий
                print(f"  📅 {event['date']} {event['time']} - "
                      f"{event['find_time_seconds']:.1f} сек - "
                      f"Перезапусков: {event['restart_count']} (×3: {event['multiplied_restarts']})")
        else:
            print("  Пока не найдено ни одного 9999999")
            
    except Exception as e:
        print(f"Ошибка загрузки детальной статистики: {e}")

if __name__ == "__main__":
    main()