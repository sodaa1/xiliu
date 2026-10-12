from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CapabilityKind = Literal["app", "builtin", "skill", "mcp", "agent"]


@dataclass(frozen=True)
class CapabilityRef:
    id: str
    kind: CapabilityKind
    source_id: str


@dataclass(frozen=True)
class CapabilitySpec(CapabilityRef):
    name: str
    description: str
    enabled: bool = True
    schema_digest: str = ""
    permission: str = ""
    requires_confirmation: bool = False
