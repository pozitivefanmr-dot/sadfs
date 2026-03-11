import os

# === НАСТРОЙКИ ===
OUTPUT_FILE = 'PROJECT_FULL_CODE.txt'

# Папки, которые СКРИПТ ПРОПУСТИТ (чтобы не брать мусор)
IGNORE_DIRS = {
    'venv', '.venv', 'env', '.git', '__pycache__',
    'static', 'media', 'node_modules', '.idea', '.vscode',
    'migrations', 'assets', 'build', 'dist'
}

# Расширения файлов, которые НУЖНО КОПИРОВАТЬ
INCLUDE_EXTS = {
    '.py', '.html', '.css', '.js', '.json', '.txt', '.md'
}

# Файлы, которые нужно исключить по имени
IGNORE_FILES = {
    'db.sqlite3', 'get_all_code.py', OUTPUT_FILE,
    'package-lock.json', 'poetry.lock', '.DS_Store'
}


def is_text_file(filename):
    return any(filename.endswith(ext) for ext in INCLUDE_EXTS)


def write_tree(out, startpath):
    out.write("=== СТРУКТУРА ПРОЕКТА ===\n")
    for root, dirs, files in os.walk(startpath):
        # Фильтрация папок на лету
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * level
        out.write(f'{indent}{os.path.basename(root)}/\n')
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if is_text_file(f) and f not in IGNORE_FILES:
                out.write(f'{subindent}{f}\n')
    out.write("\n" + "=" * 50 + "\n\n")


def dump_files():
    total_files = 0
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        # 1. Сначала пишем дерево каталогов
        write_tree(outfile, '.')

        outfile.write("=== СОДЕРЖИМОЕ ФАЙЛОВ ===\n\n")

        # 2. Потом идем по файлам
        for root, dirs, files in os.walk('.'):
            # Исключаем ненужные папки
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                if file in IGNORE_FILES or not is_text_file(file):
                    continue

                file_path = os.path.join(root, file)

                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read()

                    # Красивый разделитель, чтобы я понимал где начало файла
                    outfile.write(f"START_FILE: {file_path}\n")
                    outfile.write("-" * 50 + "\n")
                    outfile.write(content + "\n")
                    outfile.write("-" * 50 + "\n")
                    outfile.write(f"END_FILE: {file_path}\n\n")

                    print(f"Добавлен: {file_path}")
                    total_files += 1
                except Exception as e:
                    print(f"Ошибка чтения {file_path}: {e}")

    print(f"\n✅ Готово! Собрано файлов: {total_files}")
    print(f"📁 Отправь мне файл: {OUTPUT_FILE}")


if __name__ == '__main__':
    dump_files()