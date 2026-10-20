# Knigiskil

Навык Claude Code **large-book-fb2** — написание книг любого объёма (от 50 до 4000+ страниц) с готовым файлом FB2. Автор всех книг — постоянный псевдоним **Павел М**.

- Навык: [`.claude/skills/large-book-fb2/SKILL.md`](.claude/skills/large-book-fb2/SKILL.md)
- Основы мастерства: [`references/craft.md`](.claude/skills/large-book-fb2/references/craft.md), стиль: [`references/styles.md`](.claude/skills/large-book-fb2/references/styles.md)
- Скрипты: `.claude/skills/large-book-fb2/scripts/` (Python 3, без зависимостей)
- Пример книги: `books/zolotoy-zhrebiy/` — «Золотой жребий», итог в `out/zolotoy-zhrebiy.fb2`

Этапы: уточняющие вопросы → паспорт стиля, концепция и пробный абзац, «Подходит?» → библия мира и план (части и главы считаются по объёму: 500 стр. ≈ 3 части, 23 главы) → агент сам пишет главу за главой по сценам с проверкой качества → сборка и проверка FB2.

```bash
S=.claude/skills/large-book-fb2/scripts
python3 $S/book_init.py books/my-book --title "Название" --pages 500 --genre adventure
python3 $S/book_plan.py skeleton books/my-book      # части и главы по объёму
python3 $S/book_plan.py next books/my-book          # задание на следующую главу
python3 $S/book_lint.py books/my-book --chapter 1   # качество текста главы
python3 $S/book_status.py books/my-book
python3 $S/book_build.py books/my-book --zip
python3 $S/book_validate.py books/my-book/out/my-book.fb2
```
