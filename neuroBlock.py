# neuroBlock.py
import re
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

_model = None
_tokenizer = None
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ---------- Маппинг категорий (внешние ключи -> русские названия) ----------
CATEGORY_MAPPING = {
    "EMAIL": "ПОЧТА",
    "PHONE": "НОМЕР ТЕЛЕФОНА",
    "ADDR": "АДРЕС",
    "PASS": "ПАСПОРТ",
    "SNILS": "СНИЛС",
    "INN_PER": "ИНН ДЛЯ ФИЗИЧЕСКИХ ЛИЦ",
    "INN": "ИНН ДЛЯ ЮРИДИЧЕСКИХ ЛИЦ",
    "COMPANY": "НАЗВАНИЕ КОМПАНИИ",
    "FIO": "ФИО",
    "FIO_I": "ФИО",
    "FIO_R": "ФИО",
    "FIO_D": "ФИО",
    "DATE": "ДАТА",
}

# ---------- Маппинг предсказанных моделью меток -> русские названия ----------
NEURO_LABEL_MAPPING = {
    "FIO_I": "ФИО",
    "FIO_R": "ФИО",
    "FIO_D": "ФИО",
    "FIO": "ФИО",
    "DATE": "ДАТА",
    "COMPANY": "НАЗВАНИЕ КОМПАНИИ",
    "ADDR": "АДРЕС",
    "PASS": "ПАСПОРТ",
    "SNILS": "СНИЛС",
    "INN_PER": "ИНН ДЛЯ ФИЗИЧЕСКИХ ЛИЦ",
    "INN": "ИНН ДЛЯ ЮРИДИЧЕСКИХ ЛИЦ",
    "EMAIL": "ПОЧТА",
    "PHONE": "НОМЕР ТЕЛЕФОНА",
    # на случай иных меток – оставляем как есть
}

def load_model(model_path):
    global _model, _tokenizer
    if _model is None:
        _model = AutoModelForTokenClassification.from_pretrained(model_path)
        _tokenizer = AutoTokenizer.from_pretrained(model_path)
        _model.to(_device)
        _model.eval()
    return _model, _tokenizer

def tokenize_text_with_offsets(text):
    tokens = []
    offsets = []
    for m in re.finditer(r'\w+|[^\w\s]', text):
        tokens.append(m.group())
        offsets.append((m.start(), m.end()))
    return tokens, offsets

def predict_entities(text, model_path, categories=None, max_length=512):
    """
    Возвращает список сущностей [{'start':int, 'end':int, 'label':str}].
    Метки label – русские названия.
    Обрабатывает текст любой длины (чанками).
    """
    model, tokenizer = load_model(model_path)
    tokenizer.model_max_length = max_length
    words, word_offsets = tokenize_text_with_offsets(text)
    if not words:
        return []

    # Подготовка фильтра по категориям
    allowed_labels = set()
    if categories:
        for cat in categories:
            if cat in CATEGORY_MAPPING:
                allowed_labels.add(CATEGORY_MAPPING[cat])
            else:
                allowed_labels.add(cat)   # если передали сразу русское название
    # Если categories пуст, allowed_labels останется пустым – блокировать фильтрацию будем позже

    # Токенизация для определения границ подслов
    temp_enc = tokenizer(
        words,
        is_split_into_words=True,
        truncation=False,
        return_tensors='pt'
    )
    total_tokens = temp_enc['input_ids'].shape[1]
    batch_word_ids = temp_enc.word_ids(batch_index=0)

    if total_tokens <= max_length:
        word_labels = _predict_words(words, model, tokenizer, max_length)
    else:
        # Разбиение на чанки
        word_token_span = []
        last_word = None
        start_i = 0
        for i, w_idx in enumerate(batch_word_ids):
            if w_idx is None:
                continue
            if w_idx != last_word:
                if last_word is not None:
                    word_token_span.append((start_i, i))
                start_i = i
                last_word = w_idx
        if last_word is not None:
            word_token_span.append((start_i, len(batch_word_ids)))

        chunks = []
        current_chunk = []
        current_len = 2   # CLS + SEP
        for word_idx, (sp_start, sp_end) in enumerate(word_token_span):
            word_tokens = sp_end - sp_start
            if current_len + word_tokens <= max_length:
                current_chunk.append(word_idx)
                current_len += word_tokens
            else:
                chunks.append(current_chunk)
                current_chunk = [word_idx]
                current_len = 2 + word_tokens
        if current_chunk:
            chunks.append(current_chunk)

        word_labels = ['O'] * len(words)
        for chunk in chunks:
            chunk_words = [words[i] for i in chunk]
            chunk_labels = _predict_words(chunk_words, model, tokenizer, max_length)
            for i, w_idx in enumerate(chunk):
                word_labels[w_idx] = chunk_labels[i]

    # Превращаем словные метки в интервалы сущностей
    entities = []
    current_entity = None
    for idx, (label, (start, end)) in enumerate(zip(word_labels, word_offsets)):
        if label == 'O':
            if current_entity:
                entities.append(current_entity)
                current_entity = None
            continue

        # Отрезаем B-/I- префиксы, оставляем тип
        entity_type = label[2:] if label.startswith("B-") or label.startswith("I-") else label
        # Перевод в русское название
        entity_type_ru = NEURO_LABEL_MAPPING.get(entity_type, entity_type)

        # Фильтр по категориям (если заданы)
        if categories and entity_type_ru not in allowed_labels:
            if current_entity:
                entities.append(current_entity)
                current_entity = None
            continue

        if current_entity is None:
            current_entity = {'start': start, 'end': end, 'label': entity_type_ru}
        else:
            # Продолжаем, если метка совпадает и слова идут вплотную
            if entity_type_ru == current_entity['label'] and start == current_entity['end']:
                current_entity['end'] = end
            else:
                entities.append(current_entity)
                current_entity = {'start': start, 'end': end, 'label': entity_type_ru}
    if current_entity:
        entities.append(current_entity)

    return entities


def _predict_words(words, model, tokenizer, max_length):
    """Возвращает список меток для списка слов (BIO-метки)."""
    inputs = tokenizer(
        words,
        is_split_into_words=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt"
    )
    for k in inputs:
        if isinstance(inputs[k], torch.Tensor):
            inputs[k] = inputs[k].to(_device)

    with torch.no_grad():
        outputs = model(**inputs)
    pred_ids = torch.argmax(outputs.logits, dim=2).squeeze(0).cpu().tolist()

    word_ids = inputs.word_ids(batch_index=0)
    pred_labels = []
    prev_word = None
    for idx, w_idx in enumerate(word_ids):
        if w_idx is None or w_idx == prev_word:
            continue
        pred_labels.append(model.config.id2label[pred_ids[idx]])
        prev_word = w_idx
    assert len(pred_labels) == len(words), "Чанк: несовпадение слов и меток"
    return pred_labels


def process_text(text, model_path="./rubert-base-cased", categories=None):
    return predict_entities(text, model_path, categories)
