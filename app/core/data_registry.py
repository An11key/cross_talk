from __future__ import annotations

from typing import Dict
import pandas as pd


class DataRegistry:
    def __init__(self) -> None:
        self._name_to_path: Dict[str, str] = {}
        self._name_to_df: Dict[str, pd.DataFrame] = {}

    def set_file(self, display_name: str, path: str) -> None:
        self._name_to_path[display_name] = path

    def get_path(self, display_name: str) -> str:
        return self._name_to_path[display_name]

    def has_file(self, display_name: str) -> bool:
        return display_name in self._name_to_path

    def remove(self, display_name: str) -> None:
        self._name_to_path.pop(display_name, None)
        self._name_to_df.pop(display_name, None)

    def set_df(self, display_name: str, df: pd.DataFrame) -> None:
        self._name_to_df[display_name] = df

    def get_df(self, display_name: str) -> pd.DataFrame:
        return self._name_to_df[display_name]

    def has_df(self, display_name: str) -> bool:
        return display_name in self._name_to_df
