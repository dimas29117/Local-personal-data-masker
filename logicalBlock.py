# logicalBlock.py
import re
import sys
import json
import argparse
from datetime import datetime

# ========================= ВАЛИДАТОРЫ (обновлённые) =========================

def validate_date(date_str):
    # Обработка формата с '/'
    if '/' in date_str:
        parts = date_str.split('/')
        if len(parts) == 3:
            m, d, y = parts
            if m.isdigit() and d.isdigit() and y.isdigit():
                month, day, year = int(m), int(d), int(y)
                if year < 100:
                    year = 1900 + year if year >= 70 else 2000 + year
                if 1 <= month <= 12 and 1 <= day <= 31:
                    try:
                        datetime(year, month, day)
                        return True
                    except:
                        pass
    normalized = date_str.replace('-', '.')
    parts = normalized.split('.')
    if len(parts) != 3:
        return False
    first = parts[0]
    if len(first) == 4 or (len(first) in (2,3) and first.isdigit() and int(first) > 31):
        year_str, month_str, day_str = parts
        if len(year_str) == 2:
            year_int = int(year_str)
            year_str = f"19{year_int:02d}" if year_int >= 70 else f"20{year_int:02d}"
        if not (month_str.isdigit() and day_str.isdigit()):
            return False
        try:
            datetime.strptime(f"{int(day_str):02d}.{int(month_str):02d}.{year_str}", '%d.%m.%Y')
            return True
        except ValueError:
            return False
    else:
        day_str, month_str, year_str = parts
        if not (day_str.isdigit() and month_str.isdigit() and year_str.isdigit()):
            return False
        if len(year_str) == 2:
            year_int = int(year_str)
            year_str = f"19{year_int:02d}" if year_int >= 70 else f"20{year_int:02d}"
        try:
            datetime.strptime(f"{int(day_str):02d}.{int(month_str):02d}.{year_str}", '%d.%m.%Y')
            return True
        except ValueError:
            return False


def validate_passport(passport_str):
    cleaned = ' '.join(passport_str.split())
    digits = re.sub(r'\s', '', passport_str)
    if re.match(r'^\d{10}$', digits):
        series = digits[:4]
        number = digits[4:]
        if series != '0000' and number != '000000':
            return True
    m = re.match(r'^(\d{2})\s+(\d{2})\s+(\d{6})$', cleaned)
    if m:
        series = m.group(1) + m.group(2)
        number = m.group(3)
        if series != '0000' and number != '000000':
            return True
    if re.search(r'серия\s+\d{4}\s+номер\s+\d{6}', cleaned, re.IGNORECASE):
        return True
    if re.search(r'паспорт\s+\d{4}\s+\d{6}', cleaned, re.IGNORECASE):
        return True
    return False


def validate_inn(inn_str):
    digits = re.sub(r'\D', '', inn_str)
    if not digits.isdigit():
        return False
    length = len(digits)
    if length == 10:
        ratio = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        total = sum(int(digits[i]) * ratio[i] for i in range(9))
        return (total % 11 % 10) == int(digits[9])
    elif length == 12:
        ratio_1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        total_1 = sum(int(digits[i]) * ratio_1[i] for i in range(10))
        control_1 = total_1 % 11 % 10
        ratio_2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        total_2 = sum(int(digits[i]) * ratio_2[i] for i in range(11))
        control_2 = total_2 % 11 % 10
        return (control_1 == int(digits[10])) and (control_2 == int(digits[11]))
    return False


def validate_snils(snils_str):
    digits = re.sub(r'[\s\-]', '', snils_str)
    if len(digits) != 11:
        return False
    if int(digits[:9]) <= 1001998:
        return False
    total = sum(int(digits[i]) * (9 - i) for i in range(9))
    if total < 100:
        control = total
    elif total in (100, 101):
        control = 0
    else:
        control = total % 101
        if control in (100, 101):
            control = 0
    return control == int(digits[9:])


# (Функции validate_address и validate_fio оставлены, но не используются в паттернах)
def validate_address(address_str):
    street_keywords = ['ул', 'улица', 'пр', 'проспект', 'пер', 'переулок',
                       'пл', 'площадь', 'бульвар', 'ш', 'шоссе', 'проезд',
                       'тупик', 'наб', 'набережная', 'аллея', 'линия']
    has_street = any(keyword in address_str.lower() for keyword in street_keywords)
    has_house = re.search(r'д\.?\s*\d+', address_str, re.IGNORECASE) is not None
    if (has_house or re.search(r'\d{1,5}\s*(?:корп\.?|стр\.?)?\s*\d*', address_str)) and len(address_str) > 10:
        return True
    return has_street or has_house


def validate_fio(fio_str):
    if re.match(r'^[А-ЯЁ]\.\s?[А-ЯЁ]\.?\s?[А-ЯЁа-яё]*$', fio_str):
        return True
    words = fio_str.split()
    if len(words) not in (2, 3):
        return False
    for word in words:
        if not re.match(r'^[А-ЯЁ][а-яё]{1,14}$', word):
            return False
    stop_words = {
        'И', 'В', 'НА', 'ЗА', 'ПОД', 'ОТ', 'ДО', 'О', 'ОБ', 'ИЗ', 'С', 'К', 'У', 'ПО',
        'ГОД', 'РОЖДЕНИЯ', 'ДОКУМЕНТ', 'ПАСПОРТ', 'СНИЛС', 'ИНН', 'СТРАХОВОЙ', 'НОМЕР',
        'СЕРИЯ', 'ВЫДАН', 'КОГДА', 'ЭТО', 'ТО', 'ЧТО', 'КАК', 'ТАК', 'ОН', 'ОНА', 'ОНИ',
        'ЯНВАРЯ', 'ФЕВРАЛЯ', 'МАРТА', 'АПРЕЛЯ', 'МАЯ', 'ИЮНЯ', 'ИЮЛЯ', 'АВГУСТА',
        'СЕНТЯБРЯ', 'ОКТЯБРЯ', 'НОЯБРЯ', 'ДЕКАБРЯ', 'ДОМ', 'УЛИЦА', 'ПРОСПЕКТ', 'ПЕРЕУЛОК',
        'ИНЖЕНЕР', 'КОНСТРУКТОР', 'НАЧАЛЬНИК', 'ДИРЕКТОР', 'ВЕДУЩИЙ', 'СПЕЦИАЛИСТ',
        'РУКОВОДИТЕЛЬ', 'СОТРУДНИК', 'БУХГАЛТЕР', 'КАДРОВ', 'ОТДЕЛ', 'ПРОИЗВОДСТВА', 'ЦЕХА',
        'ПРОЕКТА', 'МОДЕРНИЗАЦИИ', 'ПРИКАЗ', 'ДОЛЖНОСТЬ', 'ЗАРЕКОМЕНДОВАЛ', 'УЧАСТВОВАЛ',
        'ХАРАКТЕРИСТИКА', 'СЛУЖЕБНАЯ', 'ЗАПИСКА', 'ПРЕДОСТАВЛЕНИЯ', 'ТРЕБОВАНИЯ',
        'ДОПОЛНИТЕЛЬНАЯ', 'ПОЧТА', 'ТЕЛЕФОН', 'ОПЕРАТИВНОЙ', 'СВЯЗИ', 'ЭЛЕКТРОННАЯ',
        'АДРЕС', 'РЕГИСТРАЦИИ', 'ПРОЖИВАНИЯ', 'ПАСПОРТНЫЕ', 'ДАННЫЕ', 'УДОСТОВЕРЯЮЩИЙ',
        'ЛИЧНОСТЬ', 'РАБОТАЕТ', 'НАСТОЯЩАЯ', 'ДЕЙСТВИТЕЛЬНО', 'ПРИНЯТ', 'ШТАТ', 'ОФОРМЛЕНИЯ',
        'ЛИЧНОГО', 'ДЕЛА', 'СВЕРЕНЫ', 'ПОКАЗАЛ', 'СЕБЯ', 'ГРАМОТНЫМ', 'ИНИЦИАТИВНО',
        'ВНЕДРИЛ', 'СИСТЕМУ', 'БЕРЕЖЛИВОГО', 'ЭКСТРЕННОЙ', 'ИСПОЛЬЗУЕТ', 'ЛИЧНЫЙ',
        'ПЕНСИОННОЕ', 'СВИДЕТЕЛЬСТВО', 'ЗАРЕГИСТРИРОВАНО', 'БАЗЕ', 'ПРОШУ', 'УЧЕСТЬ',
        'ИЗМЕНЕН', 'РАБОЧАЯ', 'ПЕРЕПИСКА', 'ВЕДЕТСЯ', 'ЧЕРЕЗ'
    }
    if any(word.upper() in stop_words for word in words):
        return False
    return True


# ========================= ПАТТЕРНЫ (обновлённые, без ФИО и адресов) =========================

PATTERNS = {
    # ДАТЫ
    r'\b\d{2,4}[./-]\d{1,2}[./-]\d{1,2}\b': {'label': 'ДАТА', 'validator': validate_date},
    r'\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b': {'label': 'ДАТА', 'validator': validate_date},
    r'\b\d{1,2}/\d{1,2}/\d{2,4}\b': {'label': 'ДАТА', 'validator': validate_date},
    r'\b\d{1,2}-\d{1,2}-\d{2,4}\b': {'label': 'ДАТА', 'validator': validate_date},
    r'\b\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{2,4}\b': {'label': 'ДАТА', 'validator': None},
    r'\b(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{2,4}\b': {'label': 'ДАТА', 'validator': None},
    # ПОЧТА
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b': {'label': 'ПОЧТА', 'validator': None},
    # ПАСПОРТ
    r'\b\d{4}\s?\d{6}\b': {'label': 'ПАСПОРТ', 'validator': validate_passport},
    r'\b\d{2}\s+\d{2}\s+\d{6}\b': {'label': 'ПАСПОРТ', 'validator': validate_passport},
    r'(?:серия\s+)?(\d{4})\s+(?:номер\s+)?(\d{6})\b': {'label': 'ПАСПОРТ', 'validator': validate_passport},
    r'(?:паспорт\s+)?(\d{4})\s+(\d{6})\b': {'label': 'ПАСПОРТ', 'validator': validate_passport},
    # СНИЛС
    r'\b\d{3}-\d{3}-\d{3}\s\d{2}\b': {'label': 'СНИЛС', 'validator': validate_snils},
    r'\b\d{3}\s\d{3}\s\d{3}\s\d{2}\b': {'label': 'СНИЛС', 'validator': validate_snils},
    r'\b\d{11}\b': {'label': 'СНИЛС', 'validator': validate_snils},
    r'\b\d{9}\s\d{2}\b': {'label': 'СНИЛС', 'validator': validate_snils},
    # ТЕЛЕФОНЫ (расширенные)
    r'(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}': {'label': 'НОМЕР ТЕЛЕФОНА', 'validator': None},
    r'(?:\+7|8)[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}': {'label': 'НОМЕР ТЕЛЕФОНА', 'validator': None},
    r'\b\d{5,7}\b': {'label': 'НОМЕР ТЕЛЕФОНА', 'validator': None},
    r'(?<!\d)\d{7}(?!\d)': {'label': 'НОМЕР ТЕЛЕФОНА', 'validator': None},
    r'(?<!\d)\d{3}[- ]?\d{2}[- ]?\d{2}(?!\d)': {'label': 'НОМЕР ТЕЛЕФОНА', 'validator': None},
    r'(?<!\d)\d{3}[- ]?\d{4}(?!\d)': {'label': 'НОМЕР ТЕЛЕФОНА', 'validator': None},
    r'(?<!\d)\d{4}[- ]?\d{3}(?!\d)': {'label': 'НОМЕР ТЕЛЕФОНА', 'validator': None},
    r'\b\d{3}-\d{4}\b': {'label': 'НОМЕР ТЕЛЕФОНА', 'validator': None},
    r'\b\d{3}\s\d{4}\b': {'label': 'НОМЕР ТЕЛЕФОНА', 'validator': None},
    r'\b\d{3}-\d{2}-\d{2}\b': {'label': 'НОМЕР ТЕЛЕФОНА', 'validator': None},
    r'\b\d{3}\s\d{2}\s\d{2}\b': {'label': 'НОМЕР ТЕЛЕФОНА', 'validator': None},
    r'\b\d{4}-\d{3}\b': {'label': 'НОМЕР ТЕЛЕФОНА', 'validator': None},
    r'\b\d{4}\s\d{3}\b': {'label': 'НОМЕР ТЕЛЕФОНА', 'validator': None},
    r'\b\d{2}-\d{2}-\d{3}\b': {'label': 'НОМЕР ТЕЛЕФОНА', 'validator': None},
    # ИНН
    r'\b\d{10}\b': {'label': 'ИНН ДЛЯ ЮРИДИЧЕСКИХ ЛИЦ', 'validator': validate_inn},
    r'\b\d{12}\b': {'label': 'ИНН ДЛЯ ФИЗИЧЕСКИХ ЛИЦ', 'validator': validate_inn},
    r'\b\d{4}-\d{6}-\d{2}\b': {'label': 'ИНН ДЛЯ ФИЗИЧЕСКИХ ЛИЦ', 'validator': validate_inn},
    r'\b\d{4}-\d{5}-\d{1}\b': {'label': 'ИНН ДЛЯ ЮРИДИЧЕСКИХ ЛИЦ', 'validator': validate_inn},
    r'\b\d{3}-\d{3}-\d{4}\b': {'label': 'ИНН ДЛЯ ЮРИДИЧЕСКИХ ЛИЦ', 'validator': validate_inn},
    # КОМПАНИИ
    r'\b(?:ООО|ЗАО|ОАО|ПАО|ИП|ТОО|ЧУП|КФХ)\s+["«]?[А-ЯЁа-яё0-9\s\-]+["»]?': {'label': 'НАЗВАНИЕ КОМПАНИИ', 'validator': None},
    r'\b(?:АО|НПО|НИИ|ГУП|МУП)\s+["«]?[А-ЯЁа-яё0-9\s\-]+["»]?': {'label': 'НАЗВАНИЕ КОМПАНИИ', 'validator': None},
    r'\b(?:Кооператив|Солнце|Таврия|Спектр|Потенциал|Эльбрус|Гранит|Навигатор|Лаборатория|Гелиос|Тон|Полюс|Континент|Лидер|Софит|Транс|Устойчивость|Открытие|Молния)\s+[А-ЯЁа-яё0-9\s\-]+': {'label': 'НАЗВАНИЕ КОМПАНИИ', 'validator': None},
}


# ========================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =========================

def extract_entities(text, patterns):
    """Возвращает список интервалов (start, end, label) для всех найденных сущностей."""
    matches = []
    for pattern, info in patterns.items():
        for match in re.finditer(pattern, text):
            match_str = match.group(0)
            validator = info.get('validator')
            if validator is None or validator(match_str):
                matches.append((match.start(), match.end(), info['label']))
    return matches


def replace_with_numbering(text, patterns):
    """Замена найденных сущностей на 'МЕТКА N' с нумерацией по типам."""
    matches = []
    for pattern, info in patterns.items():
        for match in re.finditer(pattern, text):
            match_str = match.group(0)
            validator = info.get('validator')
            if validator is None or validator(match_str):
                matches.append({'start': match.start(), 'end': match.end(), 'label': info['label']})
    matches.sort(key=lambda x: x['start'])
    counters = {}
    result_parts = []
    last_idx = 0
    for m in matches:
        result_parts.append(text[last_idx:m['start']])
        label = m['label']
        counters[label] = counters.get(label, 0) + 1
        result_parts.append(f"{label} {counters[label]}")
        last_idx = m['end']
    result_parts.append(text[last_idx:])
    return ''.join(result_parts), counters


# ========================= МАППИНГ КАТЕГОРИЙ =========================

CATEGORY_MAPPING = {
    "EMAIL": "ПОЧТА",
    "PHONE": "НОМЕР ТЕЛЕФОНА",
    "ADDR": "АДРЕС",
    "PASS": "ПАСПОРТ",
    "SNILS": "СНИЛС",
    "INN_PER": "ИНН ДЛЯ ФИЗИЧЕСКИХ ЛИЦ",
    "INN": "ИНН ДЛЯ ЮРИДИЧЕСКИХ ЛИЦ",
    "COMPANY": "НАЗВАНИЕ КОМПАНИИ",
    "FIO_I": "ФИО",
    "FIO_R": "ФИО",
    "FIO_D": "ФИО",
    "DATE": "ДАТА",
}


# ========================= ГЛАВНАЯ ФУНКЦИЯ ДЛЯ ИНТЕГРАЦИИ =========================

def process_text(text, categories=None):
    """
    Основная функция для вызова из backEnd.
    Возвращает список сущностей в виде [{'start': int, 'end': int, 'label': str}].
    Если categories не задан, используются все паттерны.
    """
    # Фильтрация паттернов по категориям
    allowed_labels = set()
    if categories:
        for cat in categories:
            if cat in CATEGORY_MAPPING:
                allowed_labels.add(CATEGORY_MAPPING[cat])
            else:
                allowed_labels.add(cat)
    if allowed_labels:
        filtered_patterns = {
            pat: info for pat, info in PATTERNS.items()
            if info['label'] in allowed_labels
        }
    else:
        filtered_patterns = PATTERNS

    # Извлекаем интервалы
    entities = extract_entities(text, filtered_patterns)
    # Преобразуем к удобному формату
    return [{'start': s, 'end': e, 'label': lbl} for s, e, lbl in entities]


# ========================= CLI (оставлен для совместимости) =========================

def main():
    parser = argparse.ArgumentParser(description='Извлечение и замена личных данных')
    parser.add_argument('input_file', help='Входной файл .txt или .json')
    parser.add_argument('output_file', nargs='?', default=None)
    parser.add_argument('--encoding', default='utf-8')
    args = parser.parse_args()

    if args.input_file.lower().endswith('.json'):
        try:
            text, gold_spans = load_gold_json(args.input_file)
        except Exception as e:
            print(f"Ошибка загрузки JSON: {e}")
            sys.exit(1)
        found_spans = extract_entities(text, PATTERNS)
        per_label, overall = evaluate_extraction(found_spans, gold_spans)
        print("\n=== ОЦЕНКА НА РАЗМЕЧЕННЫХ ДАННЫХ ===")
        print(f"Всего эталонных сущностей: {len(gold_spans)}")
        print(f"Всего найденных системой: {len(found_spans)}")
        print("\nМетрики по типам:")
        for label in sorted(per_label.keys()):
            m = per_label[label]
            print(f"  {label}: TP={m['tp']}, FP={m['fp']}, FN={m['fn']} | "
                  f"P={m['precision']:.2%} R={m['recall']:.2%} F1={m['f1']:.2%}")
        print(f"\nОбщие метрики (микро-усреднение):")
        print(f"  Precision = {overall['precision']:.2%}")
        print(f"  Recall    = {overall['recall']:.2%}")
        print(f"  F1-score  = {overall['f1']:.2%}")
        return

    if args.output_file is None:
        print("Ошибка: для текстового файла необходимо указать output_file")
        sys.exit(1)

    encodings_to_try = [args.encoding, 'utf-8', 'cp1251']
    content = None
    used_encoding = None
    for enc in encodings_to_try:
        try:
            with open(args.input_file, 'r', encoding=enc) as f:
                content = f.read()
            used_encoding = enc
            break
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            print(f"Ошибка: файл {args.input_file} не найден.")
            sys.exit(1)
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            sys.exit(1)
    if content is None:
        print(f"Не удалось прочитать файл {args.input_file} ни в одной из кодировок: {encodings_to_try}")
        sys.exit(1)

    processed_text, counters = replace_with_numbering(content, PATTERNS)

    output_encoding = args.encoding
    try:
        with open(args.output_file, 'w', encoding=output_encoding) as f:
            f.write(processed_text)
        print(f"Обработка завершена. Результат сохранён в {args.output_file} (кодировка {output_encoding})")
        print(f"Исходный файл прочитан в кодировке {used_encoding}")
    except Exception as e:
        print(f"Ошибка при записи файла: {e}")
        sys.exit(1)

    total_replaced = sum(counters.values())
    print(f"\nВсего заменено сущностей: {total_replaced}")
    print("Статистика по типам:")
    for label, cnt in sorted(counters.items()):
        print(f"  {label}: {cnt}")


if __name__ == '__main__':
    main()
