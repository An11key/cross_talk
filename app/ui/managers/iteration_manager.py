"""
Модуль управления данными итераций алгоритмов.

Содержит класс IterationManager для хранения, загрузки и управления
данными итераций обработки последовательностей.
"""

from typing import Dict, Optional


class IterationManager:
    """Менеджер для управления данными итераций."""

    def __init__(self, parent_window):
        """
        Инициализация менеджера итераций.

        Args:
            parent_window: Родительское окно (экземпляр MyMenu)
        """
        self.parent = parent_window

        # Данные итераций для вкладки результатов по файлам
        # {file_name: {iteration_num: iteration_data}}
        self.iteration_results_data: Dict[str, Dict[int, Dict]] = {}
        self.current_iterations_file = None  # Текущий файл для вкладки итераций
        # Файлы, для которых пользователь намеренно удалил данные итераций
        self.manually_cleared_iteration_files = set()

    def store_iteration_data(
        self, file_name: str, iteration_num: int, iteration_data: Dict
    ) -> None:
        """
        Сохраняет данные итерации для отображения.

        Args:
            file_name: Имя файла, для которого сохраняются данные
            iteration_num: Номер итерации
            iteration_data: Данные итерации в формате {(i,j): (x_data, y_data)}
        """
        if file_name not in self.iteration_results_data:
            self.iteration_results_data[file_name] = {}

        self.iteration_results_data[file_name][iteration_num] = iteration_data

        # Если вкладка создана и отображает данные для этого файла, обновляем
        if (
            self.parent.iterations_widget is not None
            and self.current_iterations_file == file_name
        ):
            self.parent.iterations_widget.set_iteration_data(
                self.iteration_results_data[file_name]
            )

        # Обновляем вкладку сходимости, если она создана
        if self.parent.convergence_widget is not None:
            self.parent.convergence_widget.set_convergence_data(
                self.iteration_results_data[file_name]
            )

    def finalize_iteration_results(self, file_name: str) -> None:
        """
        Завершает сбор данных итераций и обеспечивает вкладку.

        Args:
            file_name: Имя файла, для которого завершается сбор данных
        """
        if (
            file_name in self.iteration_results_data
            and self.iteration_results_data[file_name]
        ):
            # Удаляем файл из списка намеренно очищенных (новая обработка)
            self.manually_cleared_iteration_files.discard(file_name)

            # Сохраняем данные итераций на диск
            self._save_iteration_results_to_disk(file_name)

            # Обеспечиваем вкладки через менеджер вкладок
            from app.ui.managers.tab_manager import TabManager
            tab_manager = getattr(self.parent.plot_manager, 'tab_manager', None)
            if tab_manager:
                tab_manager.ensure_iterations_tab()
                tab_manager.ensure_convergence_tab()
            
            self.current_iterations_file = file_name
            if self.parent.iterations_widget is not None:
                self.parent.iterations_widget.set_iteration_data(
                    self.iteration_results_data[file_name]
                )
            if self.parent.convergence_widget is not None:
                self.parent.convergence_widget.set_convergence_data(
                    self.iteration_results_data[file_name]
                )

    def clear_iteration_data(self, file_name: str = None) -> None:
        """
        Очищает данные итераций.

        Args:
            file_name: Имя файла для очистки. Если None, очищает все данные.
        """
        if file_name is None:
            self.iteration_results_data.clear()
            self.current_iterations_file = None
            self.manually_cleared_iteration_files.clear()
        else:
            # Ищем все ключи, которые соответствуют данному файлу
            # (может быть как полное имя, так и базовое имя)
            keys_to_remove = []
            base_name = self._get_base_name_from_file(file_name)

            for key in self.iteration_results_data.keys():
                key_base = self._get_base_name_from_file(key)
                if key == file_name or key_base == base_name or key_base == file_name:
                    keys_to_remove.append(key)

            # Удаляем все найденные ключи
            for key in keys_to_remove:
                self.iteration_results_data.pop(key, None)
                self.manually_cleared_iteration_files.add(key)
                if self.current_iterations_file == key:
                    self.current_iterations_file = None
                print(f"Удалены данные итераций для ключа: {key}")

            # Также добавляем исходное имя файла в список очищенных
            self.manually_cleared_iteration_files.add(file_name)
            if self.current_iterations_file == file_name:
                self.current_iterations_file = None

            print(f"Очистка данных итераций для файла: {file_name}")
            print(f"Найдено ключей для удаления: {keys_to_remove}")
            print(
                f"Оставшиеся данные итераций: {list(self.iteration_results_data.keys())}"
            )

        # Удаляем вкладки iterations и convergence, если больше нет данных итераций
        print(
            f"Проверка удаления вкладок. Данных итераций: {len(self.iteration_results_data)}"
        )

        # Получаем tab_manager
        from app.ui.tab_manager import TabManager
        tab_manager = getattr(self.parent.plot_manager, 'tab_manager', None)

        if file_name is None or not self.iteration_results_data:
            # Если очищаем все данные или данных больше нет - удаляем вкладки
            print("Удаляем все вкладки итераций и сходимости")
            if self.parent.iterations_widget is not None:
                self.parent.iterations_widget.clear_data()
                if tab_manager:
                    tab_manager.remove_iterations_tab()
            if self.parent.convergence_widget is not None:
                self.parent.convergence_widget.clear_data()
                if tab_manager:
                    tab_manager.remove_convergence_tab()
        elif self.current_iterations_file is None and self.iteration_results_data:
            # Если текущий файл был удален, но есть другие файлы с данными итераций,
            # переключаемся на первый доступный файл
            first_available_file = next(iter(self.iteration_results_data.keys()))
            self.current_iterations_file = first_available_file
            print(f"Переключаемся на файл: {first_available_file}")

            if self.parent.iterations_widget is not None:
                self.parent.iterations_widget.set_iteration_data(
                    self.iteration_results_data[first_available_file]
                )
            if self.parent.convergence_widget is not None:
                self.parent.convergence_widget.set_convergence_data(
                    self.iteration_results_data[first_available_file]
                )

    def has_iteration_data_for_file(self, file_name: str) -> bool:
        """
        Проверяет наличие данных итераций для указанного файла без создания/удаления вкладки.

        Args:
            file_name: Имя файла

        Returns:
            True если данные найдены, False иначе
        """
        # Получаем базовое имя файла без расширения для поиска
        base_name = self._get_base_name_from_file(file_name)

        # Ищем данные итераций для этого файла или его базового имени в памяти
        for key in self.iteration_results_data:
            if key == file_name or self._get_base_name_from_file(key) == base_name:
                return True

        # Если данных нет в памяти, проверяем наличие файла итераций на диске
        return self._check_iteration_file_exists(file_name)

    def show_iterations_for_file(self, file_name: str) -> bool:
        """
        Показывает данные итераций для указанного файла.

        Args:
            file_name: Имя файла

        Returns:
            True если данные найдены и показаны, False иначе
        """
        # Получаем базовое имя файла без расширения для поиска
        base_name = self._get_base_name_from_file(file_name)

        # Ищем данные итераций для этого файла или его базового имени
        iteration_data = None
        found_key = None

        for key in self.iteration_results_data:
            if key == file_name or self._get_base_name_from_file(key) == base_name:
                iteration_data = self.iteration_results_data[key]
                found_key = key
                break

        # Если данных нет в памяти, пытаемся загрузить с диска
        if not iteration_data:
            if self._load_iteration_results_from_disk(file_name):
                iteration_data = self.iteration_results_data.get(file_name)
                found_key = file_name
            elif self._load_iteration_results_from_disk(base_name):
                iteration_data = self.iteration_results_data.get(base_name)
                found_key = base_name

        if iteration_data:
            # Получаем tab_manager
            from app.ui.managers.tab_manager import TabManager
            tab_manager = getattr(self.parent.plot_manager, 'tab_manager', None)
            if tab_manager:
                tab_manager.ensure_iterations_tab()
                tab_manager.ensure_convergence_tab()
            
            self.current_iterations_file = found_key
            if self.parent.iterations_widget is not None:
                self.parent.iterations_widget.set_iteration_data(iteration_data)
            if self.parent.convergence_widget is not None:
                self.parent.convergence_widget.set_convergence_data(iteration_data)
            return True

        return False

    def _get_base_name_from_file(self, file_name: str) -> str:
        """Получает базовое имя файла без расширения и _clean."""
        if "_clean" in file_name:
            base_name = file_name.split("_clean")[0]
        else:
            parts = file_name.split(".")
            base_name = parts[0]
        return base_name

    def _save_iteration_results_to_disk(self, file_name: str) -> None:
        """Сохраняет данные итераций для файла на диск."""
        if file_name in self.iteration_results_data:
            # Получаем путь к исходному файлу
            file_path = self.parent.registry.get_path(file_name)
            if file_path:
                from app.core.processing import save_iteration_data

                try:
                    save_iteration_data(
                        file_path, self.iteration_results_data[file_name]
                    )
                    print(f"Данные итераций сохранены для файла: {file_name}")
                except Exception as e:
                    print(f"Ошибка при сохранении данных итераций для {file_name}: {e}")

    def _load_iteration_results_from_disk(self, file_name: str) -> bool:
        """Загружает данные итераций для файла с диска.

        Returns:
            True если данные были загружены, False иначе
        """
        # Не загружаем данные для файлов, которые были намеренно очищены
        base_name = self._get_base_name_from_file(file_name)
        if (
            file_name in self.manually_cleared_iteration_files
            or base_name in self.manually_cleared_iteration_files
        ):
            return False

        file_path = self.parent.registry.get_path(file_name)
        if file_path:
            from app.core.processing import load_iteration_data

            try:
                exists, iteration_data = load_iteration_data(file_path)
                if exists and iteration_data:
                    self.iteration_results_data[file_name] = iteration_data
                    print(f"Данные итераций загружены для файла: {file_name}")
                    return True
            except Exception as e:
                print(f"Ошибка при загрузке данных итераций для {file_name}: {e}")
        return False

    def _check_iteration_file_exists(self, file_name: str) -> bool:
        """
        Проверяет наличие файла итераций на диске без загрузки данных.

        Args:
            file_name: Имя файла

        Returns:
            True если файл итераций существует, False иначе
        """
        # Не показываем файлы, которые были намеренно очищены
        base_name = self._get_base_name_from_file(file_name)
        if (
            file_name in self.manually_cleared_iteration_files
            or base_name in self.manually_cleared_iteration_files
        ):
            return False

        try:
            file_path = self.parent.registry.get_path(file_name)
        except KeyError:
            return False

        if file_path:
            from app.core.processing import check_iteration_file_exists

            try:
                return check_iteration_file_exists(file_path)
            except Exception:
                pass
        return False

