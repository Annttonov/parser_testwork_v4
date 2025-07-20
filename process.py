'''Модуль для сохранения данных в EXCEL файл.'''
import os

import pandas

from parser import TaskParcer

if __name__ == '__main__':
    file_path = os.path.abspath(input(
        'Введите путь к MD-файлу относительно текущего каталога:\n'))
    if not os.path.exists(file_path):
        exit('неверный путь к файлу')

    excel_path = input(
        'Введите название для excel файла без расширения:\n') + '.xlsx'

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().split('\n')

    doc = TaskParcer(content)
    tasks_data = doc.tasks
    chapters_data = [item for item in doc.outline.values()]
    authors_data = doc.description

    tasks_columns_order = [
        'id_tasks_book', 'task', 'answer', 'classes',
        'paragraph', 'topic_id', 'level'
    ]
    author_columns_order = ['name', 'author', 'description',
                            'topic_id', 'classes']

    chapters_columns_order = ['id', 'book_id', 'name', 'parent']

    tasks_df = pandas.DataFrame(tasks_data, columns=tasks_columns_order)
    tasks_df.sort_values('paragraph')
    authors_df = pandas.DataFrame(authors_data, columns=author_columns_order)
    chapters_df = pandas.DataFrame(
        chapters_data, columns=chapters_columns_order)
    chapters_df.sort_values('id')
    with pandas.ExcelWriter(excel_path, engine='openpyxl') as writer:
        tasks_df.to_excel(writer, sheet_name='tasks', index=False)
        authors_df.to_excel(writer, sheet_name='author', index=False)
        chapters_df.to_excel(
            writer, sheet_name='table_of_contents', index=False)
