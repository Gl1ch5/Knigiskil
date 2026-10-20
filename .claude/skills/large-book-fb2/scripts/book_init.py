#!/usr/bin/env python3
"""Создаёт проект большой книги.

Пример:
  python3 book_init.py books/mushketery --title "Клинок и корона" \
      --author "Анри Лаваль" --pages 4000 --genre adv_history --style "Александр Дюма"
"""
import argparse
import datetime
import os
import uuid

from bookcommon import DEFAULT_PAGE_CHARS, die, save_json

BIBLE_TEMPLATE = """# Библия книги «{title}»

## Стиль
<!-- 6 пунктов разбора стиля (references/styles.md), записанные как правила для писателя -->

## Концепция
Логлайн:
Синопсис:

## Мир
<!-- эпоха, места, устройство общества, реалии, бытовые детали -->

## Персонажи
<!-- Имя — возраст, внешность, манера речи, цель, тайна, арка -->

## Сюжетные линии
<!-- линия: завязка → узлы (номера глав) → развязка -->

## Тайны и раскрытия
<!-- что скрыто от читателя и в какой главе раскрывается -->

## Синопсис частей
<!-- Часть 1: … -->

## Глоссарий
<!-- точное написание имён, титулов, мест -->
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", help="папка проекта книги")
    ap.add_argument("--title", required=True)
    ap.add_argument("--author", default="Неизвестный автор", help="'Имя Фамилия' или псевдоним")
    ap.add_argument("--pages", type=int, default=4000, help="целевой объём в страницах")
    ap.add_argument("--page-chars", type=int, default=DEFAULT_PAGE_CHARS, help="знаков на страницу")
    ap.add_argument("--genre", action="append", help="код жанра FB2, можно несколько раз")
    ap.add_argument("--style", default="", help="образец стиля, например 'Александр Дюма'")
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--force", action="store_true", help="перезаписать book.json")
    a = ap.parse_args()

    book_json = os.path.join(a.dir, "book.json")
    if os.path.exists(book_json) and not a.force:
        die("%s уже существует (используй --force)" % book_json)

    for sub in ("plan/batches", "plan/summaries", "chapters", "out"):
        os.makedirs(os.path.join(a.dir, sub), exist_ok=True)

    book = {
        "title": a.title,
        "author": a.author,
        "genres": a.genre or ["prose_contemporary"],
        "lang": a.lang,
        "target_pages": a.pages,
        "page_chars": a.page_chars,
        "style": a.style,
        "spoilers_ok": False,
        "pov": "",
        "rating": "16+",
        "ending": "",
        "annotation": "",
        "keywords": [],
        "date": str(datetime.date.today().year),
        "id": str(uuid.uuid4()),
        "version": "1.0",
    }
    save_json(book_json, book)

    bible = os.path.join(a.dir, "bible.md")
    if not os.path.exists(bible):
        with open(bible, "w", encoding="utf-8") as f:
            f.write(BIBLE_TEMPLATE.format(title=a.title))

    print("Проект создан: %s" % a.dir)
    print("  объём: %d стр. × %d знаков ≈ %.2f млн знаков"
          % (a.pages, a.page_chars, a.pages * a.page_chars / 1e6))
    print("Дальше: заполни bible.md, затем book_plan.py skeleton %s" % a.dir)


if __name__ == "__main__":
    main()
