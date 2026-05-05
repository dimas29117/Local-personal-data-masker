# backEnd.py
import sys
import os
import argparse
import logging
import logicalBlock
import neuroBlock

DEFAULT_MODEL_PATH = "./rubert-base-cased"
DEFAULT_INPUT = "data/testInput.txt"
DEFAULT_OUTPUT = "data/testOutputFinal.txt"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def merge_adjacent_spans(spans, text):
    """
    Объединяет соседние интервалы с одинаковым label, если между ними
    нет букв или цифр (т.е. только разделители).
    """
    if not spans:
        return []
    merged = []
    current = spans[0].copy()
    for next_span in spans[1:]:
        gap = text[current['end']:next_span['start']]
        # склеиваем, если метки совпадают и в промежутке нет букв/цифр
        if next_span['label'] == current['label'] and not any(c.isalnum() for c in gap):
            current['end'] = next_span['end']
        else:
            merged.append(current)
            current = next_span.copy()
    merged.append(current)
    return merged

def merge_spans(spans_logic, spans_neuro):
    """
    Объединяет два списка интервалов.
    Приоритет отдаётся нейросетевым интервалам (spans_neuro).
    Логические интервалы добавляются только если не пересекаются с нейросетевыми.
    """
    neuro_sorted = sorted(spans_neuro, key=lambda x: x['start'])
    merged = list(neuro_sorted)   # начинаем с нейросети

    def overlaps(span, existing):
        for ex in existing:
            if not (span['end'] <= ex['start'] or span['start'] >= ex['end']):
                return True
        return False

    for logic_span in spans_logic:
        if not overlaps(logic_span, merged):
            merged.append(logic_span)
    merged.sort(key=lambda x: x['start'])
    return merged

def replace_with_numbering(text, spans):
    """
    Заменяет в тексте интервалы из spans на 'МЕТКА N' с нумерацией по типам.
    Все интервалы должны быть непересекающимися и отсортированными.
    """
    counters = {}
    result_parts = []
    last_idx = 0
    for span in spans:
        start, end, label = span['start'], span['end'], span['label']
        result_parts.append(text[last_idx:start])
        counters[label] = counters.get(label, 0) + 1
        result_parts.append(f"{label} {counters[label]}")
        last_idx = end
    result_parts.append(text[last_idx:])
    return ''.join(result_parts)


def _process_single_file(input_path, output_path, categories, model_path, direction_flags):
    print(f"[BackEnd DEBUG] categories: {categories}")
    print(f"[BackEnd DEBUG] model_path: {model_path}")
    print(f"[BackEnd DEBUG] direction_flags: {direction_flags}")
    print(f"[BackEnd DEBUG] model exists: {os.path.exists(model_path)}")

    logging.info(f"Запуск обработки: categories={categories}, flags={direction_flags}")
    
    with open(input_path, 'r', encoding='utf-8-sig') as f:
        original_text = f.read()
    logging.info(f"Текст прочитан, длина: {len(original_text)} символов")

    # 1. Логический блок
    if direction_flags[0] == "1":
        try:
            spans_logic = logicalBlock.process_text(original_text, categories)
            logging.info(f"Логический блок: найдено {len(spans_logic)} сущностей")
        except Exception as e:
            logging.error(f"Ошибка в логическом блоке: {e}", exc_info=True)
            raise RuntimeError(f"Ошибка в логическом блоке: {e}")
    else:
        spans_logic = []
        logging.info("Логический блок отключён")

    # 2. Нейросетевой блок
    if direction_flags[1] == "1":
        try:
            spans_neuro = neuroBlock.process_text(original_text, model_path, categories)
            logging.info(f"Нейросетевой блок: найдено {len(spans_neuro)} сущностей")
            # Для отладки выведем первые несколько
            for s in spans_neuro[:5]:
                snippet = original_text[s['start']:s['end']]
                logging.info(f"  - {s['label']}: '{snippet}'")
        except Exception as e:
            logging.error(f"Ошибка в нейросетевом блоке: {e}", exc_info=True)
            raise RuntimeError(f"Ошибка в нейросетевом блоке: {e}")
    else:
        spans_neuro = []
        logging.info("Нейросетевой блок отключён")

    # 3. Объединение интервалов
    merged_spans = merge_spans(spans_logic, spans_neuro)
    merged_spans = merge_adjacent_spans(merged_spans, original_text)    # 4. Замена

    final_text = replace_with_numbering(original_text, merged_spans)

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_text)
    return final_text


def process_files(input_paths, output_paths, categories, model_path, direction_flags):
    if len(input_paths) != len(output_paths):
        raise ValueError("Количество входных и выходных файлов должно совпадать")
    results = []
    for inp, out in zip(input_paths, output_paths):
        logger.info(f"Обработка: {inp} -> {out}")
        res = _process_single_file(inp, out, categories, model_path, direction_flags)
        results.append(res)
    return results


def main():
    parser = argparse.ArgumentParser(description='Скрытие ПД (логика + нейросеть, нумерация меток)')
    parser.add_argument('input_file', nargs='*', default=None)
    parser.add_argument('--output', '-o', nargs='*', default=None)
    parser.add_argument('--categories', '-c', nargs='+', default=None)
    parser.add_argument('--model', '-m', default=None)
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--direct', '-d', default="11")
    args = parser.parse_args()

    direction_flags = args.direct
    if len(direction_flags) != 2 or not all(c in '01' for c in direction_flags):
        print("Ошибка: --direct должен быть двузначным числом из 0 и 1", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.WARNING)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(BASE_DIR)

    # Списки файлов
    if not args.input_file:
        input_list = [os.path.join(PROJECT_ROOT, DEFAULT_INPUT)]
    else:
        input_list = [os.path.abspath(p) if not os.path.isabs(p) else p for p in args.input_file]

    if not args.output:
        if len(input_list) == 1:
            output_list = [os.path.join(PROJECT_ROOT, DEFAULT_OUTPUT)]
        else:
            output_list = []
            for inp in input_list:
                base, ext = os.path.splitext(os.path.basename(inp))
                output_list.append(os.path.join(PROJECT_ROOT, "data", f"{base}_masked{ext}"))
    else:
        output_list = [os.path.abspath(p) if not os.path.isabs(p) else p for p in args.output]

    if len(input_list) != len(output_list):
        print("Ошибка: число входных и выходных файлов не совпадает", file=sys.stderr)
        sys.exit(1)

    if args.model is None:
        model_path = os.path.join(PROJECT_ROOT, DEFAULT_MODEL_PATH.lstrip('./'))
    else:
        model_path = args.model

    try:
        process_files(input_list, output_list, args.categories, model_path, direction_flags)
        print(f"Обработка завершена. Обработано файлов: {len(input_list)}")
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=args.verbose)
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
