# API Contract

## POST `/v1/risk/quote`

The contract is designed for actuarial systems: deterministic inputs, explicit quality
metadata, and no hidden assumptions about masking.

The live POC endpoint uses the same request/response contract:

```text
POST /v1/risk/quote/live?max_items=25
```

The live endpoint currently uses Planetary Computer/STAC and returns composited periods
according to `aggregation.temporal`.

For multi-year pilot requests, use the asynchronous job endpoint:

```text
POST /v1/risk/quote/jobs?max_items=80
GET /v1/risk/quote/jobs/{job_id}
GET /v1/risk/quote/jobs/{job_id}/result
```

The synchronous live endpoint remains available for small requests and smoke tests.
All live endpoints require `X-API-Key`. The unauthenticated dry-run contract endpoint
and `/health` remain open.

### Request

```json
{
  "request_id": "quote_2026_000123",
  "aoi": {
    "type": "Feature",
    "properties": {
      "asset_id": "FR_VINEYARD_42",
      "crop": "vineyard"
    },
    "geometry": {
      "type": "Polygon",
      "coordinates": [
        [
          [4.82, 45.73],
          [4.83, 45.73],
          [4.83, 45.74],
          [4.82, 45.74],
          [4.82, 45.73]
        ]
      ]
    }
  },
  "crs": "EPSG:4326",
  "crop_mask": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "properties": {
          "source": "RPG_IGN",
          "crop": "vineyard"
        },
        "geometry": {
          "type": "Polygon",
          "coordinates": [
            [
              [4.821, 45.731],
              [4.829, 45.731],
              [4.829, 45.739],
              [4.821, 45.739],
              [4.821, 45.731]
            ]
          ]
        }
      }
    ]
  },
  "crop_mask_crs": "EPSG:4326",
  "date_range": {
    "start": "2021-01-01",
    "end": "2026-04-01"
  },
  "indices": ["ndvi", "ndmi", "ndwi"],
  "aggregation": {
    "temporal": "P10D",
    "spatial_stats": ["mean", "median", "p10", "p90", "std"]
  },
  "masking": {
    "cloud_mask": true,
    "shadow_mask": true,
    "snow_mask": true,
    "negative_buffer_m": 10,
    "min_valid_pixels": 20,
    "exclude_scl_classes": [0, 1, 3, 7, 8, 9, 10, 11],
    "min_clear_fraction": 0.7
  },
  "time_series": {
    "smoothing": {
      "method": "ema",
      "alpha": 0.35
    },
    "baseline": {
      "method": "day_of_year_percentile",
      "years": 5
    }
  },
  "trigger": {
    "ndmi_ema_threshold": 0.15,
    "min_consecutive_periods": 2
  },
  "resolution_m": 10
}
```

### Response

```json
{
  "request_id": "quote_2026_000123",
  "status": "completed",
  "source": {
    "provider": "sentinel-hub",
    "collection": "sentinel-2-l2a",
    "processing_crs": "auto-utm",
    "resolution_m": 10
  },
  "aoi_metrics": {
    "area_ha": 12.42,
    "usable_area_ha": 10.91,
    "masked_area_pct": 12.2,
    "crop_mask_area_ha": 9.84,
    "crop_mask_coverage_pct": 90.2,
    "crop_mask_geometry_count": 1
  },
  "series": [
    {
      "date": "2024-07-11",
      "period": "2024-07-01/2024-07-11",
      "valid_pixel_count": 812,
      "cloud_pct": 3.8,
      "quality": "good",
      "indices": {
        "ndvi": {
          "mean": 0.61,
          "median": 0.63,
          "p10": 0.49,
          "p90": 0.72,
          "std": 0.04,
          "ema": 0.59,
          "anomaly_z": -1.4
        },
        "ndmi": {
          "mean": 0.18,
          "median": 0.19,
          "p10": 0.08,
          "p90": 0.29,
          "std": 0.03,
          "ema": 0.16,
          "anomaly_z": -2.1
        }
      },
      "mask_counts": {
        "valid": 812,
        "cloud": 31,
        "shadow": 12,
        "snow": 0,
        "outside_aoi": 418,
        "non_crop": 96
      }
    }
  ],
  "risk_signal": {
    "water_stress_score": 78,
    "trigger_candidate": true,
    "trigger_reason": "ndmi_ema_below_0.15_for_2_periods",
    "confidence": 0.82,
    "critical_periods": [
      {
        "start": "2024-07-01",
        "end": "2024-07-20",
        "severity": "high"
      }
    ]
  },
  "provenance": {
    "algorithm_version": "orbitrisk.ndmi_ema_threshold.v0",
    "processing_version": "orbitrisk.sentinel2_l2a_p10d.v0",
    "provider": "sentinel-hub",
    "collection": "sentinel-2-l2a",
    "processing_crs": "auto-utm",
    "resolution_m": 10,
    "input_hash": "sha256-risk-input",
    "cache_key": "sha256-cache-key-or-null",
    "mask_mode": "vector_crop_mask",
    "crop_mask_hash": "sha256-crop-mask-or-null"
  }
}
```

## Async Quote Jobs

Submit a job:

```http
POST /v1/risk/quote/jobs?max_items=80&use_cache=true
X-API-Key: dev-orbitrisk-key
Content-Type: application/json
```

The request body is the same `RiskRequest` used by `/v1/risk/quote/live`.

Submission response:

```json
{
  "job_id": "6fd4cfd3f8d5484ba2450da7da7e8c4a",
  "request_id": "quote_2026_000123",
  "status": "queued",
  "status_url": "/v1/risk/quote/jobs/6fd4cfd3f8d5484ba2450da7da7e8c4a",
  "result_url": "/v1/risk/quote/jobs/6fd4cfd3f8d5484ba2450da7da7e8c4a/result"
}
```

Status response:

```json
{
  "job_id": "6fd4cfd3f8d5484ba2450da7da7e8c4a",
  "request_id": "quote_2026_000123",
  "status": "completed",
  "created_at": "2026-04-28T08:30:00Z",
  "updated_at": "2026-04-28T08:31:14Z",
  "status_url": "/v1/risk/quote/jobs/6fd4cfd3f8d5484ba2450da7da7e8c4a",
  "result_url": "/v1/risk/quote/jobs/6fd4cfd3f8d5484ba2450da7da7e8c4a/result",
  "error": null
}
```

Job states:

- `queued`: accepted by the API, not yet running.
- `running`: live provider request is executing.
- `completed`: result can be fetched from `result_url`.
- `failed`: provider or processing failure; `error` contains the captured message.

The current POC uses an in-memory job store. That is enough to validate the API shape,
but it is not durable across process restarts. M4 artifact storage and/or a durable queue
should replace it before a real pilot.

## Error Responses

Live endpoints return machine-readable error details for known failure classes:

```json
{
  "detail": {
    "error": {
      "code": "invalid_geometry",
      "message": "AOI geometry is invalid",
      "request_id": "quote_2026_000123",
      "retryable": false
    }
  }
}
```

Defined error codes:

| Code | Typical HTTP status | Retryable | Meaning |
| --- | ---: | --- | --- |
| `invalid_geometry` | 422 | false | AOI is not a valid Polygon/MultiPolygon after parsing. |
| `no_scenes` | 404 | false | Provider returned no Sentinel-2 scenes for the query. |
| `cloud_only_scenes` | 422 | true | Scenes exist, but all observations are cloud blocked. |
| `insufficient_pixels` | 422 | false | All observations are below `min_valid_pixels`. |
| `provider_failure` | 502 | true | Unexpected provider or processing failure. |
| `missing_api_key` | 401 | false | Missing `X-API-Key` header on a live endpoint. |
| `invalid_api_key` | 403 | false | API key is not in `ORBITRISK_API_KEYS`. |
| `rate_limited` | 429 | true | API key exceeded `ORBITRISK_RATE_LIMIT_PER_MINUTE`. |

## Quality Rules

- Reject observations below `min_valid_pixels`.
- Reject or down-rank observations below `min_clear_fraction`.
- Return mask counts with every observation.
- Accept public AOI and crop-mask CRS as explicit `EPSG:*` identifiers; reproject internally
  to the best local UTM CRS.
- Avoid comparing time points unless the raster grid, transform, and resolution are fixed.
