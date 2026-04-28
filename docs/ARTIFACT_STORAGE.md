# Artifact Storage

OrbitRisk now has a small swappable artifact storage boundary for generated pilot
outputs:

- JSON risk responses,
- Markdown validation or benchmark reports,
- chart artifacts such as SVG plots.

The first backend is local filesystem storage via `LocalArtifactStore`. It is intended
for POC and design-partner demos, not production durability.

## Interface

The storage protocol lives in `src/orbitrisk/storage/artifacts.py`:

- `write_json_response(key, response)`
- `read_json_response(key)`
- `write_markdown_report(key, markdown)`
- `read_markdown_report(key)`
- `write_chart_artifact(key, name, content)`
- `read_chart_artifact(key, name)`

Each write returns metadata:

```json
{
  "key": "sha256-key",
  "kind": "json_response",
  "path": "data/artifacts/json_response/sha256-key.json",
  "content_hash": "sha256-content-hash",
  "content_type": "application/json",
  "size_bytes": 12345
}
```

## Deterministic Keys

Use `artifact_key(namespace, payload=...)` to derive stable keys from run context:

```python
key = artifact_key(
    "validation-report",
    payload={
        "request_id": "FR_RPG23_PIC_SAINT_LOUP_02",
        "region": "languedoc",
        "window": "2022-07-01/2022-08-31",
    },
)
```

The key is a SHA-256 digest over the namespace, version, and sorted JSON payload. The
stored content also receives a separate SHA-256 `content_hash`, so an artifact can be
identified by intended run context and audited by exact bytes.

## Local Layout

For a root such as `data/artifacts`, the filesystem backend writes:

```text
data/artifacts/
  json_response/{key}.json
  markdown_report/{key}.md
  chart_artifact/{key}/{chart_name}.svg
```

Writes are atomic at the file level: content is written to a temporary path, then
replaced into the final path.

## Future Object Storage Backend

A production/pilot backend should implement the same protocol against object storage:

- S3, GCS, Azure Blob, or equivalent,
- deterministic object keys matching `artifact_key(...)`,
- content hash persisted as metadata,
- signed URLs for result delivery,
- lifecycle rules for expensive chart/report artifacts,
- immutable writes for final actuarial evidence.

This is intentionally not implemented yet. The local backend gives the repo a concrete
storage boundary without picking infrastructure before pilot requirements are known.
