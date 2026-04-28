import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from orbitrisk.schemas.response import RiskResponse

ArtifactKind = Literal["json_response", "markdown_report", "chart_artifact"]


@dataclass(frozen=True)
class ArtifactMetadata:
    key: str
    kind: ArtifactKind
    path: Path
    content_hash: str
    content_type: str
    size_bytes: int


class ArtifactStore(Protocol):
    def write_json_response(self, key: str, response: RiskResponse) -> ArtifactMetadata: ...

    def read_json_response(self, key: str) -> RiskResponse | None: ...

    def write_markdown_report(self, key: str, markdown: str) -> ArtifactMetadata: ...

    def read_markdown_report(self, key: str) -> str | None: ...

    def write_chart_artifact(
        self,
        key: str,
        name: str,
        content: bytes,
        *,
        suffix: str = ".svg",
        content_type: str = "image/svg+xml",
    ) -> ArtifactMetadata: ...

    def read_chart_artifact(
        self,
        key: str,
        name: str,
        *,
        suffix: str = ".svg",
    ) -> bytes | None: ...


class LocalArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def write_json_response(self, key: str, response: RiskResponse) -> ArtifactMetadata:
        content = response.model_dump_json(indent=2).encode("utf-8")
        path = self._artifact_path("json_response", key, ".json")
        return self._write_bytes(
            key,
            kind="json_response",
            path=path,
            content=content,
            content_type="application/json",
        )

    def read_json_response(self, key: str) -> RiskResponse | None:
        path = self._artifact_path("json_response", key, ".json")
        if not path.exists():
            return None
        return RiskResponse.model_validate_json(path.read_text())

    def write_markdown_report(self, key: str, markdown: str) -> ArtifactMetadata:
        content = markdown.encode("utf-8")
        path = self._artifact_path("markdown_report", key, ".md")
        return self._write_bytes(
            key,
            kind="markdown_report",
            path=path,
            content=content,
            content_type="text/markdown; charset=utf-8",
        )

    def read_markdown_report(self, key: str) -> str | None:
        path = self._artifact_path("markdown_report", key, ".md")
        if not path.exists():
            return None
        return path.read_text()

    def write_chart_artifact(
        self,
        key: str,
        name: str,
        content: bytes,
        *,
        suffix: str = ".svg",
        content_type: str = "image/svg+xml",
    ) -> ArtifactMetadata:
        path = self._chart_path(key, name, suffix=suffix)
        return self._write_bytes(
            key,
            kind="chart_artifact",
            path=path,
            content=content,
            content_type=content_type,
        )

    def read_chart_artifact(
        self,
        key: str,
        name: str,
        *,
        suffix: str = ".svg",
    ) -> bytes | None:
        path = self._chart_path(key, name, suffix=suffix)
        if not path.exists():
            return None
        return path.read_bytes()

    def _artifact_path(self, kind: ArtifactKind, key: str, suffix: str) -> Path:
        return self.root / kind / f"{_safe_segment(key)}{suffix}"

    def _chart_path(self, key: str, name: str, *, suffix: str) -> Path:
        return (
            self.root
            / "chart_artifact"
            / _safe_segment(key)
            / f"{_safe_segment(name)}{_safe_suffix(suffix)}"
        )

    def _write_bytes(
        self,
        key: str,
        *,
        kind: ArtifactKind,
        path: Path,
        content: bytes,
        content_type: str,
    ) -> ArtifactMetadata:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(f"{path.suffix}.tmp")
        tmp_path.write_bytes(content)
        tmp_path.replace(path)
        return ArtifactMetadata(
            key=key,
            kind=kind,
            path=path,
            content_hash=content_hash(content),
            content_type=content_type,
            size_bytes=len(content),
        )


def artifact_key(
    namespace: str,
    *,
    payload: Mapping[str, Any] | None = None,
    version: str = "artifact-v1",
) -> str:
    content = {
        "namespace": namespace,
        "payload": payload or {},
        "version": version,
    }
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _safe_segment(value: str) -> str:
    segment = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return segment or "artifact"


def _safe_suffix(value: str) -> str:
    suffix = value if value.startswith(".") else f".{value}"
    return "." + _safe_segment(suffix[1:])
