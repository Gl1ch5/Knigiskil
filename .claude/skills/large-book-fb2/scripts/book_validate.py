#!/usr/bin/env python3
"""Проверка FB2: корректный XML и обязательные элементы FictionBook 2.0.

  book_validate.py <file.fb2 | file.fb2.zip>
"""
import argparse
import sys
import xml.etree.ElementTree as ET
import zipfile

NS = "{http://www.gribuser.ru/xml/fictionbook/2.0}"


def load(path):
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.endswith(".fb2")]
            if not names:
                raise ValueError("в архиве нет .fb2")
            return z.read(names[0])
    with open(path, "rb") as f:
        return f.read()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    a = ap.parse_args()

    errors = []
    try:
        root = ET.fromstring(load(a.file))
    except (ET.ParseError, ValueError, OSError) as e:
        print("ОШИБКА: файл не читается как XML: %s" % e)
        return 1

    if root.tag != NS + "FictionBook":
        errors.append("корневой элемент не FictionBook 2.0")
    ti = root.find(NS + "description/" + NS + "title-info")
    if ti is None:
        errors.append("нет description/title-info")
    else:
        for tag in ("genre", "author", "book-title", "lang"):
            if ti.find(NS + tag) is None:
                errors.append("нет title-info/%s" % tag)
    di = root.find(NS + "description/" + NS + "document-info")
    if di is None:
        errors.append("нет description/document-info")
    else:
        for tag in ("author", "date", "id", "version"):
            if di.find(NS + tag) is None:
                errors.append("нет document-info/%s" % tag)
    bodies = root.findall(NS + "body")
    if not bodies:
        errors.append("нет body")

    sections = root.findall(".//" + NS + "section")
    paras = root.findall(".//" + NS + "body//" + NS + "p")
    chars = sum(len("".join(p.itertext())) for p in paras)
    for s in sections:
        kids = [c.tag for c in s]
        if not kids:
            errors.append("пустая section")
            break
    # хотя бы одна глава — section без вложенных section
    leaves = [s for s in sections if s.find(NS + "section") is None]

    title = ti.findtext(NS + "book-title") if ti is not None else "?"
    print("Книга: %s" % title)
    print("Секций: %d (глав: %d), абзацев: %d, знаков в абзацах: %d (~%.0f стр. по 1800)"
          % (len(sections), len(leaves), len(paras), chars, chars / 1800.0))
    if errors:
        for e in errors:
            print("ОШИБКА: " + e)
        return 1
    print("OK: структура FB2 корректна")
    return 0


if __name__ == "__main__":
    sys.exit(main())
