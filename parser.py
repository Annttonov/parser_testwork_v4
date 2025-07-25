"""Модуль для парсинга учебных материалов по математике из MD
в структурированные данные."""
import re

from constants import (CHAPTER_RE, CLASSES, LEVEL_RE, LEVLES, ONLY_CHAPTER_RE,
                       SYMBOLS, TASK_NUMBER_RE, TASK_RE, VAR_RE)


class Parser:
    """Базовый класс парсера с общими методами."""

    def find_index(self, content, name):
        """Находит индекс начала указанного раздела в контенте.

        Args:
            content (list): Список строк контента
            name (str): Название раздела для поиска

        Returns:
            int: Индекс начала раздела

        Raises:
            ValueError: Если раздел не найден
        """
        index = 0
        while index < len(content):
            item: str = content[index]
            if item.lower().endswith(name):
                return index + 1
            index += 1
        raise ValueError('Требуемое значение не найдено!')

    def normalize_symbol(self, symbol):
        """Нормализует специальные символы в тексте.

        Args:
            symbol (str): Символ для нормализации

        Returns:
            str: Нормализованный символ
        """
        return SYMBOLS[symbol] if symbol in SYMBOLS else symbol


class TaskParcer(Parser):
    """Основной класс для парсинга задач из учебного материала."""

    def __init__(self, content):
        """Инициализация парсера задач.

        Args:
            content (list): Список строк контента документа
        """
        self.outline = OutlineParser(content).outline
        self.answers = AnswerParser(content).answers
        self.description = self.get_description(content)
        self.tasks = self.process(content)
        self.outline = self.recoding_outline_to_list()

    def process(self, content):
        """Основной метод обработки контента.

        Args:
            content (list): Список строк контента

        Returns:
            list: Список словарей с данными о задачах
        """
        index = 0
        result = []
        while index < len(content):
            item, index = self.get_item(content, index)
            if item.lower() == 'ответы':
                index += 1
                break
            chapter_match = CHAPTER_RE.search(item)
            if chapter_match:
                index, chapter_data = self.find_chapter_index(
                    content,
                    start_index=index)
                chapter_symbol = self.normalize_symbol(
                    chapter_match.group(1)[0])
                chapter = chapter_symbol + chapter_match.group(1)[1:-1]
                result = self.parse_chapter(
                    chapter_data, chapter, result)
            else:
                index += 1
        return result

    def get_description(self, content):
        """Извлекает метаданные учебника (название, автора, описание).

        Args:
            content (list): Список строк контента

        Returns:
            list: Список с метаданными учебника
        """
        item, index = self.get_item(content, 0)
        result = list()
        description = {
            'name': '',
            'author': item,
            'description': '',
            'topic_id': '1',
            'classes': CLASSES
        }
        while index < len(content):
            item, index = self.get_item(content, index)
            if item.lower() == 'тригонометрия':
                break
            if 'САМОСТОЯТЕЛЬНЫЕ и КОНТРОЛЬНЫЕ РАБОТЫ' in item:
                description['name'] = item.capitalize()
                continue
            if 'Основные особенности предлагаемого сборника' in item:
                text = str()
                index += 1
                while index < len(content):
                    item, index = self.get_item(content, index)
                    if item.lower() == 'тригонометрия':
                        break
                    text = f'{text}\n{item}' if text != '' else item
                description['description'] = text
                result.append(description)
                return result

    def get_normal_string(self, string, index, text):
        """Обрабатывает специальные строки (например, LaTeX выражения).

        Args:
            string (str): Начальная строка
            index (int): Текущий индекс в контенте
            text (list): Полный контент документа

        Returns:
            tuple: (обработанная строка, новый индекс)
        """
        while True:
            item = text[index]
            if item == '$$':
                string += item
                break
            string += item
            index += 1
        return string, index

    def parse_tables_with_variant(self, string):
        """Парсит таблицы с вариантами задач.

        Args:
            string (str): Строка таблицы

        Returns:
            tuple: (вариант 1, вариант 2)
        """
        items = string.split('|')
        var_1 = {}
        var_2 = {}
        for item in items:
            item = item.strip()
            if item == ':---':
                return {}, {}
            if item == '':
                continue
            var_match = TASK_RE.search(item.strip())
            if var_match:
                if var_1 != {} and var_1.get('num') == var_match.group(1):
                    var_2 = {
                        'num': var_match.group(1),
                        'text': item
                    }
                elif var_1 == {}:
                    var_1 = {
                        'num': var_match.group(1),
                        'text': item
                    }
                else:
                    print(f'{var_1.keys()}\n{var_2.keys()}')
                    var_1 = {
                        'num': var_match.group(1),
                        'text': item
                    }
            elif var_1 != {}:
                var_2 = {
                        'num': 0,
                        'text': item
                    }
            else:
                var_1 = {
                    'num': 0,
                    'text': item
                }
        return var_1, var_2

    def get_normalise_variant(self, var, new_var, var_list):
        """Нормализует варианты задач.

        Args:
            var (dict): Текущий вариант
            new_var (dict): Новый вариант
            var_list (list): Список вариантов

        Returns:
            tuple: (нормализованный вариант, обновленный список)
        """
        if new_var != {}:
            if new_var.get('num') == 0:
                var['text'] = f'{var['text']} {new_var['text']}'
            elif var.get('num') != new_var.get('num'):
                var_list.append(var)
                var = new_var
        return var, var_list

    def get_item(self, content, index):
        """Извлекает и обрабатывает элемент контента.

        Args:
            content (list): Список строк контента
            index (int): Текущий индекс

        Returns:
            tuple: (обработанный элемент, новый индекс)
        """
        item = content[index]
        if item == '' or item == '\n':
            item, index = self.get_item(content, index + 1)
            return item, index
        if item == '$$':    # формирует LaTeX-выражение
            item, index = self.get_normal_string(
                string=item,
                index=index+1,
                text=content
            )
        elif item.startswith(('#')):
            item = item.replace('#', '').strip()
        elif item.startswith(('>')):
            item = item.replace('>', '').strip()
        elif item.startswith('![]'):
            item = item[4:-1]
        elif item.endswith('|'):
            table = []
            var_1, var_2 = self.parse_tables_with_variant(item)
            index += 1
            next_item = content[index]
            while next_item.endswith('|') and len(
                    next_item.split('|')) == len(item.split('|')):
                var_1_new, var_2_new = self.parse_tables_with_variant(
                    next_item)
                var_list = []
                var_1, var_list = self.get_normalise_variant(
                    var_1, var_1_new, var_list)
                var_2, var_list = self.get_normalise_variant(
                    var_2, var_2_new, var_list)
                index += 1
                next_item = content[index]
                if var_list != []:
                    for i in var_list:
                        table.append(i)
                var_list = []
            for i in [var_1, var_2]:
                table.append(i)
            item = table
        index += 1
        return item, index

    def find_chapter_index(self, content: list, start_index: int):
        """Находит индекс главы и ее содержимое.

        Args:
            content (list): Список строк контента
            start_index (int): Индекс начала поиска

        Returns:
            tuple: (индекс конца главы, содержимое главы)
        """
        index = start_index
        chapter_data = list()
        while index < len(content):
            item, index = self.get_item(content, index)
            if isinstance(item, list):
                for i in item:
                    chapter_data.append(i.get('text'))
                continue
            elif item.lower() == 'ответы':
                return index - 1, chapter_data
            chapter_match = CHAPTER_RE.search(item)
            if chapter_match:
                return index - 1, chapter_data
            chapter_data.append(item)
        return index - 1, chapter_data

    def find_variant(self, match, data, next_index):
        """Проверяет наличие варианта задачи.

        Args:
            match (re.Match): Результат поиска по регулярному выражению
            data (list): Список строк контента
            next_index (int): Следующий индекс для проверки

        Returns:
            re.Match or None: Результат проверки или None
        """
        if match:
            task_number_match = TASK_NUMBER_RE.search(data[next_index])
            if task_number_match:
                return match

    def parse_chapter(self, data, chapter_num, result):
        """Парсит содержимое главы.

        Args:
            data (list): Содержимое главы
            chapter_num (str): Номер главы
            result (list): Аккумулируемый результат

        Returns:
            list: Обновленный результат с задачами из главы
        """
        if data == []:
            return result
        index = 0
        while index < len(data):
            item = data[index]
            if self.find_variant(VAR_RE.search(item), data, index + 1):
                result, index = self.parse_variant(
                    data, index, chapter_num, result)
            elif LEVEL_RE.search(item):
                result, index = self.parse_level(
                    data, index, chapter_num, result)
            else:
                index += 1
            if CHAPTER_RE.search(item):
                return result
        return result

    def normalize_variant(self, symbol: str):
        """Нормализует символ варианта.

        Args:
            symbol (str): Символ варианта

        Returns:
            str: Нормализованный символ варианта
        """
        symbol = SYMBOLS[symbol] if symbol in SYMBOLS else symbol
        return symbol if symbol.isalnum() else symbol.upper()

    def parse_variant(self, data, index, chapter_num, result):
        """Парсит варианты задач в главе.

        Args:
            data (list): Содержимое главы
            index (int): Текущий индекс
            chapter_num (str): Номер главы
            result (list): Аккумулируемый результат

        Returns:
            tuple: (обновленный результат, новый индекс)
        """
        current_variant = self.normalize_variant(
            VAR_RE.search(data[index]).group(1))
        index += 1
        while index < len(data):
            item = data[index]
            task_number_match = TASK_NUMBER_RE.search(item)
            if task_number_match:
                task_number = task_number_match.group(1)
                index += 1
                unparse_tasks, index = self.find_tasks(
                    data, index, task_number)
                tasks_list = self.parse_tasks(unparse_tasks)
                result = self.save_tasks(
                    tasks_list=tasks_list,
                    result=result,
                    answers=self.answers,
                    chapter_num=chapter_num,
                    variant=current_variant,
                    task_number=task_number)
                continue
            if self.find_variant(VAR_RE.search(item), data, index + 1) or (
                    LEVEL_RE.search(item)):
                return result, index
            if CHAPTER_RE.search(item):
                return result, index
        return result, index

    def parse_level(self, data, index, chapter_num, result):
        """Парсит задачи по уровням сложности.

        Args:
            data (list): Содержимое главы
            index (int): Текущий индекс
            chapter_num (str): Номер главы
            result (list): Аккумулируемый результат

        Returns:
            tuple: (обновленный результат, новый индекс)
        """
        current_level = ''
        tasks_list = {'task_condition': data[0]}
        while index < len(data):
            item = data[index]
            level_match = LEVEL_RE.search(item)
            if level_match:
                current_level = level_match.group(1)
                index += 1
                unparse_tasks, index = self.find_tasks(
                    data, index, current_level)
                tasks_list = self.parse_level_tasks(
                    unparse_tasks, current_level, tasks_list)
                continue
            if CHAPTER_RE.search(item):
                result = self.save_tasks(
                    tasks_list,
                    result,
                    chapter_num,
                    answers=self.answers,
                    its_level=True)
                return result, index
        result = self.save_tasks(
            tasks_list,
            result,
            chapter_num,
            answers=self.answers,
            its_level=True)
        return result, index

    def parse_level_tasks(self, unparse_tasks, level, tasks):
        """Парсит задачи определенного уровня сложности.

        Args:
            unparse_tasks (list): Необработанные задачи
            level (str): Уровень сложности
            tasks (dict): Аккумулируемый результат

        Returns:
            dict: Обновленный словарь задач
        """
        index = 0
        if not tasks.get(level):
            tasks[level] = {}
        while index < len(unparse_tasks):
            item = unparse_tasks[index]
            match = TASK_RE.search(item)
            if match:
                tasks[level] = self.write_item(
                    tasks[level],
                    item[match.end():],
                    match.group(1)
                )

            else:
                raise IndentationError('Неожиданная строка!')
            index += 1
        return tasks

    def normalize_item(self, item):
        """Нормализует элемент задачи.

        Args:
            item (str): Текст задачи

        Returns:
            str: Нормализованный текст задачи
        """
        item = re.sub(r'\[\^\d\]', '', item, 1)
        item = re.sub(r'^a+?\)\s', 'а) ', item, 1)
        return item

    def write_condition_in_variants(self, match, data):
        current_task_symbol = match.group(1)
        data[current_task_symbol] = {
                    'v1': match.string[match.end():],
                }
        return data, current_task_symbol

    def parse_tasks(self, unparse_tasks):
        """Парсит список задач.

        Args:
            unparse_tasks (list): Необработанные задачи

        Returns:
            dict: Структурированные данные задач
        """

        current_task_symbol = ''
        tasks = {
            'task_condition': ''}
        task_condition = unparse_tasks[0]
        condition_match = TASK_RE.search(
            self.normalize_item(task_condition)
        )
        if condition_match:
            tasks, current_task_symbol = self.write_condition_in_variants(
                condition_match, tasks)
        else:
            tasks['task_condition'] = unparse_tasks[0]
        index_v1 = 1
        index_v2 = 2
        if index_v1 >= len(unparse_tasks):
            return tasks
        if index_v2 >= len(unparse_tasks):
            tasks['task'] = {'v1': unparse_tasks[index_v1]}
            return tasks
        while index_v1 < len(unparse_tasks) and index_v2 < len(unparse_tasks):
            item_v1 = self.normalize_item(unparse_tasks[index_v1])
            item_v2 = self.normalize_item(unparse_tasks[index_v2])
            v1_match = TASK_RE.search(item_v1)
            v2_match = TASK_RE.search(item_v2)
            if v1_match and v2_match:
                if v1_match.group(1) == v2_match.group(1):
                    current_task_symbol = v1_match.group(1)
                    tasks[current_task_symbol] = {
                        'v1': item_v1[v1_match.end():],
                        'v2': item_v2[v2_match.end():]
                    }
                elif current_task_symbol == v1_match.group(1):
                    tasks[current_task_symbol] = self.write_item(
                        tasks[current_task_symbol],
                        item_v1[v1_match.end()],
                        'v1'
                    )
                else:
                    tasks[v1_match.group(1)] = {
                        'v1': item_v1[v1_match.end():],
                    }
                    index_v1, index_v2 = index_v1 + 1, index_v2 + 1
                    continue
            elif v1_match or v2_match:
                if tasks['task_condition'] == '':
                    match = v1_match if v1_match else v2_match
                    tasks, current_task_symbol = \
                        self.write_condition_in_variants(
                            match, tasks)
                elif v1_match:
                    current_task_symbol = v1_match.group(1)
                    tasks[current_task_symbol] = {
                        'v1': item_v1[v1_match.end():]
                    }
                elif current_task_symbol == '':
                    if not tasks.get('task'):
                        tasks['task'] = {}
                    tasks['task'] = self.write_item(
                        tasks['task'], item_v1, 'v1')
                else:
                    tasks[current_task_symbol] = {
                        'v1': item_v1
                    }
                index_v1, index_v2 = index_v1 + 1, index_v2 + 1
                continue
            elif (not v1_match and not v2_match) and current_task_symbol != '':
                if condition_match and not tasks[current_task_symbol].get('v2'
                                                                          ):
                    tasks[current_task_symbol]['v2'] = tasks[
                        current_task_symbol]['v1']
                tasks[current_task_symbol] = self.write_item(
                    tasks[current_task_symbol],
                    item_v1,
                    'v1')
                tasks[current_task_symbol] = self.write_item(
                    tasks[current_task_symbol],
                    item_v2,
                    'v2')
            else:
                if not tasks.get('task'):
                    tasks['task'] = {}
                tasks['task'] = self.write_item(tasks['task'], item_v1, 'v1')
                tasks['task'] = self.write_item(tasks['task'], item_v2, 'v2')
            index_v1, index_v2 = index_v1 + 2, index_v2 + 2

        if index_v1 >= len(unparse_tasks):
            return tasks
        elif index_v1 < len(unparse_tasks):
            task_match = TASK_RE.search(unparse_tasks[index_v1])
            if current_task_symbol != '' and task_match:
                tasks[current_task_symbol] = self.write_item(
                    tasks[current_task_symbol],
                    unparse_tasks[index_v1][task_match.end():],
                    'v1')
            elif task_match:
                if not tasks.get(task_match.group(1)):
                    tasks[task_match.group(1)] = {}
                tasks[task_match.group(1)] = self.write_item(
                    tasks[task_match.group(1)],
                    unparse_tasks[index_v1][task_match.end():],
                    'v1')
            else:
                if not tasks.get('task'):
                    tasks['task'] = {}
                tasks['task'] = self.write_item(tasks['task'],
                                                unparse_tasks[index_v1],
                                                'v1')
        tasks = self.check_task_condition(tasks)
        return tasks

    def check_task_condition(self, tasks: dict):
        task = False
        condition = False
        for item in tasks.keys():
            if task and condition:
                return self.reorganise_tasks(tasks)
            if item == 'task':
                task = True
            elif re.search(r'\d|\w', item):
                condition = True
        return tasks

    def reorganise_tasks(self, tasks):
        for item in tasks['task'].values():
            tasks['task_condition'] = f'{tasks['task_condition']} {item}'
        tasks.pop('task')
        return tasks

    def write_item(self, data, item, key):
        """Добавляет элемент в словарь данных.

        Args:
            data (dict): Текущие данные
            item (str): Текст для добавления
            key (str): Ключ для добавления

        Returns:
            dict: Обновленный словарь данных
        """
        if data.get(key):
            data[key] = f'{data[key]} {item}'
        else:
            data[key] = item
        return data

    def update_outline(self, chapter, variant, outline) -> str:
        if outline[chapter]['variants'].get(variant):
            return outline[chapter]['variants'][variant]['id']
        outline[chapter]['variants'][variant] = {
            'id': outline['next_id'],
            'name': f'Вариант {variant}',
            'parent': outline[chapter]['id']
        }
        outline['next_id'] += 1
        return outline[chapter]['variants'][variant]['id']

    def save_tasks(self, tasks_list: dict,
                   result: list,
                   chapter_num: str,
                   answers: dict,
                   variant: str = None,
                   task_number: str = None,
                   its_level: str = None):
        """Сохраняет задачи в итоговый результат.

        Args:
            tasks_list (dict): Список задач
            result (list): Аккумулируемый результат
            chapter_num (str): Номер главы
            answers (dict): Словарь ответов
            variant (str, optional): Вариант задачи
            task_number (str, optional): Номер задачи
            its_level (str, optional): флаг, что элемент - это объект уровеня

        Returns:
            list: Обновленный список результатов
        """
        task_condition = str()
        for key, value in tasks_list.items():
            if key == 'task_condition':
                task_condition = value
            else:
                for number, task in value.items():
                    if its_level:
                        task_number = number
                        id_tasks_book = task_number
                        answer = 'Отстутствует'
                        level = LEVLES[self.normalize_symbol(key.upper())]
                        variant_id = self.update_outline(
                            chapter_num, key, self.outline
                        )
                    else:
                        level = LEVLES[variant] if LEVLES.get(variant) else (
                            1 if variant.isalnum() else number[-1]
                        )
                        if variant.isalpha():
                            current_variant = variant.upper() + number[-1]
                        else:
                            current_variant = number[-1]
                        id_tasks_book = '' if (
                            key == 'task') else self.normalize_symbol(
                                key).lower()
                        id_tasks_book = task_number + id_tasks_book
                        variant_id = self.update_outline(
                            chapter_num, current_variant, self.outline)
                        condition = '' if key == 'task' else '_CND({})'.format(
                                self.normalize_symbol(key).lower()
                            )
                        answer_key = 'CH({})_VAR({})_TASK({}){}'.format(
                            chapter_num,
                            current_variant,
                            task_number,
                            condition)
                        answer = answers[answer_key]['answer'] if (
                            answer_key in answers) else 'Отстутствует'
                    item = {
                        'id_tasks_book': id_tasks_book,
                        'task': f'{task_condition} {task}',
                        'answer': answer,
                        'classes': CLASSES,
                        'paragraph': variant_id,
                        'topic_id': 1,
                        'level': level
                    }
                    result.append(item)

        return result

    def find_tasks(self, data, index, task_number):
        """Находит задачи в содержимом главы.

        Args:
            data (list): Содержимое главы
            index (int): Текущий индекс
            task_number (str): Номер задачи

        Returns:
            tuple: (список задач, новый индекс)
        """
        unparse_tasks = list()
        while index < len(data):
            item = data[index]
            task_number_match = TASK_NUMBER_RE.search(item)
            level_match = LEVEL_RE.search(item)
            if level_match:
                return unparse_tasks, index
            elif task_number_match and (
                    task_number_match.group(1) != task_number):
                return unparse_tasks, index
            elif task_number_match:
                index += 1
            var_match = VAR_RE.search(item)
            if var_match:
                if self.find_variant(var_match, data, index + 1):
                    return unparse_tasks, index
                else:
                    index += 1
                    continue
            elif CHAPTER_RE.search(item):
                return unparse_tasks, index
            else:
                index += 1
                unparse_tasks.append(item)
        if unparse_tasks != []:
            return unparse_tasks, index

    def recoding_variants(self, item: dict, recoded_outline: list) -> any:
        if item is not None:
            for i in item.values():
                recoded_outline.append(i)
        return recoded_outline

    def recoding_outline_to_list(self):
        recoded_outline = list()
        self.outline.pop('next_id', None)
        for item in self.outline.values():
            variants = item.pop('variants', None)
            recoded_outline.append(item)
            recoded_outline = self.recoding_variants(
                variants, recoded_outline)
        return recoded_outline


class AnswerParser(Parser):
    """Класс для парсинга ответов к задачам."""

    def __init__(self, content):
        """Инициализация парсера ответов.

        Args:
            content (list): Список строк контента документа
        """
        self.answers = self.process(content)

    def process(self, content):
        """Основной метод обработки ответов.

        Args:
            content (list): Список строк контента

        Returns:
            dict: Словарь с ответами в формате {ключ: ответ}
        """
        answers = dict()
        index = self.find_index(content, 'ответы')
        tables, index = self.get_tables(content, index)
        for table in tables:
            answers = self.parse_table(table, answers)
        return answers

    def get_tables(self, data, index):
        """Извлекает таблицы с ответами.

        Args:
            data (list): Список строк контента
            index (int): Текущий индекс

        Returns:
            tuple: (список таблиц, новый индекс)
        """
        table_list = list()
        table = list()
        current_chapter = ''
        while index < len(data):
            row: str = data[index]
            if row.endswith('|'):
                items = row.split('|')
                chapter_match = ONLY_CHAPTER_RE.search(items[1].strip())
                if chapter_match and current_chapter == '':
                    current_chapter = chapter_match.group()
                    table.append(row)
                elif chapter_match and (
                            chapter_match.group() == current_chapter):
                    table_list.append(table)
                    table = [row,]
                elif chapter_match:
                    table_list.append(table)
                    current_chapter = chapter_match.group()
                    table = [row,]
                elif items[1].strip() == '':
                    items[1] = f' {current_chapter} '
                    row = str.join('|', items)
                    table_list.append(table)
                    table = [row,]
                else:
                    if items[1].strip() == ':---':
                        index += 1
                        continue
                    table.append(row)
            elif 'литература' in row.lower():
                table_list.append(table)
                return table_list, index + 1
            else:
                index += 1
                continue
            index += 1
        return table_list, index

    def normalize_variant(self, variant: str):
        """Нормализует вариант ответа.

        Args:
            variant (str): Вариант ответа

        Returns:
            str: Нормализованный вариант
        """
        if len(variant) > 8:
            return variant.strip()[-1]
        variant = variant.replace(' ', '')
        if len(variant) < 2 and variant.isalpha():
            return variant.upper
        elif len(variant) < 2:
            return variant
        symbol = SYMBOLS[variant[0]] if variant[0] in SYMBOLS else variant[0]
        number = variant[1]
        return symbol.upper() + number

    def parse_table(self, table, answers):
        """Парсит таблицу с ответами.

        Args:
            table (list): Таблица с ответами
            answers (dict): Аккумулируемый словарь ответов

        Returns:
            dict: Обновленный словарь ответов
        """
        chapter = ''
        for var_idx, variant in enumerate(table[0].split('|')):
            variant = variant.strip()
            if variant == '':
                continue
            elif var_idx == 1 and ONLY_CHAPTER_RE.search(variant):
                chapter = self.normalize_symbol(variant[0]) + variant[1:]
                continue
            else:
                variant = self.normalize_variant(variant)
                for item in table[1:]:
                    item = item.split('|')
                    task_number = item[1].strip()
                    task = task_number if task_number.isalnum(
                        ) else task_number[0]
                    answer = item[var_idx]
                    condition = '' if task_number.isalnum(
                        ) else '_CND({})'.format(
                        self.normalize_symbol(
                                    task_number[1]).lower()
                    )
                    key = 'CH({})_VAR({})_TASK({}){}'.format(
                        chapter,
                        variant,
                        task,
                        condition
                        )
                    task_name = f'Глава {chapter}, вариант {
                        variant} задача {
                        task_number if task_number.isalnum() else f'{
                            task_number[0]}, условие {task_number[1]}'
                    }'
                    answers[key] = {'task_name': task_name, 'answer': answer}
        return answers


class OutlineParser(Parser):
    """Класс для парсинга структуры учебника (оглавления)."""

    def __init__(self, content):
        """Инициализация парсера оглавления.

        Args:
            content (list): Список строк контента документа
        """
        self.outline = self.process(content)

    def process(self, content):
        """Основной метод обработки оглавления.

        Args:
            content (list): Список строк контента

        Returns:
            dict: Словарь с структурой учебника
        """
        index = self.find_index(content, 'содержание')
        result = self.parse_outline(content, index)
        return result

    def parse_outline(self, content, index):
        """Парсит оглавление учебника.

        Args:
            content (list): Список строк контента
            index (int): Текущий индекс

        Returns:
            dict: Структурированное оглавление
        """
        result = {'next_id': 1}
        supreme_chapter = 0
        while index < len(content):
            row = content[index]
            if row.endswith('|'):
                row = row.split('|')
                items = [row[i].strip() for i in range(1,
                                                       len(row) - 1,
                                                       1)]
                chater_match = ONLY_CHAPTER_RE.search(items[0])
                if chater_match:
                    chapter_name = self.normalize_symbol(
                        chater_match.group()[0]) + chater_match.group()[1:]
                    result[chapter_name] = {
                        'id': result['next_id'],
                        'name': chater_match.string,
                        'parent': supreme_chapter,
                        'variants': {}
                    }
                    result['next_id'] += 1
                elif items[-1] == '':
                    key, value = result.popitem()
                    value['name'] = f'{value['name']} {items[0]}'
                    result[key] = value
                elif items[-1].isalnum():
                    item = {
                        'id': result['next_id'],
                        'name': items[0],
                        'parent': 0,
                    }
                    result[result['next_id']] = item
                    supreme_chapter = result['next_id']
                    result['next_id'] += 1
                elif items[0].lower() == 'работа' and (
                            items[-1].lower() == 'стр.'):
                    pass
                elif items[0] == ':---':
                    pass
                else:
                    raise ValueError('Неожиданное значение!')
            elif row == '':
                pass
            elif 'самостоятельные и контрольные работы' in row.lower():
                break
            index += 1
        return result
