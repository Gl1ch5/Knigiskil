#!/usr/bin/env python3
"""Прогресс книги: страницы по главам и частям, пустые и короткие главы.

  book_status.py <dir> [--short] [--from N] [--to M] [--threshold 0.7]
"""
import argparse

from bookcommon import (
    body_chars, chapter_files, iter_chapters, load_book, load_outline,
    page_chars, read_chapter_text,
)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("--short", action="store_true", help="показать только пустые/короткие главы")
    ap.add_argument("--from", dest="first", type=int, default=0)
    ap.add_argument("--to", dest="last", type=int, default=10 ** 9)
    ap.add_argument("--threshold", type=float, default=0.7, help="доля цели, ниже которой глава короткая")
    a = ap.parse_args()

    book = load_book(a.dir)
    outline = load_outline(a.dir)
    pc = page_chars(book)
    files = chapter_files(a.dir)

    total_chars = 0
    total_target = 0
    done = short = empty = 0
    cur_part = None
    for part, ch in iter_chapters(outline):
        n = ch["num"]
        if not (a.first <= n <= a.last):
            continue
        target = int(ch.get("target_pages", 10) * pc)
        chars = body_chars(read_chapter_text(files[n])) if n in files else 0
        total_chars += chars
        total_target += target
        if chars == 0:
            mark, empty = "ПУСТО", empty + 1
        elif chars < target * a.threshold:
            mark, short = "КОРОТКО", short + 1
        else:
            mark, done = "ок", done + 1
        if a.short and mark == "ок":
            continue
        if part["num"] != cur_part:
            cur_part = part["num"]
            print("— Часть %d. %s" % (part["num"], part.get("title", "")))
        pieces = len(files.get(n, []))
        print("  %4d %-40.40s %7d / %7d зн.  %5.1f стр.  кусков:%d  %s"
              % (n, ch.get("title") or "—", chars, target, chars / pc, pieces, mark))

    print("\nИтого: %d зн. = %.1f стр. из %.0f (%.0f%%). Готово: %d, коротких: %d, пустых: %d"
          % (total_chars, total_chars / pc, total_target / pc,
             100.0 * total_chars / max(total_target, 1), done, short, empty))


if __name__ == "__main__":
    main()
