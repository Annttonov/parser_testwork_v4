from mrkdwn_analysis import MarkdownAnalyzer

import re

from patterns import (
    CHAPTER_RE,
    VAR_RE,
    LEVEL_RE,
    TASK_RE,
    TASK_NUMBER_RE
)

input_path = 'input.md'

LINE_STARTED_SYMBOLS = ("#", "$$", ">", "|")


def get_normal_string(string, index, text):
    while True:
        item = text[index]
        if item == '$$':
            string += item
            break
        string += item
        index += 1
    return string, index


def parse_tables_with_variant(string):
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
                    'text': item[var_match.end():]
                }
            elif var_1 == {}:
                var_1 = {
                    'num': var_match.group(1),
                    'text': item[var_match.end():]
                }
            else:
                print(f'{var_1.keys()}\n{var_2.keys()}')
                var_1 = {
                    'num': var_match.group(1),
                    'text': item[var_match.end():]
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


def get_normalise_variant(var, new_var, var_list):
    if new_var != {}:
        if new_var.get('num') == 0:
            var['text'] = f'{var['text']} {new_var['text']}'
        elif var.get('num') != new_var.get('num'):
            var_list.append(var)
            var = new_var
    return var, var_list


def get_item(content, index):
    item = content[index]
    if item == '' or item == '\n':
        item, index = get_item(content, index + 1)
        return item, index
    if item == '$$':    # формирует LaTeX-выражение
        item, index = get_normal_string(
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
        var_1, var_2 = parse_tables_with_variant(item)
        index += 1
        next_item = content[index]
        while next_item.endswith('|') and len(
                next_item.split('|')) == len(item.split('|')):
            var_1_new, var_2_new = parse_tables_with_variant(next_item)
            var_list = []
            var_1, var_list = get_normalise_variant(var_1, var_1_new,
                                                    var_list)
            var_2, var_list = get_normalise_variant(var_2, var_2_new,
                                                    var_list)
            index += 1
            next_item = content[index]
            if var_list != []:
                table.append(var_list)
            var_list = []
        table.append([var_1, var_2])
        item = table
    index += 1
    return item, index


def find_chapter_index(content: list, data: list, start_index: int):
    index = start_index
    chapter_data = list()
    while index < len(content):
        item, index = get_item(content, index)
        if isinstance(item, list):
            item = 'ТАБЛИЦА\n-----------------------------------\n'
        elif item.lower() == 'ответы':
            return index - 1, data, chapter_data
        chapter_match = CHAPTER_RE.search(item)
        if chapter_match:
            return index - 1, data, chapter_data
        chapter_data.append(item)
        data.append(item)
    return index - 1, data, chapter_data


def find_variant(match, data, next_index):
    if match:
        task_number_match = TASK_NUMBER_RE.search(data[next_index])
        if task_number_match:
            return True


def parse_chapter(data):
    if data == []:
        return
    index = 0
    while index < len(data):
        item = data[index]
        if find_variant(VAR_RE.search(item), data, index + 1):
            index = parse_variant(data, index + 1)
        elif LEVEL_RE.search(item):
            index = parse_level(data, index)
        else:
            index += 1
        if CHAPTER_RE.search(item):
            return
    return


def parse_variant(data, index):
    while index < len(data):
        item = data[index]
        task_number_match = TASK_NUMBER_RE.search(item)
        if task_number_match:
            index += 1
            unparse_tasks, index = find_tasks(
                data, index, task_number_match.group(1))
            tasks_list = parse_tasks(unparse_tasks)
            save_tasks(tasks_list)
            continue
        if find_variant(VAR_RE.search(item), data, index + 1) or (
                LEVEL_RE.search(item)):
            return index
        if CHAPTER_RE.search(item):
            return index
    return index


def parse_level(data, index):
    current_level = ''
    tasks_list = {'task_condition': data[0]}
    while index < len(data):
        item = data[index]
        level_match = LEVEL_RE.search(item)
        if level_match:
            current_level = level_match.group(1)
            index += 1
            unparse_tasks, index = find_tasks(
                data, index, current_level)
            tasks_list = parse_level_tasks(
                unparse_tasks, current_level, tasks_list)
            continue
        if CHAPTER_RE.search(item):
            save_tasks(tasks_list)
            return index
    save_tasks(tasks_list)
    return index


def parse_level_tasks(unparse_tasks, level, tasks):
    index = 0
    if not tasks.get(level):
        tasks[level] = {}
    while index < len(unparse_tasks):
        item = unparse_tasks[index]
        match = TASK_RE.search(item)
        if match:
            tasks[level] = write_item(
                tasks[level],
                item[match.end():],
                match.group(1)
            )

        else:
            raise IndentationError('Неожиданная строка!')
        index += 1
    return tasks


def parse_tasks(unparse_tasks):
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
        item_v1 = re.sub(r'\[\^\d\]', '', unparse_tasks[index_v1], 1)
        item_v1 = re.sub(r'^a+?\)\s', 'а) ', item_v1, 1)
        item_v2 = re.sub(r'\[\^\d\]', '', unparse_tasks[index_v2], 1)
        item_v2 = re.sub(r'^a+?\)\s', 'а) ', item_v2, 1)
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
                tasks[current_task_symbol] = write_item(
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
            else:
                tasks[current_task_symbol] = {
                    'v1': item_v1
                }
            index_v1, index_v2 = index_v1 + 1, index_v2 + 1
            continue
        elif (not v1_match and not v2_match) and current_task_symbol != '':
            tasks[current_task_symbol] = write_item(
                tasks[current_task_symbol],
                item_v1,
                'v1')
            tasks[current_task_symbol] = write_item(
                tasks[current_task_symbol],
                item_v2,
                'v2')
        else:
            if not tasks.get('task'):
                tasks['task'] = {}
            tasks['task'] = write_item(tasks['task'], item_v1, 'v1')
            tasks['task'] = write_item(tasks['task'], item_v2, 'v2')
        index_v1, index_v2 = index_v1 + 2, index_v2 + 2

    if index_v1 >= len(unparse_tasks):
        return tasks
    elif index_v1 < len(unparse_tasks):
        task_match = TASK_RE.search(unparse_tasks[index_v1])
        if current_task_symbol != '' and task_match:
            tasks[current_task_symbol] = write_item(
                tasks[current_task_symbol],
                unparse_tasks[index_v1][task_match.end():],
                'v1')
        elif task_match:
            if not tasks.get(task_match.group(1)):
                tasks[task_match.group(1)] = {}
            tasks[task_match.group(1)] = write_item(
                tasks[task_match.group(1)],
                unparse_tasks[index_v1][task_match.end():],
                'v1')
        else:
            if not tasks.get('task'):
                tasks['task'] = {}
            tasks['task'] = write_item(tasks['task'],
                                       unparse_tasks[index_v1],
                                       'v1')

    return tasks


def write_item(data, item, key):
    if data.get(key):
        data[key] = f'{data[key]} {item}'
    else:
        data[key] = item
    return data


def save_tasks(tasks_list: dict):
    for item in tasks_list.items():

        print(item)


def find_tasks(data, index, task_number):
    unparse_tasks = list()
    while index < len(data):
        item = data[index]
        task_number_match = TASK_NUMBER_RE.search(item)
        level_match = LEVEL_RE.search(item)
        if level_match:
            return unparse_tasks, index
        elif task_number_match and task_number_match.group(1) != task_number:
            return unparse_tasks, index
        elif task_number_match:
            index += 1
        var_match = VAR_RE.search(item)
        if var_match:
            if find_variant(var_match, data, index + 1):
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


def process(file_path):
    doc = MarkdownAnalyzer(file_path)
    content = doc.text.split("\n")
    index = 0
    data = []
    while index < len(content[:]):
        item, index = get_item(content, index)
        if isinstance(item, list):
            item = 'ТАБЛИЦА\n-----------------------------------\n'
        elif item.lower() == 'ответы':
            break
        chapter_match = CHAPTER_RE.search(item)
        if chapter_match:
            index, data, chapter_data = find_chapter_index(
                content,
                data,
                start_index=index)
            parse_chapter(chapter_data)
        else:
            index += 1

        data.append(item)

    return data


if __name__ == '__main__':
    result = process(input_path)
    # for item in result[:200]:
    #     print(item)
    print(
        '‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\n',
        "ДАЛЬШЕ ИДУТ ТАБЛИЦЫ, ОТВЕТЫ, СОДЕРЖАНИЕ\n",
        '___________________________________________')
