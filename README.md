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
`python src/main.py --package requests --repo https://pypi.org/pypi`
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
`python src/main.py --package A --repo tests/graph.txt --test-mode --output out.svg --ascii-tree --filter test`
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
`python src/main.py`
Вывод:
`Ошибка: имя пакета не задано (--package)`
4. Репозиторий не URL
`python src/main.py --package requests --repo pypi.org`
Вывод:
`Ошибка: некорректный URL: pypi.org`
5. Неверное расширение
`python src/main.py --package requests --repo https://pypi.org/pypi --output graph.png
`
Вывод:
`Ошибка: выходной файл должен иметь расширение .svg`
6. Неизвестная опция: ошибка argparse, код 2
`python src/main.py --package requests --repo https://pypi.org/pypi --foo`
Вывод:
`main.py: error: unrecognized arguments: --foo`

## Этап 2

Получение прямых зависимостей пакета по URL репозитория (JSON-интерфейс PyPI)
и вывод их на экран. Менеджеры пакетов и сторонние библиотеки не
используются, запрос выполняется стандартным `urllib`.

### Структура проекта

```
src/main.py            - точка входа
src/cli.py             - разбор аргументов командной строки
src/validation.py      - проверка параметров
src/errors.py          - ошибки ConfigError и RepositoryError
src/repository.py      - скачивание метаданных пакета по URL
src/requirement.py     - разбор строки зависимости (PEP 508)
src/dependencies.py    - получение списка прямых зависимостей
tests/tests_phase2.py  - тесты этапа 2
tests/graph.txt        - тестовый репозиторий
run.sh                 - запуск программы на Linux/macOS
run.bat                - запуск программы на Windows
```

### Описание

1. Программа запрашивает `<repo>/<package>/json` и получает метаданные пакета
   последней версии.
2. Из поля `info.requires_dist` берутся строки зависимостей
   (например, `urllib3<3,>=1.21.1`) и разбираются на имя, версии и условие.
3. Зависимости с условием `extra == ...` (опциональные дополнения)
   пропускаются. Остальные условия (`python_version`, `sys_platform`)
   не вычисляются, такие зависимости остаются в списке.
4. Имена приводятся к единому виду (нижний регистр, `_` и `.` заменяются
   на `-`), повторы убираются.
5. Список имён выводится на экран, по одному на строку.

Вывод параметров «ключ: значение» из этапа 1 убран. Тестовый режим
(`--test-mode`) пока выдаёт ошибку, он будет реализован на этапе 3.
Ошибки репозитория (пакет не найден, нет связи, неверный ответ) выводятся
как `Ошибка: ...` с кодом выхода 1.

### Добавленные функции

| Файл | Функция | Назначение |
|---|---|---|
| `repository.py` | `fetch_package_info(repo, package)` | скачивает и разбирает JSON с метаданными пакета |
| `repository.py` | `build_url`, `download`, `parse_json` | формирование адреса, запрос, разбор ответа |
| `requirement.py` | `parse_requirement(line)` | разбирает строку зависимости на имя, версии, условие |
| `requirement.py` | `normalize_name`, `is_extra` | нормализация имени, проверка на опциональную зависимость |
| `dependencies.py` | `get_direct_dependencies(package, repo)` | возвращает имена прямых зависимостей |
| `dependencies.py` | `extract_requirement_lines(data)` | достаёт `requires_dist` из метаданных |
| `main.py` | `run(args)`, `print_dependencies(...)` | получение и вывод зависимостей |
| `errors.py` | `RepositoryError` | ошибка получения данных из репозитория |

### Примеры работы программы

1. Пакет с зависимостями
`python src/main.py --package requests --repo https://pypi.org/pypi`
Вывод:
```commandline
Прямые зависимости пакета requests:
charset-normalizer
idna
urllib3
certifi
```
2. Пакет без зависимостей
`python src/main.py --package six --repo https://pypi.org/pypi`
Вывод:
```commandline
У пакета six нет прямых зависимостей
```
3. Зависимость с условием (`colorama` только для Windows, условие не вычисляется)
`python src/main.py --package click --repo https://pypi.org/pypi`
Вывод:
```commandline
У пакета click нет прямых зависимостей
```
4. Пакет не найден
`python src/main.py --package no-such-pkg-12345 --repo https://pypi.org/pypi`
Вывод:
```commandline
Ошибка: пакет не найден в репозитории (https://pypi.org/pypi/no-such-pkg-12345/json)
```
5. Репозиторий недоступен
`python src/main.py --package requests --repo https://no-such-host-12345.org/pypi`
Вывод:
```commandline
Ошибка: не удалось подключиться к https://no-such-host-12345.org/pypi/requests/json: [Errno 11001] getaddrinfo failed
```
6. Тестовый режим пока не поддерживается
`python src/main.py --package A --repo tests/graph.txt --test-mode`
Вывод:
```commandline
Ошибка: тестовый режим пока не реализован
```