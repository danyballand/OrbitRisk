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
  }
}
```

## Quality Rules

- Reject observations below `min_valid_pixels`.
- Reject or down-rank observations below `min_clear_fraction`.
- Return mask counts with every observation.
- Accept public AOI and crop-mask CRS as explicit `EPSG:*` identifiers; reproject internally
  to the best local UTM CRS.
- Avoid comparing time points unless the raster grid, transform, and resolution are fixed.
