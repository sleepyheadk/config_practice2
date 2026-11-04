# Визуализатор графа зависимостей pip-пакетов

Консольная утилита на Python, которая строит граф зависимостей pip-пакета.
Сторонние библиотеки не используются, достаточно Python 3.8+.
## Этап 1
Разбор и проверка параметров командной строки,
вывод параметров в формате «ключ: значение».
### Структура проекта
```
src/main.py            - исходный код
tests/tests_phase1.py  - тесты этапа 1
tests/graph.txt        - тестовый репозиторий
run.sh                 - запуск программы на Linux/maxOS
run.bat                - запуск программы на Windows
```
### Параметры 
| параметры                                             | ключ         | значение                              | обрабатываемые ошибки                    |
|-------------------------------------------------------|--------------|---------------------------------------|------------------------------------------|
| Имя анализируемого пакета                             | --package    | строка, обязательный                  | Не задан; пустая строка или одни пробелы; недопустимые символы (допустимы буквы, цифры, `-`, `_`, `.`); имя начинается или заканчивается не буквой/цифрой |
| URL-адрес репозитория или путь к файлу тестового репозитория | --repo       | строка, обязательный                  | Не задан; пустая строка. В обычном режиме: не http/https, нет хоста. В тестовом режиме: файл не существует, это папка |
| Режим работы с тестовым репозиторием                  | --test-mode  | флаг без значения, по умолчанию false | Передано значение у флага; включён тестовый режим, а в repo указан URL вместо пути к файлу |
| Имя сгенерированного файла с изображением графа       | --output     | строка, по умолчанию graph.svg        | Пустое имя; расширение не `.svg`; указанная папка не существует; имя совпадает с существующей папкой |
| Режим вывода зависимостей в формате ASCII-дерева      | --ascii-tree | флаг без значения, по умолчанию false | Передано значение у флага |
| Подстрока для фильтрации пакетов                      | --filter     | строка, по умолчанию пустая           | Опция указана без значения |

### Функции (src/main.py)

| Функция | Назначение |
|---|---|
| `parse_args()` | разбирает аргументы командной строки (argparse) |
| `ConfigError` | исключение для ошибок в параметрах пользователя |
| `validate_package(name)` | проверяет имя пакета |
| `validate_repo(repo, test_mode)` | проверяет URL или путь к файлу тестового репозитория |
| `validate_output(output)` | проверяет имя выходного `.svg`-файла |
| `validate_args(args)` | вызывает все проверки |
| `main()` | точка входа: разбор, проверка, вывод параметров |

Коды выхода: `0` - успех, `1` - ошибка параметров, `2` - ошибка argparse
(например, неизвестная опция).

### Запуск и тесты

Запуск программы:

```commandline
python src/main.py --package requests --repo https://pypi.org/pypi
```

Или через скрипты:

- Windows: `run.bat --package requests --repo https://pypi.org/pypi`
- Linux/macOS: `./run.sh --package requests --repo https://pypi.org/pypi`

Запуск тестов (из корня проекта):

```commandline
python -m unittest discover -s tests -p "tests_*.py" -v
```

### Пример работы программы

1. Введены верные имя пакета и репозиторий
`python3 src/main.py --package requests --repo https://pypi.org/pypi`
Вывод:
```commandline
package: requests
repo: https://pypi.org/pypi
test_mode: False
output: graph.svg 
ascii_tree: False  
filter:
```
2. Все опции
`python3 src/main.py --package A --repo tests/graph.txt --test-mode --output out.svg --ascii-tree --filter test`
Вывод:
```commandline
package: A 
repo: tests/graph.txt  
test_mode: True            
output: out.svg               
ascii_tree: True           
filter: test
```
3. Без параметров
`python3 src/main.py`
Вывод:
`Ошибка: имя пакета не задано (--package)`
4. Репозиторий не URL
`python3 src/main.py --package requests --repo pypi.org`
Вывод:
`Ошибка: некорректный URL: pypi.org`
5. Неверное расширение
`python3 src/main.py --package requests --repo https://pypi.org/pypi --output graph.png
`
Вывод:
`Ошибка: выходной файл должен иметь расширение .svg`
6. Неизвестная опция: ошибка argparse, код 2
`python3 src/main.py --package requests --repo https://pypi.org/pypi --foo`
Вывод:
`main.py: error: unrecognized arguments: --foo`

