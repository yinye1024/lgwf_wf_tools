import difflib

import lgwf.capabilities.catalog as catalog_module


class CapabilityCatalogView:
    def __init__(self, names: set[str]) -> None:
        self._names = names

    @classmethod
    def load_default(cls) -> "CapabilityCatalogView":
        catalog = catalog_module.load_catalog()
        return cls(set(catalog_module.entry_by_name(catalog)))

    def has_capability(self, name: str) -> bool:
        return name in self._names

    def suggest_capability(self, name: str) -> str | None:
        matches = difflib.get_close_matches(name, sorted(self._names), n=1, cutoff=0.65)
        if not matches:
            return None
        return matches[0]
