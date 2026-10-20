# FB2: кратко

FB2 (FictionBook 2.0) — XML-формат электронных книг. Сборщик `book_build.py` делает всё сам; здесь — то, что нужно знать для `book.json` и текста глав.

## Структура файла

```xml
<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">
  <description>
    <title-info> genre+, author+, book-title, annotation?, keywords?, date?, coverpage?, lang </title-info>
    <document-info> author, program-used, date, id, version </document-info>
  </description>
  <body>
    <title>…</title>
    <section>            ← часть
      <title><p>Часть первая</p><p>Название</p></title>
      <section>          ← глава
        <title><p>Глава 1</p><p>Название</p></title>
        <epigraph><p>…</p></epigraph>
        <p>Абзац…</p>
        <subtitle>* * *</subtitle>
      </section>
    </section>
  </body>
  <binary id="cover.jpg" content-type="image/jpeg">base64…</binary>
</FictionBook>
```

## Разметка текста глав → FB2

| В файле главы | В FB2 |
|---|---|
| `# Название` (первая строка) | `<title>` главы |
| строка текста | `<p>` |
| `* * *` / `***` | `<subtitle>* * *</subtitle>` |
| `> строка` в начале главы | `<epigraph>` |
| `> — Автор` после эпиграфа | `<text-author>` |
| `> строка` в середине | `<cite>` |
| `*текст*` | `<emphasis>` |
| `**текст**` | `<strong>` |
| пустая строка | игнорируется |

## Коды жанров (поле `genres` в book.json)

| Код | Жанр |
|---|---|
| `adventure` | Приключения |
| `adv_history` | Исторические приключения |
| `adv_maritime` | Морские приключения |
| `prose_history` | Историческая проза |
| `prose_classic` | Классическая проза |
| `prose_contemporary` | Современная проза |
| `love_history` | Исторический любовный роман |
| `love_contemporary` | Современный любовный роман |
| `det_classic` | Классический детектив |
| `det_history` | Исторический детектив |
| `thriller` | Триллер |
| `sf` | Научная фантастика |
| `sf_fantasy` | Фэнтези |
| `sf_epic` | Эпическая фантастика |
| `sf_horror` | Ужасы |
| `sf_space` | Космическая фантастика |
| `sf_social` | Социальная фантастика |
| `child_adv` | Детские приключения |

Можно указать несколько: `"genres": ["adv_history", "adventure"]`.
