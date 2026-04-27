import hashlib
import json
from pathlib import Path
from typing import Any

from orbitrisk.schemas.request import RiskRequest
from orbitrisk.schemas.response import RiskResponse

CACHE_VERSION = "risk-response-v1"


class LocalRiskResponseCache:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.quote_dir = root / "risk_quotes"

    def get(self, key: str) -> RiskResponse | None:
        path = self._path(key)
        if not path.exists():
            return None
        return RiskResponse.model_validate_json(path.read_text())

    def set(self, key: str, response: RiskResponse) -> Path:
        self.quote_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(key)
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(response.model_dump_json(indent=2))
        tmp_path.replace(path)
        return path

    def _path(self, key: str) -> Path:
        return self.quote_dir / f"{key}.json"


def risk_response_cache_key(
    payload: RiskRequest,
    *,
    provider_name: str,
    collection: str,
    max_items: int | None,
    extra: dict[str, Any] | None = None,
) -> str:
    content: dict[str, Any] = {
        "version": CACHE_VERSION,
        "provider": provider_name,
        "collection": collection,
        "max_items": max_items,
        "extra": extra or {},
        "payload": payload.model_dump(mode="json"),
    }
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
