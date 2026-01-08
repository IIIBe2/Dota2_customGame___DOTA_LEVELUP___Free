# statistics.py
import datetime
import json
import os
from config import STATS_FILE

class Statistics:
    def __init__(self):
        self.stats_file = STATS_FILE
        self.session_start_time = datetime.datetime.now()
        self.current_session_data = {
            'session_start': self.session_start_time.isoformat(),
            'gold_found_count': 0,
            'restart_count': 0,
            'total_gold_find_time': 0,
            'multiplied_gold_count': 0,  # Добавляем умноженное количество
            'infinite_cycles': 0,  # 🔥 ДОБАВЛЯЕМ СТАТИСТИКУ БЕСКОНЕЧКИ
            'events': []
        }
        self.load_existing_stats()
    
    def record_pet_switch_by_trigger(self, pet_id, pet_name, trigger_cycles, current_cycles, trigger_deactivated=True):
        """
        Записывает переключение питомца по триггеру бесконечки
        trigger_deactivated: True если триггер был деактивирован после срабатывания
        """
        event_time = datetime.datetime.now()
        
        event_data = {
            'timestamp': event_time.isoformat(),
            'date': event_time.strftime("%Y-%m-%d"),
            'time': event_time.strftime("%H:%M:%S"),
            'event_type': 'pet_switch_by_trigger',
            'pet_id': pet_id,
            'pet_name': pet_name,
            'trigger_cycles': trigger_cycles,
            'current_cycles': current_cycles,
            'trigger_deactivated': trigger_deactivated  # 🔥 НОВЫЙ ПАРАМЕТР
        }
        
        # Добавляем в текущую сессию
        self.current_session_data['events'].append(event_data)
        
        # Увеличиваем счетчик переключений
        if 'pet_switches_by_trigger' not in self.current_session_data:
            self.current_session_data['pet_switches_by_trigger'] = 0
        self.current_session_data['pet_switches_by_trigger'] += 1
        
        # Обновляем общую статистику
        if 'total_pet_switches_by_trigger' not in self.total_stats:
            self.total_stats['total_pet_switches_by_trigger'] = 0
        self.total_stats['total_pet_switches_by_trigger'] += 1
        
        self.save_stats()
        
        print(f"\n📊 СТАТИСТИКА: Переключение питомца по триггеру бесконечки!")
        print(f"🐾 Питомец: {pet_name}")
        print(f"🎯 Триггер: {trigger_cycles} циклов")
        print(f"🌀 Текущие циклы: {current_cycles}")
        if trigger_deactivated:
            print(f"⚠️ Триггер деактивирован для предотвращения повторного срабатывания")

    def record_hero_death_in_infinite(self, details=""):
        """
        Записывает смерть героя в бесконечке
        """
        event_time = datetime.datetime.now()
        
        event_data = {
            'timestamp': event_time.isoformat(),
            'date': event_time.strftime("%Y-%m-%d"),
            'time': event_time.strftime("%H:%M:%S"),
            'event_type': 'hero_death_infinite',
            'details': details
        }
        
        # Добавляем в текущую сессию
        self.current_session_data['events'].append(event_data)
        
        # Увеличиваем счетчик смертей героя
        if 'hero_death_infinite_count' not in self.current_session_data:
            self.current_session_data['hero_death_infinite_count'] = 0
        self.current_session_data['hero_death_infinite_count'] += 1
        
        # Обновляем общую статистику
        if 'hero_death_infinite_count' not in self.total_stats:
            self.total_stats['hero_death_infinite_count'] = 0
        self.total_stats['hero_death_infinite_count'] += 1
        
        self.save_stats()
        
        print(f"\n💀 СТАТИСТИКА: Зафиксирована смерть героя в бесконечке!")
        print(f"📅 Дата: {event_data['date']}")
        print(f"⏰ Время: {event_data['time']}")
        print(f"📋 Детали: {details}")

    def get_stats_for_telegram(self):
        """Получение статистики для Telegram бота"""
        session = self.get_session_summary()
        total = self.get_total_summary()
        
        return {
            'session': session,
            'total': total,
            'current_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # statistics.py - добавляем новые методы

    def record_host_death(self, death_type, details=""):
        """
        Записывает смерть хоста (красная рамка или 9999999)
        death_type: 'red_frame' или 'gold_text'
        details: дополнительные детали
        """
        event_time = datetime.datetime.now()
        
        event_data = {
            'timestamp': event_time.isoformat(),
            'date': event_time.strftime("%Y-%m-%d"),
            'time': event_time.strftime("%H:%M:%S"),
            'event_type': 'host_death',
            'death_type': death_type,
            'details': details
        }
        
        # Добавляем в текущую сессию
        self.current_session_data['events'].append(event_data)
        
        # Увеличиваем счетчик в зависимости от типа
        if death_type == 'gold_text':
            key = 'gold_deaths_count'
        elif death_type == 'red_frame':
            key = 'red_frame_deaths_count'
        else:
            key = 'other_deaths_count'
        
        # Инициализируем счетчики если их нет
        if key not in self.current_session_data:
            self.current_session_data[key] = 0
        
        self.current_session_data[key] += 1
        
        # Обновляем общую статистику
        if key not in self.total_stats:
            self.total_stats[key] = 0
        self.total_stats[key] += 1
        
        self.save_stats()
        
        # Выводим информацию
        death_name = "9999999 в чате" if death_type == 'gold_text' else "красная рамка"
        print(f"\n💀 СТАТИСТИКА: Зафиксирована смерть хоста ({death_name})!")
        print(f"📅 Дата: {event_data['date']}")
        print(f"⏰ Время: {event_data['time']}")
        print(f"📋 Детали: {details}")

    def get_death_statistics(self):
        """Возвращает статистику смертей хоста"""
        session_stats = {
            'gold_deaths': self.current_session_data.get('gold_deaths_count', 0),
            'red_frame_deaths': self.current_session_data.get('red_frame_deaths_count', 0),
            'total_deaths': self.current_session_data.get('gold_deaths_count', 0) + 
                        self.current_session_data.get('red_frame_deaths_count', 0)
        }
        
        total_stats = {
            'gold_deaths': self.total_stats.get('gold_deaths_count', 0),
            'red_frame_deaths': self.total_stats.get('red_frame_deaths_count', 0),
            'total_deaths': self.total_stats.get('gold_deaths_count', 0) + 
                        self.total_stats.get('red_frame_deaths_count', 0)
        }
        
        return {
            'session': session_stats,
            'total': total_stats
        }

    def record_infinite_cycle(self):
        """Запись полного цикла бесконечки"""
        self.current_session_data['infinite_cycles'] = self.current_session_data.get('infinite_cycles', 0) + 1
        
        event_time = datetime.datetime.now()
        event_data = {
            'timestamp': event_time.isoformat(),
            'date': event_time.strftime("%Y-%m-%d"),
            'time': event_time.strftime("%H:%M:%S"),
            'event_type': 'infinite_cycle',
            'total_cycles': self.current_session_data['infinite_cycles']
        }
        
        self.current_session_data['events'].append(event_data)
        self.save_stats()
        
        print(f"📊 СТАТИСТИКА: Записан цикл бесконечки!")
        print(f"   Всего циклов в сессии: {self.current_session_data['infinite_cycles']}")

    def load_existing_stats(self):
        """Загружает существующую статистику из файла"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Загружаем только общую статистику, сессию начинаем заново
                    self.total_stats = data.get('total_stats', {
                        'total_sessions': 0,
                        'total_gold_found': 0,
                        'total_restarts': 0,
                        'total_gold_find_time': 0,
                        'total_multiplied_gold': 0,  # Добавляем общее умноженное количество
                        'average_find_time': 0
                    })
            except Exception as e:
                print(f"⚠️ Ошибка загрузки статистики: {e}")
                self.total_stats = {
                    'total_sessions': 0,
                    'total_gold_found': 0,
                    'total_restarts': 0,
                    'total_gold_find_time': 0,
                    'total_multiplied_gold': 0,
                    'average_find_time': 0
                }
        else:
            self.total_stats = {
                'total_sessions': 0,
                'total_gold_found': 0,
                'total_restarts': 0,
                'total_gold_find_time': 0,
                'total_multiplied_gold': 0,
                'average_find_time': 0
            }
    
    def record_gold_found(self, find_time_seconds):
        """
        Записывает событие нахождения 9999999
        find_time_seconds - время затраченное на поиск
        """
        event_time = datetime.datetime.now()
        
        # Умножаем текущее количество найденных 9999999 на 3
        multiplied_count = (self.current_session_data['gold_found_count'] + 1) * 3
        
        event_data = {
            'timestamp': event_time.isoformat(),
            'date': event_time.strftime("%Y-%m-%d"),
            'time': event_time.strftime("%H:%M:%S"),
            'find_time_seconds': find_time_seconds,
            'gold_found_count': self.current_session_data['gold_found_count'] + 1,
            'multiplied_gold_count': multiplied_count,  # Умноженное количество
            'event_type': 'gold_found'
        }
        
        # Добавляем в текущую сессию
        self.current_session_data['gold_found_count'] += 1
        self.current_session_data['multiplied_gold_count'] = multiplied_count
        self.current_session_data['total_gold_find_time'] += find_time_seconds
        self.current_session_data['events'].append(event_data)
        
        # Обновляем общую статистику
        self.total_stats['total_gold_found'] += 1
        self.total_stats['total_multiplied_gold'] = self.total_stats['total_gold_found'] * 3
        self.total_stats['total_gold_find_time'] += find_time_seconds
        
        # Рассчитываем среднее время поиска
        if self.total_stats['total_gold_found'] > 0:
            self.total_stats['average_find_time'] = (
                self.total_stats['total_gold_find_time'] / self.total_stats['total_gold_found']
            )
        
        # Сохраняем в файл
        self.save_stats()
        
        # Выводим информацию о событии
        print(f"\n🎯 СТАТИСТИКА: 9999999 найден!")
        print(f"📅 Дата: {event_data['date']}")
        print(f"⏰ Время: {event_data['time']}")
        print(f"⏱ Затраченное время: {find_time_seconds:.1f} сек")
        print(f"🔢 Найдено 9999999: {event_data['gold_found_count']} раз")
        print(f"📊 Умноженное количество: {event_data['multiplied_gold_count']} (×3)")
    
    def record_restart(self, reason=""):
        """Записывает событие перезапуска"""
        self.current_session_data['restart_count'] += 1
        event_time = datetime.datetime.now()
        
        event_data = {
            'timestamp': event_time.isoformat(),
            'date': event_time.strftime("%Y-%m-%d"),
            'time': event_time.strftime("%H:%M:%S"),
            'reason': reason,
            'event_type': 'restart'
        }
        
        self.current_session_data['events'].append(event_data)
        self.save_stats()
    
    def record_session_start(self):
        """Записывает начало новой сессии"""
        self.session_start_time = datetime.datetime.now()
        self.total_stats['total_sessions'] += 1
        self.current_session_data = {
            'session_start': self.session_start_time.isoformat(),
            'gold_found_count': 0,
            'restart_count': 0,
            'total_gold_find_time': 0,
            'multiplied_gold_count': 0,
            'events': []
        }
        self.save_stats()
    
    def save_stats(self):
        """Сохраняет статистику в файл"""
        try:
            stats_data = {
                'total_stats': self.total_stats,
                'current_session': self.current_session_data,
                'last_update': datetime.datetime.now().isoformat()
            }
            
            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"⚠️ Ошибка сохранения статистики: {e}")
    
    def get_session_summary(self):
        """Возвращает сводку по текущей сессии"""
        session_duration = datetime.datetime.now() - self.session_start_time
        hours, remainder = divmod(session_duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return {
            'session_duration': f"{int(hours)}ч {int(minutes)}м {int(seconds)}с",
            'gold_found_count': self.current_session_data['gold_found_count'],
            'multiplied_gold_count': self.current_session_data['multiplied_gold_count'],
            'restart_count': self.current_session_data['restart_count'],
            'infinite_cycles': self.current_session_data.get('infinite_cycles', 0),
            'gold_deaths_count': self.current_session_data.get('gold_deaths_count', 0),  # ⬅️ Добавляем
            'red_frame_deaths_count': self.current_session_data.get('red_frame_deaths_count', 0),  # ⬅️ Добавляем
            'total_deaths_count': self.current_session_data.get('gold_deaths_count', 0) + 
                                self.current_session_data.get('red_frame_deaths_count', 0),  # ⬅️ Добавляем
            'average_find_time': (
                self.current_session_data['total_gold_find_time'] / 
                self.current_session_data['gold_found_count'] 
                if self.current_session_data['gold_found_count'] > 0 else 0
            )
        }

    def get_total_summary(self):
        """Возвращает общую сводку статистики"""
        total_deaths = (self.total_stats.get('gold_deaths_count', 0) + 
                    self.total_stats.get('red_frame_deaths_count', 0))
        
        result = self.total_stats.copy()
        result['total_deaths'] = total_deaths
        return result
    
    def print_current_stats(self):
        """Выводит текущую статистику в консоль"""
        session_summary = self.get_session_summary()
        total_summary = self.get_total_summary()
        
        print("\n" + "=" * 60)
        print("📊 ТЕКУЩАЯ СТАТИСТИКА СЕССИИ")
        print("=" * 60)
        print(f"⏱ Длительность сессии: {session_summary['session_duration']}")
        print(f"🎯 Найдено 9999999: {session_summary['gold_found_count']} раз")
        print(f"📊 Умноженное количество: {session_summary['multiplied_gold_count']} (×3)")
        print(f"🌀 Циклов бесконечки: {session_summary['infinite_cycles']}")
        print(f"🔴 Смертей по красной рамке: {session_summary.get('red_frame_deaths_count', 0)}")
        print(f"💰 Смертей по 9999999: {session_summary.get('gold_deaths_count', 0)}")
        print(f"⚰️ Всего смертей хоста: {session_summary.get('total_deaths_count', 0)}")
        print(f"🔄 Перезапусков: {session_summary['restart_count']}")
        
        print("\n📈 ОБЩАЯ СТАТИСТИКА")
        print("=" * 60)
        print(f"📅 Всего сессий: {total_summary['total_sessions']}")
        print(f"🎯 Всего найдено 9999999: {total_summary['total_gold_found']}")
        print(f"📊 Всего умноженное количество: {total_summary['total_multiplied_gold']} (×3)")
        print(f"🔴 Всего смертей по красной рамке: {total_summary.get('gold_deaths_count', 0)}")
        print(f"💰 Всего смертей по 9999999: {total_summary.get('red_frame_deaths_count', 0)}")
        print(f"⚰️ Всего смертей хоста: {total_summary.get('total_deaths', 0)}")
        print(f"🔄 Всего перезапусков: {total_summary['total_restarts']}")

# Глобальный экземпляр статистики
stats = Statistics()