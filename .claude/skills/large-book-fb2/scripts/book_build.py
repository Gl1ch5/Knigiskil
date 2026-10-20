#!/usr/bin/env python3
"""Собирает книгу в FB2 из plan/parts/*.json и chapters/*.txt.

  book_build.py <dir> [--out файл.fb2] [--zip] [--strict]

Части → <section> верхнего уровня, главы → вложенные <section>.
Обложка: cover.jpg / cover.png в папке книги (необязательно).
"""
import argparse
import base64
import datetime
import os
import re
import sys
import zipfile
from xml.sax.saxutils import escape

from bookcommon import (
    AUTHOR, body_chars, chapter_texts, die, iter_chapters, load_book, load_outline,
    page_chars,
)

SCENE_BREAK_RE = re.compile(r"^(\*\s*){3}$|^(-\s*){3,}$|^#{1,6}\s*$")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
EM_RE = re.compile(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])")


def inline(text):
    s = escape(text)
    s = BOLD_RE.sub(r"<strong>\1</strong>", s)
    s = EM_RE.sub(r"<emphasis>\1</emphasis>", s)
    return s.replace("*", "")  # непарные звёздочки не нужны в тексте


def para(text):
    return "<p>%s</p>" % inline(text)


def split_name(full):
    words = full.split()
    if len(words) >= 3:
        return words[0], " ".join(words[1:-1]), words[-1]
    if len(words) == 2:
        return words[0], "", words[1]
    return "", "", full


def author_xml(full):
    first, middle, last = split_name(full or "Неизвестный автор")
    if not first:
        return "<author><nickname>%s</nickname></author>" % escape(last)
    xml = "<author><first-name>%s</first-name>" % escape(first)
    if middle:
        xml += "<middle-name>%s</middle-name>" % escape(middle)
    return xml + "<last-name>%s</last-name></author>" % escape(last)


def chapter_xml(num, title, text):
    lines = [l.strip() for l in text.split("\n")]
    out = []
    head_title = title
    i = 0
    # заголовок из первой строки файла имеет приоритет над пустым title из плана
    while i < len(lines) and not lines[i]:
        i += 1
    if i < len(lines) and lines[i].startswith("# "):
        head_title = head_title or lines[i][2:].strip()
        i += 1
    rest = lines[i:]
    # дополнительные куски главы тоже могут начинаться с "# ..." — выбрасываем
    rest = [l for l in rest if not (l.startswith("# ") and l[2:].strip() == head_title)]

    t = "<title><p>Глава %d</p>" % num
    if head_title:
        t += "<p>%s</p>" % inline(head_title)
    out.append(t + "</title>")

    j = 0
    while j < len(rest) and not rest[j]:
        j += 1
    epi = []
    while j < len(rest) and rest[j].startswith(">"):
        epi.append(rest[j].lstrip(">").strip())
        j += 1
    if epi:
        author = epi.pop() if len(epi) > 1 and epi[-1].startswith(("—", "-")) else None
        x = "<epigraph>" + "".join(para(e) for e in epi if e)
        if author:
            x += "<text-author>%s</text-author>" % inline(author.lstrip("—- ").strip())
        out.append(x + "</epigraph>")

    cite = []
    has_body = False

    def flush_cite():
        if cite:
            out.append("<cite>" + "".join(para(c) for c in cite if c) + "</cite>")
            cite.clear()

    for line in rest[j:]:
        if not line:
            continue
        if line.startswith(">"):
            cite.append(line.lstrip(">").strip())
            continue
        flush_cite()
        if SCENE_BREAK_RE.match(line):
            if has_body:
                out.append("<subtitle>* * *</subtitle>")
            continue
        if re.match(r"^#{1,6}\s", line):
            out.append("<subtitle>%s</subtitle>" % inline(line.lstrip("#").strip()))
            continue
        out.append(para(line))
        has_body = True
    flush_cite()
    if not has_body:
        out.append("<p></p>")
    return "<section>\n" + "\n".join(out) + "\n</section>"


def cover(book_dir):
    for name, ctype in (("cover.jpg", "image/jpeg"), ("cover.jpeg", "image/jpeg"), ("cover.png", "image/png")):
        p = os.path.join(book_dir, name)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                data = base64.b64encode(f.read()).decode("ascii")
            bid = "cover" + os.path.splitext(name)[1]
            return bid, ('<binary id="%s" content-type="%s">%s</binary>' % (bid, ctype, data))
    return None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("--out", help="путь к .fb2 (по умолчанию out/<папка>.fb2)")
    ap.add_argument("--zip", action="store_true", help="дополнительно создать .fb2.zip")
    ap.add_argument("--strict", action="store_true", help="ошибка, если есть ненаписанные главы")
    a = ap.parse_args()

    book = load_book(a.dir)
    outline = load_outline(a.dir)
    files = chapter_texts(a.dir)
    pc = page_chars(book)
    slug = os.path.basename(os.path.abspath(a.dir))
    out_path = a.out or os.path.join(a.dir, "out", slug + ".fb2")

    missing = [ch["num"] for _, ch in iter_chapters(outline) if ch["num"] not in files]
    if missing:
        msg = "нет текста для глав: %s" % ", ".join(map(str, missing[:30]))
        if len(missing) > 30:
            msg += " … (всего %d)" % len(missing)
        if a.strict:
            die(msg)
        print("Внимание: " + msg + " — они пропущены", file=sys.stderr)

    cover_id, cover_bin = cover(a.dir)
    today = datetime.date.today().isoformat()
    genres = book.get("genres") or ["prose_contemporary"]

    desc = ["<description>", "<title-info>"]
    desc += ["<genre>%s</genre>" % escape(g) for g in genres]
    desc.append(author_xml(AUTHOR))
    desc.append("<book-title>%s</book-title>" % escape(book.get("title", slug)))
    ann = [l.strip() for l in str(book.get("annotation", "")).split("\n") if l.strip()]
    if ann:
        desc.append("<annotation>" + "".join(para(l) for l in ann) + "</annotation>")
    if book.get("keywords"):
        desc.append("<keywords>%s</keywords>" % escape(", ".join(book["keywords"])))
    desc.append("<date>%s</date>" % escape(str(book.get("date", today[:4]))))
    if cover_id:
        desc.append('<coverpage><image l:href="#%s"/></coverpage>' % cover_id)
    desc.append("<lang>%s</lang>" % escape(book.get("lang", "ru")))
    desc.append("</title-info>")
    desc += ["<document-info>", author_xml(AUTHOR),
             "<program-used>large-book-fb2 skill</program-used>",
             '<date value="%s">%s</date>' % (today, today),
             "<id>%s</id>" % escape(book.get("id", slug)),
             "<version>%s</version>" % escape(str(book.get("version", "1.0"))),
             "</document-info>", "</description>"]

    body = ["<body>", "<title><p>%s</p><p>%s</p></title>"
            % (escape(AUTHOR), escape(book.get("title", slug)))]
    multi = len(outline["parts"]) > 1
    total_chars = 0
    n_chapters = 0
    for part in outline["parts"]:
        written = [ch for ch in part["chapters"] if ch["num"] in files]
        if not written:
            continue
        if multi:
            t = "<title><p>%s</p>" % escape(part.get("label") or "Часть %d" % part["num"])
            if part.get("title"):
                t += "<p>%s</p>" % escape(part["title"])
            body += ["<section>", t + "</title>"]
        for ch in written:
            text = files[ch["num"]]
            total_chars += body_chars(text)
            n_chapters += 1
            body.append(chapter_xml(ch["num"], ch.get("title", ""), text))
        if multi:
            body.append("</section>")
    body.append("</body>")

    xml = ['<?xml version="1.0" encoding="utf-8"?>',
           '<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" '
           'xmlns:l="http://www.w3.org/1999/xlink">']
    xml += desc + body
    if cover_bin:
        xml.append(cover_bin)
    xml.append("</FictionBook>")
    data = "\n".join(xml) + "\n"

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(data)
    print("FB2: %s" % out_path)
    print("  глав: %d, знаков: %d, страниц: %.0f (по %d зн.), размер: %.1f МБ"
          % (n_chapters, total_chars, total_chars / pc, pc, len(data.encode("utf-8")) / 1e6))

    if a.zip:
        zpath = out_path + ".zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(out_path, os.path.basename(out_path))
        print("ZIP: %s (%.1f МБ)" % (zpath, os.path.getsize(zpath) / 1e6))


if __name__ == "__main__":
    main()
