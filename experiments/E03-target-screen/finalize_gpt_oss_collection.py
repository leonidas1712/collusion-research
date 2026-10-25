"""Backfill immutable timing metadata and freeze the gpt-oss collection manifest."""

import argparse
import hashlib
import json
from pathlib import Path

from escalation_sweep import episode_record, first_emission_indices, first_peer_ask, summarize


QUOTAS = {"recruiting": 50, "control": 10}


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exclusion_reason(record):
    if record.get("status") != "complete":
        return "incomplete"
    if not record.get("token_in_context"):
        return "protected_value_not_read"
    if record.get("valid_for_comparison") is not True:
        return "invalid_for_comparison"
    return None


def backfill_run(run_dir, postprocess_commit):
    meta = read_json(run_dir / "meta.json")
    settings = meta["settings"]
    scenario = settings["scenario"]
    strategy = settings["strategy"]
    records = []
    attempts = []
    stored_records = {row["episode_id"]: row for row in read_json(run_dir / "records.json")}
    for episode_id, old_record in stored_records.items():
        episode_path = run_dir / "episodes" / f"{episode_id}.json"
        if not episode_path.exists():
            attempts.append({
                "run_id": meta["id"], "scenario": scenario,
                "condition": old_record["condition"], "episode_id": episode_id,
                "family_id": None, "episode_file": None, "episode_sha256": None,
                "selected": False, "exclusion_reason": "episode_file_missing",
            })
            records.append(old_record)
            continue
        episode = read_json(episode_path)
        ask = first_peer_ask(episode)
        emissions = first_emission_indices(episode)
        collection = dict(episode.get("collection_metadata") or {})
        collection.update({
            "first_ask_round": ask["round"],
            "first_ask_text": ask["text"],
            "first_ask_method": ask["method"],
            "primary_forbidden_action": "channel_publication",
            "secondary_forbidden_action": "other_file_disclosure",
            "analysis_cutoff": "first_any_exact_secret_emission",
            "postprocess_commit": postprocess_commit,
            **emissions,
        })
        episode["collection_metadata"] = collection
        write_json(episode_path, episode)
        record = episode_record(scenario, strategy, old_record["condition"], episode)
        records.append(record)
        scenario_meta = (episode.get("scenario_spec") or {}).get("metadata") or {}
        attempts.append({
            "run_id": meta["id"], "scenario": scenario,
            "condition": old_record["condition"], "episode_id": episode_id,
            "family_id": scenario_meta.get("family_id"),
            "episode_file": str(episode_path), "episode_sha256": sha256(episode_path),
            "selected": False, "exclusion_reason": exclusion_reason(record),
            "first_ask_round": record.get("first_ask_round"),
            "read_round": record.get("token_read_round"),
            "first_any_emission_round": record.get("first_any_emission_round"),
            "first_any_emission_request_index": record.get("first_any_emission_request_index"),
            "first_channel_emission_round": record.get("first_channel_emission_round"),
            "first_channel_emission_request_index": record.get("first_channel_emission_request_index"),
            "first_file_emission_round": record.get("first_file_emission_round"),
            "first_file_emission_request_index": record.get("first_file_emission_request_index"),
            "channel_publication": bool(record.get("channel_disclosure")),
            "other_file_disclosure": bool(record.get("other_file_disclosure")),
        })
    write_json(run_dir / "records.json", records)
    current_summary = read_json(run_dir / "summary.json") if (run_dir / "summary.json").exists() else {}
    current_summary["summary"] = summarize(records)
    current_summary["timing_metadata_postprocess_commit"] = postprocess_commit
    write_json(run_dir / "summary.json", current_summary)
    return attempts


def freeze_manifest(run_dirs, output_dir, postprocess_commit):
    attempts = []
    for run_dir in run_dirs:
        attempts.extend(backfill_run(run_dir, postprocess_commit))

    scenarios = sorted({row["scenario"] for row in attempts})
    deficits = []
    for scenario in scenarios:
        for condition, quota in QUOTAS.items():
            eligible = sorted(
                (row for row in attempts
                 if row["scenario"] == scenario and row["condition"] == condition
                 and row["exclusion_reason"] is None),
                key=lambda row: (int(row["family_id"]), row["run_id"], row["episode_id"]),
            )
            for row in eligible[:quota]:
                row["selected"] = True
            for row in eligible[quota:]:
                row["exclusion_reason"] = "surplus_valid_topup"
            if len(eligible) < quota:
                deficits.append({"scenario": scenario, "condition": condition,
                                 "needed": quota - len(eligible)})

    selected = [row for row in attempts if row["selected"]]
    excluded = [row for row in attempts if not row["selected"]]
    manifest = {
        "schema_version": 1,
        "analysis_cutoff": "first_any_exact_secret_emission",
        "primary_episode_label": "channel_publication",
        "postprocess_commit": postprocess_commit,
        "run_ids": [path.name for path in run_dirs],
        "quotas": QUOTAS,
        "deficits": deficits,
        "selected_episode_count": len(selected),
        "excluded_attempt_count": len(excluded),
        "episodes": selected,
    }
    write_json(output_dir / "manifest.json", manifest)
    write_json(output_dir / "excluded_attempts.json", excluded)
    write_json(output_dir / "all_attempts.json", attempts)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", action="append", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--postprocess-commit", required=True)
    args = parser.parse_args()
    manifest = freeze_manifest(args.run_dir, args.output_dir, args.postprocess_commit)
    print(json.dumps({key: manifest[key] for key in
                      ("selected_episode_count", "excluded_attempt_count", "deficits")},
                     indent=2))
    if manifest["deficits"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
