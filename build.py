import os
import platform
import subprocess
import sys
from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize
import shutil
import os

def get_external_imports(py_file, existing_imports):
    """Извлекает внешние импорты из указанного .py файла."""
    with open(py_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if (line.startswith('import ') or line.startswith('from ')) and line not in existing_imports:
                # Проверяем, является ли импорт локальным
                if line.startswith('from '):
                    module_name = line.split()[1].split('.')[0]  # Имя модуля
                else:
                    module_name = line.split()[1]  # Имя модуля
                    
                if not os.path.exists(module_name + '.py'):
                    if 'wmi' in line:
                        line = f"try:\n    {line}\nexcept:\n    pass"
                    existing_imports.add(line)  # Добавляем уникальную строку импорта

def compile_to_pyd():
    # Создаем директорию compile если её нет
    if not os.path.exists('compile'):
        os.makedirs('compile')
    
    # Получаем все .py файлы в текущей директории
    py_files = [f for f in os.listdir('.') if f.endswith('.py') and f != "build.py"]
    
    # Создаем содержимое для run.py
    run_content = []
    existing_imports = set()  # Множество для хранения уникальных импортов
    
    # Компилируем каждый файл
    for py_file in py_files:
        module_name = os.path.splitext(py_file)[0]
        
        # Пропускаем текущий скрипт
        if module_name == os.path.splitext(os.path.basename(__file__))[0]:
            continue
            
        # Создаем Extension
        ext = Extension(
            name=module_name,
            sources=[py_file],
            language='c'
        )
        
        # Компилируем
        setup(
            ext_modules=cythonize([ext], language_level=3),
            script_args=['build_ext', '--inplace']
        )
        
        # Собираем внешние импорты
        get_external_imports(py_file, existing_imports)
        
        # Перемещаем файлы с расширением .pyd или .so в папку compile
        for file in os.listdir('.'):
            if file.startswith(module_name) and (file.endswith('.pyd') or file.endswith('.so')):
                shutil.move(file, os.path.join('compile', file))
    
    # Добавляем уникальные импорты в run_content
    run_content.extend(existing_imports)
    
    # Добавляем import main
    run_content.append("import main")
    
    # Добавляем код запуска main
    run_content.extend([
        "",
        "if __name__ == \"__main__\":",
        "    main.main()"
    ])
    
    # Создаем run.py
    with open(os.path.join('compile', 'run.py'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(run_content))
    
    # Очищаем временные файлы
    if os.path.exists('build'):
        shutil.rmtree('build')
    
    # Удаляем .c файлы
    for file in os.listdir('.'):
        if file.endswith('.c'):
            os.remove(file)

def compile_with_pyinstaller(arguments):
    # Определяем текущую систему
    system = platform.system()
    current_dir = os.getcwd()
    compile_dir = os.path.join(current_dir, "compile")
    
    # Проверяем существование папки compile
    if not os.path.isdir(compile_dir):
        print(f"Папка {compile_dir} не существует.")
        return
    
    # Переходим в папку compile
    os.chdir(compile_dir)
    
    # Базовая команда
    if system == "Windows":
        base_command = 'pyinstaller --onefile --add-data="*.pyd:."'
    elif system == "Linux":
        base_command = 'pyinstaller --onefile --add-data="*.so:."'
    else:
        print("Скрипт поддерживает только Windows и Linux.")
        return


    base_command += " " + arguments

    try:
        # Выполняем команду
        subprocess.run(base_command + "run.py", shell=True, check=True)
        print("Компиляция завершена успешно.")
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды: {e}")

if __name__ == "__main__":
    arguments = " ".join(sys.argv[1:])
    compile_to_pyd()
    compile_with_pyinstaller(arguments)
