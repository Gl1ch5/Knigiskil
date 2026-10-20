#!/usr/bin/env python3
"""План книги: каркас частей и глав, задание на следующую главу, просмотр.

  book_plan.py skeleton <dir> [--pages N] [--chapters N] [--parts N] [--force]
  book_plan.py next     <dir> [--chapter N]
  book_plan.py show     <dir> [--no-spoilers] [--part N]
  book_plan.py check    <dir>
  book_plan.py trim     <dir> --chapters 20 --parts 1-7,8-14,15-20

skeleton сам выбирает число частей и глав по объёму книги (layout), чтобы
главы были полноценными эпизодами, а не мелкими кусками. --chapters/--parts
задают их вручную.

next печатает задание на первую ненаписанную главу: её план, место в
структуре, конспекты предыдущих глав и следующую главу.

trim сокращает план до N глав и при желании заново раскладывает главы по
частям: диапазоны через запятую, по одному на часть.
"""
import argparse
import math
import os
import re
import shutil

from bookcommon import (
    AUTHOR, body_chars, chapter_files, chapter_texts, chapter_id, chapter_title, die,
    iter_chapters, load_book, load_outline, page_chars, part_path, parts_dir,
    save_json, scenes,
)

ORDINALS = ["первая", "вторая", "третья", "четвёртая", "пятая", "шестая", "седьмая",
            "восьмая", "девятая", "десятая", "одиннадцатая", "двенадцатая"]

# ключевые точки структуры: доля объёма → роль главы (references/craft.md)
KEY_POINTS = [(0.0, "крючок и завязка"), (0.10, "событие-катализатор"),
              (0.25, "точка невозврата"), (0.50, "середина: переворот"),
              (0.75, "всё потеряно"), (0.90, "кульминация")]


def part_label(num):
    if num <= len(ORDINALS):
        return "Часть " + ORDINALS[num - 1]
    return "Часть %d" % num


def layout(pages):
    """(частей, глав) для объёма: глава — полноценный эпизод на 12–28 страниц."""
    if pages <= 150:
        cp, parts = 12, 1
    elif pages <= 400:
        cp, parts = 18, 2 if pages < 250 else 3
    elif pages <= 800:
        cp, parts = 22, 3 if pages < 600 else 4
    elif pages <= 2000:
        cp, parts = 25, min(6, max(4, math.ceil(pages / 350)))
    else:
        cp, parts = 28, math.ceil(pages / 500)
    return parts, max(1, round(pages / cp))


def cmd_skeleton(a):
    book = load_book(a.dir)
    pages = a.pages or int(book.get("target_pages") or 500)
    d = parts_dir(a.dir)
    if os.path.isdir(d) and os.listdir(d) and not a.force:
        die("план уже есть в %s (используй --force, чтобы пересоздать)" % d)
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)

    auto_parts, auto_ch = layout(pages)
    n_ch = a.chapters or auto_ch
    n_parts = max(1, min(a.parts or auto_parts, n_ch))
    base, extra = divmod(n_ch, n_parts)
    per_ch = pages / n_ch
    # роль главы по ключевым точкам: глава, на которую приходится доля объёма
    roles = {}
    for share, role in KEY_POINTS + [(1.0, "развязка")]:
        k = min(n_ch, int(share * n_ch) + 1)
        roles[k] = roles[k] + " + " + role if k in roles else role
    num = 1
    for p in range(1, n_parts + 1):
        count = base + (1 if p <= extra else 0)
        chapters = []
        for _ in range(count):
            chapters.append({
                "num": num,
                "title": "",
                "pov": "",
                "function": roles.get(num, ""),
                "summary": "",
                "scenes": [],
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
    print("Ключевые точки: " + ", ".join("гл. %d — %s" % (k, v) for k, v in sorted(roles.items())))
    print("Теперь заполни в каждой главе: title, pov, function, summary, scenes, ends_with.")


def problems(outline):
    out = []
    for part, ch in iter_chapters(outline):
        miss = [k for k in ("title", "summary") if not str(ch.get(k, "")).strip()]
        if not scenes(ch):
            miss.append("scenes")
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
            role = "  (%s)" % ch["function"] if spoilers and ch.get("function") else ""
            print("  %4d. %s  [%s стр.]%s" % (ch["num"], ch.get("title") or "—", ch.get("target_pages"), role))
            if spoilers:
                if ch.get("summary"):
                    print("        " + ch["summary"])
                for b in scenes(ch):
                    print("        • " + b)
    print("\nИтого по плану: %.0f стр. (цель книги %s)" % (total_pages, book.get("target_pages")))


SUMMARY_RE = re.compile(r"^c(\d{4,})(?:-(\d{4,}))?\.md$")


def summaries(book_dir):
    """{номер главы: путь к конспекту}; конспект на блок глав относится ко всем его главам."""
    d = os.path.join(book_dir, "plan", "summaries")
    out = {}
    if os.path.isdir(d):
        for name in sorted(os.listdir(d)):
            m = SUMMARY_RE.match(name)
            if m:
                lo = int(m.group(1))
                for n in range(lo, int(m.group(2) or lo) + 1):
                    out[n] = os.path.join(d, name)
    return out


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def cmd_next(a):
    book = load_book(a.dir)
    outline = load_outline(a.dir)
    pc = page_chars(book)
    flat = list(iter_chapters(outline))
    texts = chapter_texts(a.dir)
    files = chapter_files(a.dir)

    def written(ch):
        return body_chars(texts[ch["num"]]) if ch["num"] in texts else 0

    def target(ch):
        return int(ch.get("target_pages", 10) * pc)

    if a.chapter:
        idx = next((i for i, (_, ch) in enumerate(flat) if ch["num"] == a.chapter), None)
        if idx is None:
            die("нет главы %d в плане" % a.chapter)
    else:
        idx = next((i for i, (_, ch) in enumerate(flat) if written(ch) < target(ch) * a.threshold), None)
        if idx is None:
            print("Все главы написаны. Дальше: book_lint.py, book_build.py --zip, book_validate.py")
            return 0
    part, ch = flat[idx]
    n, cid = ch["num"], chapter_id(ch["num"])
    done, need = written(ch), target(ch)
    total_target = sum(target(c) for _, c in flat)
    before = sum(target(c) for _, c in flat[:idx])
    pieces = files.get(n, [])
    nxt_file = "%s.txt" % cid if not pieces else "%s.%d.txt" % (cid, len(pieces) + 1)

    out = ["# Глава %d из %d: %s" % (n, len(flat), chapter_title(ch, texts.get(n)) or "—"),
           "Книга «%s», %s. Позиция: %.0f%% книги. %s. %s"
           % (book.get("title"), AUTHOR, 100.0 * before / max(total_target, 1),
              part.get("label") or part_label(part["num"]), part.get("title", ""))]
    if part.get("synopsis"):
        out.append("Синопсис части: %s" % part["synopsis"])
    out += ["", "## План главы"]
    if ch.get("function"):
        out.append("Роль в структуре: %s" % ch["function"])
    if ch.get("pov"):
        out.append("Точка зрения: %s" % ch["pov"])
    out.append("Содержание: %s" % (ch.get("summary") or "—"))
    sc = scenes(ch)
    if sc:
        out.append("Сцены:")
        out += ["  %d. %s" % (i + 1, b) for i, b in enumerate(sc)]
    if ch.get("ends_with"):
        out.append("Концовка (крючок): %s" % ch["ends_with"])
    out.append("Объём: %d из %d знаков (~%s стр.). Следующий файл: chapters/%s"
               % (done, need, ch.get("target_pages"), nxt_file))

    sums = summaries(a.dir)
    prev = []
    seen = set()
    for _, pch in reversed(flat[:idx]):
        path = sums.get(pch["num"])
        if path and path not in seen:
            seen.add(path)
            prev.append((pch, read_text(path)))
        elif not path:
            prev.append((pch, pch.get("summary") or "—"))
        if len(prev) >= a.prev:
            break
    if prev:
        out += ["", "## Что было раньше (конспекты)"]
        for pch, text in reversed(prev):
            out.append("— Глава %d «%s»: %s" % (pch["num"], chapter_title(pch, texts.get(pch["num"])),
                                                text.replace("\n", " ")))
    if idx + 1 < len(flat):
        nch = flat[idx + 1][1]
        out += ["", "## Следующая глава %d «%s»" % (nch["num"], nch.get("title", "")),
                nch.get("summary") or "—", "Подведи к ней, но не забегай вперёд."]
    else:
        out += ["", "## Это последняя глава: кульминация/развязка, ответ на главный вопрос книги."]
    out += ["", "После записи: book_lint.py %s --chapter %d, чек-лист craft.md, конспект plan/summaries/%s.md"
            % (a.dir, n, cid)]
    print("\n".join(out))
    return 0


def cmd_trim(a):
    book = load_book(a.dir)
    outline = load_outline(a.dir)
    chapters = [ch for _, ch in iter_chapters(outline) if ch["num"] <= a.chapters]
    by_num = {ch["num"]: ch for ch in chapters}
    if a.parts:
        ranges = []
        for r in a.parts.split(","):
            lo, _, hi = r.partition("-")
            ranges.append((int(lo), int(hi or lo)))
    else:
        ranges = []
        for part in outline["parts"]:
            nums = [ch["num"] for ch in part["chapters"] if ch["num"] <= a.chapters]
            if nums:
                ranges.append((nums[0], nums[-1]))
    old = {p["num"]: p for p in outline["parts"]}
    shutil.rmtree(parts_dir(a.dir))
    os.makedirs(parts_dir(a.dir))
    for i, (lo, hi) in enumerate(ranges, 1):
        part = dict(old.get(i, {"num": i, "label": part_label(i), "title": "", "synopsis": ""}))
        part["chapters"] = [by_num.get(n, {"num": n, "title": "", "pov": "", "function": "", "summary": "",
                                           "scenes": [], "ends_with": "", "target_pages": 20}) for n in range(lo, hi + 1)]
        save_json(part_path(a.dir, i), part)
    book["target_pages"] = int(sum(ch.get("target_pages", 20) for ch in by_num.values()))
    save_json(os.path.join(a.dir, "book.json"), book)
    print("План: %d глав, частей %d, цель %d стр." % (a.chapters, len(ranges), book["target_pages"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("skeleton")
    s.add_argument("dir")
    s.add_argument("--pages", type=int, help="объём (по умолчанию из book.json)")
    s.add_argument("--chapters", type=int, help="число глав (по умолчанию — по объёму)")
    s.add_argument("--parts", type=int, help="число частей (по умолчанию — по объёму)")
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("next")
    s.add_argument("dir")
    s.add_argument("--chapter", type=int, help="задание на конкретную главу")
    s.add_argument("--prev", type=int, default=3, help="сколько прошлых конспектов показать")
    s.add_argument("--threshold", type=float, default=0.7, help="глава считается написанной от этой доли цели")
    s = sub.add_parser("show")
    s.add_argument("dir")
    s.add_argument("--no-spoilers", action="store_true")
    s.add_argument("--part", type=int)
    s = sub.add_parser("check")
    s.add_argument("dir")
    s = sub.add_parser("trim")
    s.add_argument("dir")
    s.add_argument("--chapters", type=int, required=True)
    s.add_argument("--parts", help="например 1-20,21-36,37-45")
    a = ap.parse_args()
    rc = {"skeleton": cmd_skeleton, "next": cmd_next, "show": cmd_show, "check": cmd_check,
          "trim": cmd_trim}[a.cmd](a)
    raise SystemExit(rc or 0)


if __name__ == "__main__":
    main()
