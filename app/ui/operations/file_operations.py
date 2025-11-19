"""
Операции с файлами для главного окна приложения.

Этот модуль содержит всю логику работы с файлами:
загрузка, сохранение, удаление, генерация тестовых данных.
"""

import os
import shutil
from PySide6.QtWidgets import QFileDialog, QListWidgetItem, QMenu
from typing import Tuple, Optional
from app.utils.generate_utils import getTestData
from app.utils.load_utils import load_dataframe_by_path
from app.core.processing import delete_processed_sequence
from app.core.data_registry import DataRegistry


class FileOperationsManager:
    """Менеджер для операций с файлами."""

    def __init__(self, parent_window):
        """
        Инициализация менеджера файловых операций.

        Args:
            parent_window: Родительское окно (экземпляр MyMenu)
        """
        self.parent = parent_window
        self.test_counter = 1

    def load_processed_files(self):
        """Автоматически загружает последовательности из папки processed_sequences.

        Каждая папка представляет одну последовательность с исходным и clean файлами.
        В список добавляется только основной файл, но регистрируются оба.
        """
        processed_dir = "processed_sequences"

        if not os.path.exists(processed_dir):
            return

        # Сканируем все подпапки в processed_sequences
        for folder_name in os.listdir(processed_dir):
            folder_path = os.path.join(processed_dir, folder_name)

            if not os.path.isdir(folder_path):
                continue

            # Найдём основной и clean файлы в папке
            main_file = None
            clean_file = None

            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)

                if file_name.lower().endswith((".csv", ".srd")):
                    if "_clean" in file_name.lower():
                        clean_file = (file_name, file_path)
                    else:
                        main_file = (file_name, file_path)

            # Регистрируем оба файла, но в список добавляем только основной
            if main_file:
                main_name, main_path = main_file

                # Проверяем, что последовательность ещё не добавлена
                if not self.parent.registry.has_file(main_name):
                    # Регистрируем основной файл
                    self.parent.registry.set_file(main_name, main_path)

                    # Регистрируем clean файл, если он есть
                    if clean_file:
                        clean_name, clean_path = clean_file
                        self.parent.registry.set_file(clean_name, clean_path)

                    # В список добавляем только основной файл
                    self.parent.list_widget.addItem(main_name)

        # После загрузки всех файлов запускаем предварительную загрузку
        # для улучшения производительности при первом клике
        if hasattr(self.parent, "plot_manager"):
            file_paths = []
            for i in range(self.parent.list_widget.count()):
                item = self.parent.list_widget.item(i)
                if item:
                    file_path = self.parent.registry.get_path(item.text())
                    file_paths.append(file_path)

            # Предварительная загрузка первых нескольких файлов
            self.parent.plot_manager.preload_data_async(file_paths)

    def open_file_dialog(self):
        """Показывает диалог выбора, создаёт папку и копирует файлы в processed_sequences."""
        files, _ = QFileDialog.getOpenFileNames(
            self.parent,
            "Выберете файлы",
            "",
            "Data files (*.csv *.srd);;CSV (*.csv);;SRD (*.srd);;All files (*)",
        )

        # Создаём базовую папку processed_sequences если её нет
        processed_dir = "processed_sequences"
        if not os.path.exists(processed_dir):
            os.makedirs(processed_dir)

        names = [os.path.basename(path) for path in files]
        for name, path in zip(names, files):
            # Создаём папку для последовательности
            base_name = os.path.splitext(name)[0]
            folder = os.path.join(processed_dir, f"{base_name}_seq")
            if not os.path.exists(folder):
                os.makedirs(folder)

            # Копируем файл в папку
            dest_path = os.path.join(folder, name)
            shutil.copy(path, dest_path)

            # Регистрируем новый путь к файлу
            self.parent.registry.set_file(name, dest_path)
            self.parent.list_widget.addItem(name)

    def generate_test_data(self):
        """Запрашивает параметры и генерирует тестовые данные, добавляя их в список."""
        from app.ui.dialogs.dialogs import ask_test_data_params

        params = ask_test_data_params(self.parent)
        if params is None:
            return
        n, peak_space, detail, noise_level = params

        # Используем разумные значения по умолчанию для ширины и высоты
        peak_width = 1.3
        peak_height = 1000

        data, M = getTestData(
            n, peak_space, peak_width, peak_height, detail, noise_level
        )

        # Формируем имя и сохраняем как реальный CSV в processed_sequences
        name = f"TestData_{self.test_counter}.csv"

        # Создаём базовую папку processed_sequences если её нет
        processed_dir = "processed_sequences"
        if not os.path.exists(processed_dir):
            os.makedirs(processed_dir)

        # Создаём папку для этой последовательности
        folder = os.path.join(processed_dir, f"TestData_{self.test_counter}_seq")
        if not os.path.exists(folder):
            os.makedirs(folder)

        csv_path = os.path.join(folder, name)
        data.to_csv(csv_path, sep=";", index=False, header=False)

        # Регистрируем файл и кэшируем DataFrame
        self.parent.registry.set_file(name, csv_path)
        self.parent.registry.set_df(name, data)

        # Добавляем в список и показываем
        self.parent.list_widget.addItem(name)
        self.test_counter += 1

        # Рисуем Raw и переключаемся на него
        self.parent.plot_data(self.parent.raw_plot_widget, data)
        self.parent.view_tabs.setCurrentWidget(self.parent.raw_plot_widget)

    def delete_file(self, item: QListWidgetItem):
        """Удаляет файл из списка и соответствующую папку из processed_sequences."""
        name = item.text()

        # Получаем базовое имя файла для очистки связанных данных
        base_name = os.path.splitext(name)[0]

        # Получаем путь к исходному файлу
        if self.parent.registry.has_file(name):
            file_path = self.parent.registry.get_path(name)

            # Удаляем обработанные файлы из processed_sequences
            deleted = delete_processed_sequence(file_path)
            print(
                f"Удаление папки для {name}: {'успешно' if deleted else 'не удалось'}"
            )

        # Удаляем данные итераций для этого файла и, если нужно, вкладку iterations
        self.parent.plot_manager.clear_iteration_data(base_name)

        # Очищаем кэши для данного файла и связанных clean файлов
        self.parent.plot_manager.clear_cache_for_file(name)

        # Также очищаем кэши для потенциальных clean файлов
        clean_candidates = [f"{base_name}_clean.csv", f"{base_name}_clean.srd"]
        for clean_name in clean_candidates:
            self.parent.plot_manager.clear_cache_for_file(clean_name)

        # Удаляем clean вкладку, если текущий файл связан с ней
        if (
            hasattr(self.parent.plot_manager, "current_clean_file_base")
            and self.parent.plot_manager.current_clean_file_base == base_name
        ):
            self.parent.plot_manager.remove_clean_tab()

        # Удаляем из списка и реестра
        self.parent.list_widget.takeItem(self.parent.list_widget.row(item))
        self.parent.registry.remove(name)

        # Также удаляем связанный clean файл из реестра, если он есть
        clean_candidates = [f"{base_name}_clean.csv", f"{base_name}_clean.srd"]
        for clean_name in clean_candidates:
            if self.parent.registry.has_file(clean_name):
                self.parent.registry.remove(clean_name)

    def delete_selected_files(self):
        """Удаляет все выбранные файлы из списка."""
        selected_items = self.parent.list_widget.selectedItems()
        
        if not selected_items:
            return
        
        # Копируем список, так как будем удалять элементы в процессе
        items_to_delete = list(selected_items)
        
        for item in items_to_delete:
            self.delete_file(item)

    def show_context_menu(self, pos):
        """Контекстное меню по ПКМ: содержит пункты для работы с файлами."""
        item = self.parent.list_widget.itemAt(pos)
        if not item:
            return

        menu = QMenu(self.parent)
        selected_items = self.parent.list_widget.selectedItems()
        
        # Если выбрано несколько файлов
        if len(selected_items) > 1:
            # Пакетные операции
            menu.addAction("Обработать выбранные").triggered.connect(
                lambda: self.parent.process_selected_files()
            )
            menu.addSeparator()
            menu.addAction("Удалить выбранные").triggered.connect(
                lambda: self.delete_selected_files()
            )
        else:
            # Операции с одним файлом
            file_name = item.text()

            # Основные действия
            action = menu.addAction("Запуск")
            action.triggered.connect(lambda: self.parent.file_process(file_name))

            # Проверяем, есть ли clean данные для этого файла
            base_name = self._get_base_name(file_name)
            has_clean_data = self._check_has_clean_data(base_name)

            if has_clean_data:
                menu.addSeparator()
                clean_action = menu.addAction("Удалить обработанные данные")
                clean_action.triggered.connect(lambda: self._remove_clean_data(base_name))

            menu.addSeparator()
            action2 = menu.addAction("Удалить файл")
            action2.triggered.connect(lambda: self.parent.delete_file(item))

        menu.exec(self.parent.list_widget.mapToGlobal(pos))

    def _get_base_name(self, file_name: str) -> str:
        """Получает базовое имя файла (без _clean и расширения)."""
        # Убираем _clean если есть
        if "_clean" in file_name:
            base_no_ext = file_name.split("_clean")[0]
        else:
            # Убираем расширение
            parts = file_name.split(".")
            base_no_ext = parts[0]
        return base_no_ext

    def _check_has_clean_data(self, base_name: str) -> bool:
        """Проверяет, есть ли clean данные для указанного базового имени."""
        clean_candidates = [f"{base_name}_clean.csv", f"{base_name}_clean.srd"]

        for candidate in clean_candidates:
            if self.parent.registry.has_file(candidate):
                return True
        return False

    def _remove_clean_data(self, base_name: str):
        """Удаляет clean данные для указанного файла."""
        print(f"Начинаем удаление clean данных для: {base_name}")
        removed_files = self.parent.plot_manager.remove_clean_data_for_file(base_name)
        if removed_files:
            print(f"Удалены обработанные данные из реестра: {', '.join(removed_files)}")
            # Обновляем статус
            self.parent.status_label.setText(
                f"Удалены обработанные данные для {base_name}"
            )
        else:
            print(f"Не найдено clean данных для удаления: {base_name}")
            self.parent.status_label.setText(
                f"Не найдено обработанных данных для {base_name}"
            )

    def refresh_file_list(self):
        """Обновляет список файлов в интерфейсе."""
        # Сохраняем текущие файлы из реестра (кроме clean файлов)
        current_files = []
        for file_name in self.parent.registry._name_to_path.keys():
            # Не добавляем clean файлы в список, они показываются автоматически
            if "_clean" not in file_name:
                current_files.append(file_name)

        # Очищаем текущий список
        self.parent.list_widget.clear()

        # Перезагружаем файлы из processed_sequences
        self.load_processed_files()

        # Добавляем файлы, которые были загружены через диалог/генерацию
        for file_name in current_files:
            # Проверяем, что файл еще не добавлен (избегаем дублирования)
            items = [
                self.parent.list_widget.item(i).text()
                for i in range(self.parent.list_widget.count())
            ]
            if file_name not in items:
                self.parent.list_widget.addItem(file_name)
