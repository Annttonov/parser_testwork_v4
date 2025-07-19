import pandas

from process import TaskParcer

if __name__ == '__main__':
    path = 'input.md'  # input('Укажите путь к файлу:\n')
    excel_path = 'output.xlsx'  # input('Введите название для excel файла в формате ".xlsx":\n')

    with open(path, 'r', encoding='utf-8') as f:
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
