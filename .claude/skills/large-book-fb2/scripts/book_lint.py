#!/usr/bin/env python3
"""Проверка качества текста глав: объём, диалоги, ритм, повторы, штампы.

  book_lint.py <dir> [--chapter N | --from N --to M]

С --chapter печатает подробный разбор главы, без него — сводку по книге.
Это подсказки, а не приговор: смотри на найденные места и решай сам.
«абз. N» — номер абзаца главы (без заголовка, пустых строк и «* * *»).
"""
import argparse
import re
import statistics
from collections import Counter

from bookcommon import body_chars, chapter_texts, chapter_title, iter_chapters, load_book, load_outline, page_chars

# штампы (корни, чтобы ловить формы слов) — references/craft.md, «Чёрный список»
CLICHES = [
    r"сердце (пропустило|бешено|гулко|забилось|ёкнуло|упало)", r"повисл\w* (тишина|молчание|напряжение)",
    r"по спине пробежал\w*", r"кровь (застыла|стыла)", r"глаза\w* (сверкнул|вспыхнул|блеснул)",
    r"губы тронул\w*", r"время (остановилось|замерло)", r"мир (перевернулся|рухнул)",
    r"не мог\w* поверить своим", r"полн\w+ решимости", r"ком в горле", r"не заметив, что задержал",
    r"волна (облегчения|страха|ужаса|тепла|гнева)", r"что-то (внутри )?оборвалось", r"тишину нарушил",
    r"(ещё|еще) не знал\w*, что", r"это было только начало", r"и в этот момент \w+ понял",
    r"холодок\w* (страха|по)", r"сжал\w* кулаки", r"на губах (играла|появилась) улыбка",
    r"(почувствовал|ощутил)\w* (гнев|страх|радость|грусть|тревогу|облегчение)",
]
KANTS = [r"\bявля(ется|ются|лся|лась)\b", r"\bосуществл\w+", r"\bданн(ый|ая|ое|ые|ого|ом)\b",
         r"в связи с тем", r"на сегодняшний день", r"имел\w* место", r"в процессе\b"]
SIMILE_RE = re.compile(r"\b(словно|будто|как будто|точно\s+\w+\s+\w+)\b", re.I)
SENT_RE = re.compile(r"[^.!?…]+[.!?…]+")
WORD_RE = re.compile(r"[а-яё]+", re.I)
STOP = set("""который которая которые которого которой потому только чтобы когда тогда теперь
очень может можно нужно будет было были была этого этой этот этим этих свою своей своего своих
сейчас снова опять всего всегда никогда ничего никто кто-то что-то через после перед между около
сказал сказала спросил спросила ответил ответила даже здесь разве почти слишком""".split())


def sentences(text):
    return [s.strip() for s in SENT_RE.findall(text) if WORD_RE.search(s)]


def analyze(text):
    lines = [l.strip() for l in text.split("\n") if l.strip() and not l.startswith("# ")]
    prose = [l for l in lines if l not in ("* * *", "***") and not l.startswith(">")]
    body = "\n".join(prose)
    low = body.lower()
    chars = max(len(body), 1)
    dialog = sum(len(l) for l in prose if l.startswith(("—", "–", "-")))
    sents = sentences(body)
    lens = [len(WORD_RE.findall(s)) for s in sents] or [0]
    words = [w.lower() for w in WORD_RE.findall(body)]
    caps = set(w.lower() for w in re.findall(r"(?<![.!?…—]\s)\b[А-ЯЁ][а-яё]+", body))
    freq = Counter(w for w in words if len(w) >= 5 and w not in STOP and w not in caps)
    per10k = 10000.0 / chars
    over = [(w, c) for w, c in freq.most_common(15) if c * per10k >= 6 and c >= 6]
    # 3+ фразы подряд с одного слова — только в повествовании (в репликах это часто намеренная анафора)
    runs = []
    for pi, l in enumerate(prose, 1):
        if l.startswith(("—", "–", "-")):
            continue
        ss = sentences(l)
        st = [(WORD_RE.findall(x) or [""])[0].lower() for x in ss]
        for i in range(2, len(st)):
            if st[i] and st[i] == st[i - 1] == st[i - 2]:
                runs.append("абз. %d: «%s…»" % (pi, ss[i - 2][:40]))
                break
    where = {}
    for w, _ in over:
        where[w] = [pi for pi, l in enumerate(prose, 1) if re.search(r"\b%s\b" % w, l.lower())][:6]
    cliche = [m.group(0) for r in CLICHES for m in re.finditer(r, low)]
    kants = [m.group(0) for r in KANTS for m in re.finditer(r, low)]
    para = [len(l) for l in prose] or [0]
    first = sents[0].lower() if sents else ""
    last = prose[-1].lower() if prose else ""
    return {
        "chars": body_chars(text),
        "dialog": 100.0 * dialog / chars,
        "sent_mean": statistics.mean(lens),
        "sent_var": statistics.pstdev(lens) / max(statistics.mean(lens), 1),
        "para_var": statistics.pstdev(para) / max(statistics.mean(para), 1),
        "similes": len(SIMILE_RE.findall(body)) * per10k,
        "over": over,
        "runs": runs,
        "where": where,
        "paras": len(prose),
        "cliche": cliche,
        "kants": kants,
        "weak_open": bool(re.search(r"проснул|открыл\w* глаза|утро (было|выдалось)|солнце (вставало|светило)", first)),
        "weak_end": bool(re.search(r"понял\w*, что|не знал\w*, что|только начало|что ждёт|уснул|заснул|задумал", last)),
    }


def warnings(r, target):
    w = []
    if target and r["chars"] < target * 0.9:
        w.append("%s: %d из %d знаков, не хватает %d — допиши сценой, не водой"
                 % ("коротко" if r["chars"] < target * 0.7 else "чуть меньше цели",
                    r["chars"], target, target - r["chars"]))
    if r["sent_var"] < 0.45:
        w.append("монотонный ритм фраз (разброс %.2f) — чередуй короткие и длинные" % r["sent_var"])
    if r["para_var"] < 0.35:
        w.append("абзацы одной длины — меняй их размер")
    if r["dialog"] < 10:
        w.append("мало диалога (%.0f%%)" % r["dialog"])
    if r["similes"] > 12:
        w.append("много сравнений «словно/будто»: %.0f на 10 тыс. знаков" % r["similes"])
    if r["runs"]:
        w.append("подряд 3+ фразы с одного слова (%d): %s" % (len(r["runs"]), "; ".join(r["runs"][:5])))
    if r["over"]:
        w.append("частые слова: " + ", ".join(
            "%s×%d (абз. %s)" % (x, c, ",".join(map(str, r["where"].get(x, [])))) for x, c in r["over"]))
    if r["cliche"]:
        w.append("штампы: " + "; ".join(sorted(set(r["cliche"]))))
    if r["kants"]:
        w.append("канцелярит: " + ", ".join(sorted(set(r["kants"]))))
    if r["weak_open"]:
        w.append("слабое начало (пробуждение/погода)")
    if r["weak_end"]:
        w.append("слабая концовка (итог/«понял, что»/засыпание) — нужен крючок")
    return w


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--from", dest="first", type=int, default=0)
    ap.add_argument("--to", dest="last", type=int, default=10 ** 9)
    a = ap.parse_args()
    if a.chapter:
        a.first = a.last = a.chapter

    book = load_book(a.dir)
    pc = page_chars(book)
    texts = chapter_texts(a.dir)
    total_warn = 0
    rows = 0
    for _, ch in iter_chapters(load_outline(a.dir)):
        n = ch["num"]
        if not (a.first <= n <= a.last) or n not in texts:
            continue
        r = analyze(texts[n])
        target = int(ch.get("target_pages", 10) * pc)
        title = chapter_title(ch, texts[n]) or "—"
        w = warnings(r, target)
        total_warn += len(w)
        rows += 1
        if a.chapter:
            print("Глава %d «%s»" % (n, title))
            print("  объём %d / %d знаков (%.1f стр.), диалог %.0f%%, фраза %.1f слова (разброс %.2f), "
                  "сравнений %.1f на 10 тыс."
                  % (r["chars"], target, r["chars"] / pc, r["dialog"], r["sent_mean"], r["sent_var"], r["similes"]))
            for line in w or ["замечаний нет"]:
                print("  • " + line)
        else:
            print("%4d %-34.34s %6.1f стр. диалог %3.0f%%  замечаний: %d%s"
                  % (n, title, r["chars"] / pc, r["dialog"], len(w),
                     ("  — " + w[0]) if w else ""))
    if not rows:
        print("Нет написанных глав в выбранном диапазоне.")
    elif not a.chapter:
        print("\nГлав: %d, замечаний: %d. Подробно: book_lint.py %s --chapter N" % (rows, total_warn, a.dir))


if __name__ == "__main__":
    main()
