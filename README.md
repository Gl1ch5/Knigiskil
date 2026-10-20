# Knigiskil

Навык Claude Code **large-book-fb2** — создание больших книг (1000–4000+ страниц) в формате FB2.

- Навык: [`.claude/skills/large-book-fb2/SKILL.md`](.claude/skills/large-book-fb2/SKILL.md)
- Скрипты: `.claude/skills/large-book-fb2/scripts/` (Python 3, без зависимостей)
- Пример книги: `books/` (проект, главы и итоговый `.fb2`)

Этапы: изучение запроса и стиля → краткий сюжет и «Подходит?» → вопрос про спойлеры и остальные параметры → библия мира → поглавный план → пакеты для параллельных субагентов → контроль объёма → сборка и проверка FB2.

```bash
S=.claude/skills/large-book-fb2/scripts
python3 $S/book_init.py books/my-book --title "Название" --author "Имя Фамилия" --pages 4000 --genre adventure
python3 $S/book_plan.py skeleton books/my-book --parts 8 --chapter-pages 10
python3 $S/book_plan.py batches books/my-book --size 5
python3 $S/book_status.py books/my-book
python3 $S/book_build.py books/my-book --zip
python3 $S/book_validate.py books/my-book/out/my-book.fb2
```
