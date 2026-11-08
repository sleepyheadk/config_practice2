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

## Этап 3

Построение полного графа зависимостей пакета (с учётом транзитивности) и
основные операции над ним. Граф строится обходом в глубину (DFS) без
рекурсии, с явным стеком.

### Структура проекта

```
src/main.py             - точка входа
src/cli.py              - разбор аргументов командной строки
src/validation.py       - проверка параметров
src/errors.py           - ошибки ConfigError и RepositoryError
src/repository.py       - скачивание метаданных пакета по URL
src/requirement.py      - разбор строки зависимости (PEP 508)
src/dependencies.py     - прямые зависимости пакета, выбор источника данных
src/file_repository.py  - чтение тестового репозитория из файла
src/graph.py            - построение графа: DFS без рекурсии, фильтр, циклы
src/report.py           - текстовый вывод графа и циклов
tests/tests_phase1.py   - тесты этапа 1
tests/tests_phase2.py   - тесты этапа 2
tests/tests_phase3.py   - тесты этапа 3
tests/graph.txt         - тестовый репозиторий
run.sh                  - запуск программы на Linux/macOS
run.bat                 - запуск программы на Windows
```

### Что добавлено

- **Транзитивные зависимости.** Для каждого пакета запрашиваются его прямые
  зависимости, затем зависимости этих зависимостей и так далее. Каждый пакет
  обрабатывается один раз, поэтому общие зависимости не дублируются и
  лишних запросов к репозиторию нет.
- **DFS без рекурсии.** Обход выполняется циклом с явным стеком, поэтому
  глубина графа не ограничена лимитом рекурсии Python.
- **Фильтр `--filter`.** Пакеты, в имени которых есть заданная подстрока
  (без учёта регистра), не попадают в граф и не обходятся. Если подстрока
  входит в имя самого анализируемого пакета, программа сообщает об ошибке.
- **Циклические зависимости.** Если пакет зависит от пакета, лежащего на
  текущем пути обхода (в том числе от самого себя), цикл фиксируется и
  выводится в отчёте, обход в него не заходит и не зависает.
- **Тестовый режим `--test-mode`.** Вместо URL в `--repo` указывается путь
  к файлу с описанием графа, пакеты называются большими латинскими буквами.
- **Вывод.** Для каждого пакета графа выводится строка
  `пакет -> зависимости` в порядке обхода, затем найденные циклы.

В обычном режиме имена пакетов приводятся к единому виду (нижний регистр,
`_` и `.` заменяются на `-`). Если запрос зависимости к репозиторию завершился
ошибкой, программа выводит `Ошибка: ...` и завершается с кодом 1.

### Формат файла тестового репозитория

Одна строка на пакет: имя, двоеточие, зависимости через пробел. Допустимы
только большие латинские буквы. Пустые строки и комментарии (после `#`)
игнорируются. Пакет, который упомянут только как зависимость, считается
пакетом без зависимостей.

Содержимое `tests/graph.txt`:

```
# Ромб: D - общая зависимость B и C
A: B C
B: D
C: D
D:

# Цикл из трёх пакетов
E: F
F: G
G: E

# Пакет зависит сам от себя
H: H

# J есть только как зависимость, своей строки нет
I: J

# Фильтр по подстроке: --package K --filter A исключит KA и LA
K: KA KB LA
```

### Добавленные функции

| Файл | Функция | Назначение |
|---|---|---|
| `graph.py` | `build_graph(root, get_dependencies, substring)` | строит граф обходом DFS без рекурсии, возвращает граф и список циклов |
| `graph.py` | `is_excluded`, `visible_dependencies` | применение фильтра по подстроке |
| `file_repository.py` | `make_file_provider(path)` | читает тестовый репозиторий и возвращает функцию «пакет -> зависимости» |
| `file_repository.py` | `parse_repository`, `parse_line`, `read_file`, `make_lookup` | чтение и проверка формата файла |
| `dependencies.py` | `make_source(package, repo, test_mode)` | выбирает источник данных: PyPI по URL или файл |
| `report.py` | `format_report` и вспомогательные | формирует текст с графом и циклами |
| `validation.py` | `validate_filter` | проверка, что фильтр не исключает анализируемый пакет |
| `main.py` | `run(args)` | построение графа и вывод |

### Примеры работы программы

1. Тестовый репозиторий: общая зависимость (ромб)
`python src/main.py --package A --repo tests/graph.txt --test-mode`
Вывод:
```commandline
Граф зависимостей пакета A:
A -> B, C
B -> D
D -> (нет зависимостей)    
C -> D
Циклических зависимостей нет
```
2. Цикл из трёх пакетов
`python src/main.py --package E --repo tests/graph.txt --test-mode`
Вывод:
```commandline
Граф зависимостей пакета E:
E -> F
F -> G
G -> E
Циклические зависимости:
E -> F -> G -> E
```
3. Пакет зависит сам от себя
`python src/main.py --package H --repo tests/graph.txt --test-mode`
Вывод:
```commandline
Граф зависимостей пакета H:
H -> H
Циклические зависимости:
H -> H
```
4. Зависимость без собственной строки в файле
`python src/main.py --package I --repo tests/graph.txt --test-mode`
Вывод:
```commandline
Граф зависимостей пакета I:
I -> J
J -> (нет зависимостей)
Циклических зависимостей нет
```
5. Фильтр по подстроке
`python src/main.py --package K --repo tests/graph.txt --test-mode --filter A`
Вывод:
```commandline
Граф зависимостей пакета K:
K -> KB
KB -> (нет зависимостей)
Циклических зависимостей нет
```
6. Реальный репозиторий: полный граф зависимостей
`python src/main.py --package requests --repo https://pypi.org/pypi`
Вывод:
```commandline
Граф зависимостей пакета requests:
requests -> charset-normalizer, idna, urllib3, certifi
charset-normalizer -> (нет зависимостей)
idna -> (нет зависимостей)
urllib3 -> (нет зависимостей)
certifi -> (нет зависимостей)
Циклических зависимостей нет
```
7. Реальный репозиторий с фильтром
`python src/main.py --package requests --repo https://pypi.org/pypi --filter urllib`
Вывод:
```commandline
Граф зависимостей пакета requests:
requests -> charset-normalizer, idna, certifi
charset-normalizer -> (нет зависимостей)
idna -> (нет зависимостей)
certifi -> (нет зависимостей)
Циклических зависимостей нет
```
8. Фильтр исключает анализируемый пакет
`python src/main.py --package A --repo tests/graph.txt --test-mode --filter A`
Вывод:
```commandline
Ошибка: фильтр исключает анализируемый пакет
```
9. Пакета нет в тестовом репозитории
`python src/main.py --package Z --repo tests/graph.txt --test-mode`
Вывод:
```commandline
Ошибка: пакет Z не найден в тестовом репозитории
```
10. Файл неверного формата (для проверки подставлен README.md)
`python src/main.py --package A --repo README.md --test-mode`
Вывод:
```commandline
Ошибка: строка 3: ожидается формат 'A: B C'
```
11. Файл тестового репозитория не найден
`python src/main.py --package A --repo nofile.txt --test-mode`
Вывод:
```commandline
Ошибка: файл не найден
```
