#!/usr/bin/env python3
"""План большой книги: каркас частей и глав, задания-пакеты для субагентов, просмотр.

  book_plan.py skeleton <dir> --parts 8 --chapter-pages 10 [--pages N] [--force]
  book_plan.py batches  <dir> --size 5 [--only-missing]
  book_plan.py show     <dir> [--no-spoilers] [--part N]
  book_plan.py check    <dir>

План хранится в plan/parts/part_NN.json — по файлу на часть, поэтому разные
субагенты могут заполнять разные части одновременно.
"""
import argparse
import math
import os
import shutil

from bookcommon import (
    chapter_files, chapter_id, die, iter_chapters, load_book, load_json,
    load_outline, page_chars, part_path, parts_dir, save_json,
)

ORDINALS = ["первая", "вторая", "третья", "четвёртая", "пятая", "шестая", "седьмая",
            "восьмая", "девятая", "десятая", "одиннадцатая", "двенадцатая"]


def part_label(num):
    if num <= len(ORDINALS):
        return "Часть " + ORDINALS[num - 1]
    return "Часть %d" % num


def cmd_skeleton(a):
    book = load_book(a.dir)
    pages = a.pages or int(book.get("target_pages") or 1000)
    d = parts_dir(a.dir)
    if os.path.isdir(d) and os.listdir(d) and not a.force:
        die("план уже есть в %s (используй --force, чтобы пересоздать)" % d)
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)

    n_ch = max(1, math.ceil(pages / a.chapter_pages))
    n_parts = max(1, min(a.parts, n_ch))
    base, extra = divmod(n_ch, n_parts)
    per_ch = pages / n_ch
    num = 1
    for p in range(1, n_parts + 1):
        count = base + (1 if p <= extra else 0)
        chapters = []
        for _ in range(count):
            chapters.append({
                "num": num,
                "title": "",
                "pov": "",
                "summary": "",
                "beats": [],
                "ends_with": "",
                "target_pages": round(per_ch, 1),
            })
            num += 1
        save_json(part_path(a.dir, p), {
            "num": p,
            "label": part_label(p),
            "title": "",
            "synopsis": "",
            "chapters": chapters,
        })
    book["target_pages"] = pages
    save_json(os.path.join(a.dir, "book.json"), book)
    print("Каркас: частей %d, глав %d по ~%.1f стр. (~%d знаков) → %s"
          % (n_parts, n_ch, per_ch, per_ch * page_chars(book), d))
    print("Теперь заполни в каждой главе: title, pov, summary, beats, ends_with.")


def problems(outline):
    out = []
    for part, ch in iter_chapters(outline):
        miss = [k for k in ("title", "summary") if not str(ch.get(k, "")).strip()]
        if not ch.get("beats"):
            miss.append("beats")
        if miss:
            out.append("глава %d (часть %d): нет %s" % (ch["num"], part["num"], ", ".join(miss)))
    for part in outline["parts"]:
        if not str(part.get("title", "")).strip():
            out.append("часть %d: нет title" % part["num"])
    return out


def cmd_check(a):
    outline = load_outline(a.dir)
    pr = problems(outline)
    for line in pr:
        print(line)
    total = sum(1 for _ in iter_chapters(outline))
    print("Глав в плане: %d, незаполненных мест: %d" % (total, len(pr)))
    return 1 if pr else 0


def cmd_show(a):
    book = load_book(a.dir)
    outline = load_outline(a.dir)
    spoilers = not a.no_spoilers
    total_pages = 0
    for part in outline["parts"]:
        if a.part and part["num"] != a.part:
            continue
        print("\n== %s. %s ==" % (part.get("label") or part_label(part["num"]), part.get("title", "")))
        if spoilers and part.get("synopsis"):
            print("   " + part["synopsis"])
        for ch in part["chapters"]:
            total_pages += ch.get("target_pages", 0)
            print("  %4d. %s  [%s стр.]" % (ch["num"], ch.get("title") or "—", ch.get("target_pages")))
            if spoilers:
                if ch.get("summary"):
                    print("        " + ch["summary"])
                for b in ch.get("beats", []):
                    print("        • " + b)
    print("\nИтого по плану: %.0f стр. (цель книги %s)" % (total_pages, book.get("target_pages")))


def neighbour_info(chapters_flat, idx, book_dir):
    lines = []
    if idx > 0:
        prev = chapters_flat[idx - 1][1]
        sp = os.path.join(book_dir, "plan", "summaries", chapter_id(prev["num"]) + ".md")
        lines.append("- Предыдущая глава %d «%s»: %s" % (prev["num"], prev.get("title", ""), prev.get("summary", "")))
        lines.append("  (если существует `%s` — прочитай, там что реально написано)" % sp)
    return lines


def render_chapter(ch, part, pc):
    target = int(ch.get("target_pages", 10) * pc)
    out = ["### Глава %d. %s" % (ch["num"], ch.get("title", "")),
           "- Файл: `chapters/%s.txt` (+ `%s.2.txt`, `%s.3.txt` … для продолжения)"
           % (chapter_id(ch["num"]), chapter_id(ch["num"]), chapter_id(ch["num"])),
           "- Краткое содержание: `plan/summaries/%s.md`" % chapter_id(ch["num"]),
           "- Объём: **не меньше %d знаков** (~%s стр.)" % (target, ch.get("target_pages")),
           "- Часть: %s. %s" % (part.get("label") or part_label(part["num"]), part.get("title", ""))]
    if ch.get("pov"):
        out.append("- Точка зрения: %s" % ch["pov"])
    out.append("- Содержание: %s" % ch.get("summary", ""))
    if ch.get("beats"):
        out.append("- Сцены по порядку:")
        out += ["  %d. %s" % (i + 1, b) for i, b in enumerate(ch["beats"])]
    if ch.get("ends_with"):
        out.append("- Концовка главы: %s" % ch["ends_with"])
    return "\n".join(out)


WRITER_RULES = """## Правила записи

1. Перед работой прочитай `bible.md` целиком (стиль, персонажи, глоссарий) и описание своей части в `plan/parts/part_{part:02d}.json`.
2. Пиши главы строго по порядку. Каждую главу — **кусками по 5–8 тыс. знаков**: первый кусок в `chapters/cNNNN.txt`, следующие в `chapters/cNNNN.2.txt`, `cNNNN.3.txt` и т. д., пока не наберёшь объём. Не переписывай уже сохранённые куски.
3. Формат: первая строка первого куска — `# Название главы` (без слова «Глава» и номера). Дальше **каждый абзац — одна строка**. Разрыв сцены — строка `* * *`. Эпиграф (по желанию) — строки `> …` сразу после заголовка, автор эпиграфа — `> — Имя`. Курсив `*так*`. Диалоги — с новой строки через тире «— ».
4. Пиши художественный текст полностью: сцены, диалоги, описания, мысли героев. Никаких пересказов «далее произошло…», никаких пометок, комментариев, markdown-заголовков внутри текста.
5. Сохраняй имена и факты из `bible.md`. Не раскрывай тайны раньше главы, указанной в библии. Не заканчивай книгу — веди к следующей главе.
6. После каждой главы создай `plan/summaries/cNNNN.md`: 5–10 строк — что произошло, где герои в конце, что они узнали, новые персонажи/предметы.
7. Проверь объём: `python3 {scripts}/book_status.py {dir} --from {first} --to {last}`. Если глава короче цели — допиши следующий кусок.
8. Пользователю текст не пересказывай. В конце ответь одной строкой: какие главы готовы и их объём в знаках.
"""


def cmd_batches(a):
    book = load_book(a.dir)
    outline = load_outline(a.dir)
    pc = page_chars(book)
    bdir = os.path.join(a.dir, "plan", "batches")
    os.makedirs(bdir, exist_ok=True)
    for name in os.listdir(bdir):
        if name.startswith("batch_") and name.endswith(".md"):
            os.remove(os.path.join(bdir, name))

    flat = list(iter_chapters(outline))
    files = chapter_files(a.dir) if a.only_missing else {}
    scripts = os.path.dirname(os.path.abspath(__file__))

    groups, cur = [], []
    for idx, (part, ch) in enumerate(flat):
        if a.only_missing and ch["num"] in files:
            continue
        if cur and (len(cur) >= a.size or cur[-1][1] != part["num"]):
            groups.append(cur)
            cur = []
        cur.append((idx, part["num"], part, ch))
    if cur:
        groups.append(cur)

    for bi, group in enumerate(groups, 1):
        first, last = group[0][3]["num"], group[-1][3]["num"]
        part = group[0][2]
        text = ["# Пакет %03d: главы %d–%d" % (bi, first, last), "",
                "Книга: «%s», автор: %s. Стиль: %s." % (book.get("title"), book.get("author"), book.get("style") or "см. bible.md"),
                "Папка книги: `%s` (все пути ниже — относительно неё)." % os.path.abspath(a.dir), "",
                "## Контекст"]
        text += neighbour_info(flat, group[0][0], a.dir) or ["- Это начало книги."]
        if part.get("synopsis"):
            text.append("- Синопсис части: %s" % part["synopsis"])
        nxt = group[-1][0] + 1
        if nxt < len(flat):
            n = flat[nxt][1]
            text.append("- Следующая глава %d «%s» (её пишет другой агент): %s" % (n["num"], n.get("title", ""), n.get("summary", "")))
        text += ["", "## Главы"]
        for _, _, p, ch in group:
            text += ["", render_chapter(ch, p, pc)]
        text += ["", WRITER_RULES.format(part=part["num"], scripts=scripts, dir=os.path.abspath(a.dir),
                                         first=first, last=last)]
        with open(os.path.join(bdir, "batch_%03d.md" % bi), "w", encoding="utf-8") as f:
            f.write("\n".join(text))
    print("Создано пакетов: %d в %s" % (len(groups), bdir))
    for bi, group in enumerate(groups, 1):
        print("  batch_%03d.md: главы %d–%d" % (bi, group[0][3]["num"], group[-1][3]["num"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("skeleton")
    s.add_argument("dir")
    s.add_argument("--parts", type=int, default=8)
    s.add_argument("--chapter-pages", type=float, default=10)
    s.add_argument("--pages", type=int)
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("batches")
    s.add_argument("dir")
    s.add_argument("--size", type=int, default=5)
    s.add_argument("--only-missing", action="store_true", help="только главы без файлов")
    s = sub.add_parser("show")
    s.add_argument("dir")
    s.add_argument("--no-spoilers", action="store_true")
    s.add_argument("--part", type=int)
    s = sub.add_parser("check")
    s.add_argument("dir")
    a = ap.parse_args()
    rc = {"skeleton": cmd_skeleton, "batches": cmd_batches, "show": cmd_show, "check": cmd_check}[a.cmd](a)
    raise SystemExit(rc or 0)


if __name__ == "__main__":
    main()
