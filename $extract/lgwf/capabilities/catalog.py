import json
from pathlib import Path
from typing import Any

import lgwf.capabilities.policy.registry as policy_registry_module
import lgwf.capabilities.registry as capability_registry_module


Catalog = dict[str, Any]
CatalogEntry = dict[str, Any]

CATALOG_PATH = Path(__file__).with_name("catalog.json")


class CatalogLoadError(ValueError):
    """Raised when the capability catalog cannot be loaded."""


class CatalogValidationError(ValueError):
    """Raised when the capability catalog is invalid."""


def load_catalog(path: Path = CATALOG_PATH) -> Catalog:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CatalogLoadError(f"Capability catalog file not found: {path}") from exc
    except OSError as exc:
        raise CatalogLoadError(f"Failed to read capability catalog file: {path}") from exc

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise CatalogLoadError(f"Capability catalog file is not valid JSON: {path}") from exc

    if not isinstance(data, dict):
        raise CatalogLoadError(f"Capability catalog root must be a JSON object: {path}")

    validate_catalog(data)
    return data


def validate_catalog(catalog: Catalog) -> None:
    version = catalog.get("version")
    if not isinstance(version, int) or version < 1:
        raise CatalogValidationError("Capability catalog must include a positive integer version.")

    entries = catalog.get("capabilities")
    if not isinstance(entries, list) or not entries:
        raise CatalogValidationError("Capability catalog must include a non-empty capabilities list.")

    seen_names: set[str] = set()
    for entry in entries:
        _validate_entry(entry, seen_names)

    _validate_registry_coverage(seen_names)


def catalog_entries(catalog: Catalog) -> list[CatalogEntry]:
    entries = catalog["capabilities"]
    return list(entries)


def entry_by_name(catalog: Catalog) -> dict[str, CatalogEntry]:
    return {
        entry["name"]: entry
        for entry in catalog_entries(catalog)
    }


def _validate_entry(entry: Any, seen_names: set[str]) -> None:
    if not isinstance(entry, dict):
        raise CatalogValidationError("Capability catalog entries must be objects.")

    name = entry.get("name")
    if not isinstance(name, str) or not name:
        raise CatalogValidationError("Capability catalog entry must include a non-empty name.")
    if name in seen_names:
        raise CatalogValidationError(f"Duplicate capability catalog entry: {name}")
    seen_names.add(name)

    kind = entry.get("kind")
    if kind not in {"exec", "flow", "policy", "subgraph"}:
        raise CatalogValidationError(f"Capability catalog entry '{name}' has invalid kind.")

    _require_string(entry, "description", name)
    _require_object(entry, "config_schema", name)
    _require_string_list(entry, "reads", name)
    _require_string_list(entry, "writes", name)
    _require_string_list(entry, "side_effects", name)

    examples = entry.get("examples")
    if not isinstance(examples, list):
        raise CatalogValidationError(f"Capability catalog entry '{name}' examples must be a list.")

    if kind == "policy":
        if not policy_registry_module.has_policy(name):
            raise CatalogValidationError(f"Catalog policy is not registered: {name}")
    elif not capability_registry_module.has_capability(name):
        raise CatalogValidationError(f"Catalog capability is not registered: {name}")


def _validate_registry_coverage(catalog_names: set[str]) -> None:
    missing_capabilities = sorted(set(capability_registry_module.REGISTRY) - catalog_names)
    if missing_capabilities:
        joined = ", ".join(missing_capabilities)
        raise CatalogValidationError(f"Registered capabilities missing from catalog: {joined}")

    missing_policies = sorted(set(policy_registry_module.REGISTRY) - catalog_names)
    if missing_policies:
        joined = ", ".join(missing_policies)
        raise CatalogValidationError(f"Registered policies missing from catalog: {joined}")


def _require_string(entry: CatalogEntry, field: str, name: str) -> None:
    value = entry.get(field)
    if not isinstance(value, str) or not value:
        raise CatalogValidationError(f"Capability catalog entry '{name}' field '{field}' must be a non-empty string.")


def _require_object(entry: CatalogEntry, field: str, name: str) -> None:
    value = entry.get(field)
    if not isinstance(value, dict):
        raise CatalogValidationError(f"Capability catalog entry '{name}' field '{field}' must be an object.")


def _require_string_list(entry: CatalogEntry, field: str, name: str) -> None:
    value = entry.get(field)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise CatalogValidationError(f"Capability catalog entry '{name}' field '{field}' must be a list of strings.")

