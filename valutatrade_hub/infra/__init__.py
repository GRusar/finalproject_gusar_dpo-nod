"""Инфраструктурные компоненты (синглтоны, хранилища и пр.)."""

from valutatrade_hub.infra.settings import SettingsLoader, settings

__all__ = ["SettingsLoader", "settings"]
