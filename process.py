import re

from patterns import (
    ONLY_CHAPTER_RE,
    CHAPTER_RE,
    VAR_RE,
    LEVEL_RE,
    TASK_RE,
    TASK_NUMBER_RE,
    SYMBOLS,
    CLASSES
)

input_path = 'input.md'

LINE_STARTED_SYMBOLS = ("#", "$$", ">", "|")


class Parser:

    def find_index(self, content, name):
        index = 0
        while index < len(content):
            item: str = content[index]
            if item.lower().endswith(name):
                return index + 1
            index += 1
        raise ValueError('Требуемое значение не найдено!')

    def normalize_symbol(self, symbol):
        return SYMBOLS[symbol] if symbol in SYMBOLS else symbol


class TaskParcer(Parser):

    def __init__(self, content, answers, outline):
        self.outline = outline
        self.answers = answers
        self.description = self.get_description(content)
        self.tasks, self.index = self.process(content)

    def process(self, content):
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
        return result, index

    def get_description(self, content):
        item, index = self.get_item(content, 0)
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
                return description

    def get_normal_string(self, string, index, text):
        while True:
            item = text[index]
            if item == '$$':
                string += item
                break
            string += item
            index += 1
        return string, index

    def parse_tables_with_variant(self, string):
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
        if new_var != {}:
            if new_var.get('num') == 0:
                var['text'] = f'{var['text']} {new_var['text']}'
            elif var.get('num') != new_var.get('num'):
                var_list.append(var)
                var = new_var
        return var, var_list

    def get_item(self, content, index):
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
        if match:
            task_number_match = TASK_NUMBER_RE.search(data[next_index])
            if task_number_match:
                return match

    def parse_chapter(self, data, chapter_num, result):
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
        symbol = SYMBOLS[symbol] if symbol in SYMBOLS else symbol
        return symbol if symbol.isalnum() else symbol.upper()

    def parse_variant(self, data, index, chapter_num, result):
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
                    level=True)
                return result, index
        result = self.save_tasks(
            tasks_list,
            result,
            chapter_num,
            answers=self.answers,
            level=True)
        return result, index

    def parse_level_tasks(self, unparse_tasks, level, tasks):
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
        item = re.sub(r'\[\^\d\]', '', item, 1)
        item = re.sub(r'^a+?\)\s', 'а) ', item, 1)
        return item

    def parse_tasks(self, unparse_tasks):
        tasks = {
            'task_condition': unparse_tasks[0],
        }
        index_v1 = 1
        index_v2 = 2
        current_task_symbol = ''
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
                        'v2': item_v1[v1_match.end():]
                    }
                    index_v1, index_v2 = index_v1 + 1, index_v2 + 1
                    continue
            elif v1_match or v2_match:
                if v1_match:
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

        return tasks

    def write_item(self, data, item, key):
        if data.get(key):
            data[key] = f'{data[key]} {item}'
        else:
            data[key] = item
        return data

    def save_tasks(self, tasks_list: dict,
                   result: list,
                   chapter_num: str,
                   answers: dict,
                   variant: str = None,
                   task_number: str = None,
                   level: str = None):
        if chapter_num == 'С-64*':
            pass
        for key, value in tasks_list.items():
            if key == 'task_condition':
                text = f'Условие для задачи {
                    task_number if task_number else chapter_num}'
                item = {
                        'id_tasks_book': text,
                        'task': value,
                        'answer': 'Отсутствует',
                        'classes': CLASSES,
                        'paragraph': self.outline[chapter_num]['id'],
                        'topic_id': 1,
                        'level': 1
                    }
                result.append(item)
            else:
                for number, task in value.items():
                    if level:
                        task_number = number
                        text = f'Уровень {key}, задача {task_number}'
                        answer = 'Отстутствует'
                    else:
                        if variant.isalpha():
                            current_variant = variant + number[-1]
                        else:
                            current_variant = number[-1]
                        text = f'Вариант {
                            current_variant}, задача {task_number},{
                            '' if key == 'task' else f' условие {key}'}'
                        answer_key = f'CH({chapter_num})_VAR({
                            current_variant})_TSK{
                            f'({task_number})' if key == 'task' else f'({
                                task_number})_CND({
                                    self.normalize_symbol(key).lower(
                                    )})'}'
                        answer = answers[answer_key]['answer'] if (
                            answer_key in answers) else 'Отстутствует'
                    item = {
                        'id_tasks_book': text,
                        'task': task,
                        'answer': answer,
                        'classes': CLASSES,
                        'paragraph': self.outline[chapter_num]['id'],
                        'topic_id': 1,
                        'level': 1
                    }
                    result.append(item)

        return result

    def find_tasks(self, data, index, task_number):
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


class AnswerParser(Parser):
    def __init__(self, content):

        self.answers = self.process(content)

    def get_tables(self, data, index):
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
        if len(variant) > 8:
            return variant.strip()[-1]
        variant = variant.replace(' ', '')
        if len(variant) < 2:
            return variant
        symbol = SYMBOLS[variant[0]] if variant[0] in SYMBOLS else variant[0]
        number = variant[1]
        return symbol.upper() + number

    def parse_table(self, table, answers):
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
                    answer = item[var_idx]
                    key = f'CH({chapter})_VAR({variant})_TSK{
                        f'({task_number})' if task_number.isalnum() else f'({
                            task_number[0]})_CND({
                                self.normalize_symbol(
                                    task_number[1]).lower()})'
                    }'
                    task_name = f'Глава {chapter}, вариант {
                        variant} задача {
                        task_number if task_number.isalnum() else f'{
                            task_number[0]}, условие {task_number[1]}'
                    }'
                    answers[key] = {'task_name': task_name, 'answer': answer}
        return answers

    def process(self, content):
        answers = dict()
        index = self.find_index(content, 'ответы')
        tables, index = self.get_tables(content, index)
        for table in tables:
            answers = self.parse_table(table, answers)
        return answers


class OutlineParser(Parser):

    def __init__(self, content):
        self.outline = self.process(content)

    def process(self, content):
        index = self.find_index(content, 'содержание')
        result = self.parse_outline(content, index)
        return result

    def parse_outline(self, content, index):
        id = 1
        result = dict()
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
                    name = chater_match.string[chater_match.end(
                            ):].strip()
                    name = name.replace('.', '', 1).strip() if name.startswith(
                        '.') else name
                    result[chapter_name] = {
                        'id': id,
                        'book_id': chapter_name,
                        'name': name,
                        'parent': supreme_chapter,
                    }
                    id += 1
                elif items[-1] == '':
                    key, value = result.popitem()
                    value['name'] = f'{value['name']} {items[0]}'
                    result[key] = value
                elif items[-1].isalnum():
                    item = {
                        'id': id,
                        'book_id': items[0],
                        'name': items[0],
                        'parent': 0,
                    }
                    result[id] = item
                    supreme_chapter = id
                    id += 1
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


if __name__ == '__main__':
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read().split('\n')
    outline = OutlineParser(content).outline
    answers = AnswerParser(content).answers
    parser_tasks = TaskParcer(content, answers, outline)
    tasks_data, index = parser_tasks.tasks, parser_tasks.index
