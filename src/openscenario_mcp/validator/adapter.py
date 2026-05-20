from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

DEFAULT_VALIDATOR_MODULE = "openscenario_mcp.validator.real_validator"


@dataclass(slots=True)
class ValidatorAdapter:
    module_name: str = DEFAULT_VALIDATOR_MODULE

    def validate(self, xml: str, schema_version: str) -> list[Any]:
        module = importlib.import_module(self.module_name)
        return module.validate(xml=xml, schema_version=schema_version)
