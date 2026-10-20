"""Общие функции для скриптов навыка large-book-fb2."""
import json
import os
import re
import sys

DEFAULT_PAGE_CHARS = 1800
AUTHOR = "Павел М"  # постоянный псевдоним всех книг навыка
CHAPTER_FILE_RE = re.compile(r"^c(\d{4,})(?:\.(\d+))?\.txt$")
# крупный файл сразу на несколько глав: c0036-0040.txt, каждая глава начинается с "# Название"
BLOCK_FILE_RE = re.compile(r"^c(\d{4,})-(\d{4,})(?:\.(\d+))?\.txt$")


def die(msg):
    print("Ошибка: " + msg, file=sys.stderr)
    sys.exit(1)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def load_book(book_dir):
    path = os.path.join(book_dir, "book.json")
    if not os.path.isfile(path):
        die("не найден %s — сначала запусти book_init.py" % path)
    return load_json(path)


PART_FILE_RE = re.compile(r"^part_(\d+)\.json$")


def parts_dir(book_dir):
    return os.path.join(book_dir, "plan", "parts")


def part_path(book_dir, num):
    return os.path.join(parts_dir(book_dir), "part_%02d.json" % num)


def load_outline(book_dir):
    """План хранится по файлу на часть (plan/parts/part_NN.json),
    чтобы части можно было заполнять параллельно."""
    d = parts_dir(book_dir)
    files = []
    if os.path.isdir(d):
        for name in os.listdir(d):
            m = PART_FILE_RE.match(name)
            if m:
                files.append((int(m.group(1)), os.path.join(d, name)))
    if not files:
        die("нет файлов плана в %s — сначала запусти book_plan.py skeleton" % d)
    return {"parts": [load_json(p) for _, p in sorted(files)]}


def page_chars(book):
    return int(book.get("page_chars") or DEFAULT_PAGE_CHARS)


def scenes(ch):
    """Сцены главы (поле scenes; в старых планах — beats)."""
    return ch.get("scenes") or ch.get("beats") or []


def chapter_title(ch, text=None):
    """Название главы: из плана, иначе из строки '# …' в тексте."""
    if ch.get("title"):
        return ch["title"]
    for line in (text or "").split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
        if line.strip():
            break
    return ""


def chapter_id(num):
    return "c%04d" % num


def iter_chapters(outline):
    """Выдаёт (часть, глава) по порядку."""
    for part in outline.get("parts", []):
        for ch in part.get("chapters", []):
            yield part, ch


def chapter_files(book_dir):
    """{номер главы: [пути кусков по порядку]}."""
    d = os.path.join(book_dir, "chapters")
    result = {}
    if not os.path.isdir(d):
        return result
    for name in os.listdir(d):
        m = CHAPTER_FILE_RE.match(name)
        if not m:
            continue
        num = int(m.group(1))
        piece = int(m.group(2) or 1)
        result.setdefault(num, []).append((piece, os.path.join(d, name)))
    return {k: [p for _, p in sorted(v)] for k, v in result.items()}


def split_block(text, first):
    """Делит текст крупного файла на главы по строкам '# …' → {номер: текст}."""
    out = {}
    num = first - 1
    for line in text.split("\n"):
        if line.startswith("# "):
            num += 1
        if num >= first:
            out.setdefault(num, []).append(line)
    return {k: "\n".join(v) for k, v in out.items()}


def block_of(book_dir):
    """{номер главы: путь блок-файла cNNNN-MMMM.txt, где она лежит}."""
    d = os.path.join(book_dir, "chapters")
    out = {}
    if os.path.isdir(d):
        for name in sorted(os.listdir(d)):
            m = BLOCK_FILE_RE.match(name)
            if m:
                for n in range(int(m.group(1)), int(m.group(2)) + 1):
                    out.setdefault(n, os.path.join(d, name))
    return out


def chapter_texts(book_dir):
    """{номер главы: полный текст} из одиночных файлов и крупных блоков."""
    texts = {n: read_chapter_text(p) for n, p in chapter_files(book_dir).items()}
    d = os.path.join(book_dir, "chapters")
    if not os.path.isdir(d):
        return texts
    blocks = []
    for name in os.listdir(d):
        m = BLOCK_FILE_RE.match(name)
        if m:
            blocks.append((int(m.group(1)), int(m.group(3) or 1), os.path.join(d, name)))
    for first, piece, path in sorted(blocks):
        for num, text in split_block(read_chapter_text([path]), first).items():
            texts[num] = texts[num] + "\n" + text if num in texts else text
    return texts


def read_chapter_text(paths):
    parts = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            parts.append(f.read().replace("\r\n", "\n").replace("﻿", ""))
    return "\n".join(parts)


def body_chars(text):
    """Число знаков с пробелами без заголовка и пустых строк (как считает издатель)."""
    n = 0
    for line in text.split("\n"):
        s = line.strip()
        if not s or s.startswith("# "):
            continue
        n += len(s) + 1
    return n
