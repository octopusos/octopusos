"""i18n - Internationalization support for OctopusOS CLI"""

from octopusos.i18n.locale_manager import (
    LocaleManager,
    get_locale_manager,
    set_language,
    get_language,
    t,
    get_available_languages,
)

__all__ = [
    "LocaleManager",
    "get_locale_manager",
    "set_language",
    "get_language",
    "t",
    "get_available_languages",
]
