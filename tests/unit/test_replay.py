import json
from pathlib import Path

from orbitrisk.cli import main
from orbitrisk.demo.replay import load_replay_rows, render_replay_table, summarize_rows


def _write_report(path: Path) -> Path:
    document = {
        "aois": [
            {
                "aoi_id": "FR_RPG23_TEST_01",
                "region": "bordeaux",
                "validation": {
                    "validation_assessment": {
                        "classification": "accepted",
                        "reasons": [],
                        "inputs": {
                            "trigger_candidate": True,
                            "min_baseline_percentile": 0.0,
                            "min_valid_pixel_count": 1200,
                        },
                    }
                },
            },
            {
                "aoi_id": "FR_RPG23_TEST_02",
                "region": "languedoc",
                "validation": {
                    "validation_assessment": {
                        "classification": "ambiguous",
                        "reasons": ["seasonal_percentile_not_low"],
                        "inputs": {
                            "trigger_candidate": True,
                            "min_baseline_percentile": 0.56,
                            "min_valid_pixel_count": 300,
                        },
                    }
                },
            },
        ]
    }
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_replay_rows_and_summary(tmp_path: Path) -> None:
    rows = load_replay_rows([_write_report(tmp_path / "report.json")])
    assert [row["classification"] for row in rows] == ["accepted", "ambiguous"]
    assert summarize_rows(rows) == {"analysed": 2, "accepted": 1, "ambiguous": 1, "rejected": 0}
    table = render_replay_table(rows)
    assert "TEST_02" in table
    assert "seasonal_percentile_not_low" in table
    assert "2 parcels analysed: 1 accepted, 1 ambiguous, 0 rejected" in table


def test_replay_cli_json(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    report = _write_report(tmp_path / "report.json")
    assert main(["replay-2022", "--report", str(report), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["accepted"] == 1


def test_replay_tracked_reports_match_readme() -> None:
    root = Path(__file__).resolve().parents[2]
    rows = load_replay_rows(
        [
            root / "reports/bordeaux-2022-batch-validation.json",
            root / "reports/languedoc-2022-batch-validation.json",
        ]
    )
    assert summarize_rows(rows) == {"analysed": 10, "accepted": 6, "ambiguous": 4, "rejected": 0}
