from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PendingAction:
    type: str
    lang: str = "en"
    context: Dict[str, Any] = field(default_factory=dict)
    resume: Optional[Dict[str, Any]] = None
