import copy
import itertools
import json
from datetime import datetime
from pathlib import Path

from sim_plane.runner import ensure_artifact_root
from sim_plane.scenario import load_scenario


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUITE_REPORT_ROOT = REPO_ROOT / "runs" / "suites"
DEFAULT_KEEP_LAST = 10


def run_suite(
    scenario_path,
    suite_path=None,
    artifact_root="runs",
    report_root=None,
    keep_last=DEFAULT_KEEP_LAST,
    runtime_options=None,
):
    base_scenario = load_scenario(scenario_path)
    suite = load_suite_definition(suite_path)
    ensure_artifact_root(artifact_root)
    rows = []
    issues = []
    for variant in suite["variants"]:
        variant_scenario = build_variant_scenario(base_scenario, variant)
        outcome = run_scenario_data(
            variant_scenario,
            artifact_root=artifact_root,
            runtime_options=runtime_options or {},
        )
        row = build_variant_report(variant, outcome)
        rows.append(row)
        issues.extend(row["issues"])
    report = {
        "suite_name": suite["name"],
        "base_scenario": str(scenario_path),
        "artifact_root": str(Path(artifact_root)),
        "status": "passed" if not issues else "failed",
        "issues": issues,
        "rows": rows,
        "metric_summary": summarize_metrics(rows),
    }
    report["factor_analysis"] = analyze_factors(rows)
    report["top_metric_effects"] = summarize_top_metric_effects(report["factor_analysis"])
    if report_root is not None:
        report["saved_report"] = write_suite_report(
            report,
            report_root=report_root,
            keep_last=keep_last,
        )
    return report


def load_suite_definition(path=None):
    if path is None:
        return {
            "name": "default_disturbance_suite",
            "variants": [
                {"name": "baseline", "overrides": {}},
                {
                    "name": "crosswind_light",
                    "overrides": {
                        "disturbances": {
                            "seed": 7,
                            "wind": {"x_mps": 0.2, "y_mps": -0.1},
                        }
                    },
                },
                {
                    "name": "sensor_noise_light",
                    "overrides": {
                        "disturbances": {
                            "seed": 11,
                            "measurement_noise": {
                                "position_std_m": 0.05,
                                "altitude_std_m": 0.03,
                            },
                        }
                    },
                },
            ],
        }
    suite_path = Path(path)
    payload = json.loads(suite_path.read_text(encoding="utf-8"))
    variants = expand_suite_variants(payload)
    if not variants:
        raise ValueError("suite must contain at least one variant")
    for index, variant in enumerate(variants):
        if not isinstance(variant, dict):
            raise ValueError("suite variant #{0} must be an object".format(index + 1))
        if "name" not in variant:
            raise ValueError("each suite variant must have a name")
        if not isinstance(variant["name"], str) or not variant["name"].strip():
            raise ValueError("suite variant #{0} name must be a non-empty string".format(index + 1))
        variant.setdefault("overrides", {})
        if not isinstance(variant["overrides"], dict):
            raise ValueError("suite variant {0} overrides must be an object".format(variant["name"]))
        validate_optional_mapping(variant, "required_metrics")
        validate_metric_thresholds(variant)
    validate_unique_variant_names(variants)
    payload.setdefault("name", suite_path.stem)
    payload["variants"] = variants
    return payload


def expand_suite_variants(payload):
    variants = payload.get("variants")
    sweep = payload.get("sweep")
    if variants is not None and sweep is not None:
        raise ValueError("suite must use either variants or sweep, not both")
    if sweep is None:
        if not isinstance(variants, list):
            raise ValueError("suite must contain at least one variant")
        return variants
    return build_sweep_variants(payload, sweep)


def build_sweep_variants(payload, sweep):
    if not isinstance(sweep, dict):
        raise ValueError("suite sweep must be an object")
    axes = sweep.get("axes")
    if not isinstance(axes, list) or not axes:
        raise ValueError("suite sweep must contain at least one axis")

    normalized_axes = []
    for index, axis in enumerate(axes):
        if not isinstance(axis, dict):
            raise ValueError("suite sweep axis #{0} must be an object".format(index + 1))
        axis_name = axis.get("name")
        if not isinstance(axis_name, str) or not axis_name.strip():
            raise ValueError("suite sweep axis #{0} name must be a non-empty string".format(index + 1))
        path = axis.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ValueError("suite sweep axis {0} path must be a non-empty string".format(axis_name))
        values = axis.get("values")
        if not isinstance(values, list) or not values:
            raise ValueError("suite sweep axis {0} must contain at least one value".format(axis_name))
        normalized_axes.append({"name": axis_name.strip(), "path": path.strip(), "values": values})

    base_overrides = payload.get("base_overrides", {})
    if not isinstance(base_overrides, dict):
        raise ValueError("suite base_overrides must be an object")
    required_metrics = payload.get("required_metrics")
    metric_thresholds = payload.get("metric_thresholds")

    variants = []
    for values in itertools.product(*[axis["values"] for axis in normalized_axes]):
        overrides = copy.deepcopy(base_overrides)
        name_parts = []
        for axis, value in zip(normalized_axes, values):
            set_path_value(overrides, axis["path"], value)
            name_parts.append("{0}_{1}".format(axis["name"], sanitize_variant_name(value)))
        factors = [
            {
                "name": axis["name"],
                "path": axis["path"],
                "value": copy.deepcopy(value),
            }
            for axis, value in zip(normalized_axes, values)
        ]
        variant = {
            "name": "_".join(name_parts),
            "overrides": overrides,
            "factors": factors,
        }
        if required_metrics is not None:
            variant["required_metrics"] = copy.deepcopy(required_metrics)
        if metric_thresholds is not None:
            variant["metric_thresholds"] = copy.deepcopy(metric_thresholds)
        variants.append(variant)
    return variants


def set_path_value(target, dotted_path, value):
    parts = [part for part in dotted_path.split(".") if part]
    if not parts:
        raise ValueError("suite sweep path must not be empty")
    current = target
    for part in parts[:-1]:
        existing = current.get(part)
        if existing is None:
            existing = {}
            current[part] = existing
        if not isinstance(existing, dict):
            raise ValueError("suite sweep path {0} conflicts with non-object value".format(dotted_path))
        current = existing
    current[parts[-1]] = copy.deepcopy(value)


def validate_optional_mapping(variant, field_name):
    value = variant.get(field_name)
    if value is not None and not isinstance(value, dict):
        raise ValueError("suite variant {0} {1} must be an object".format(variant["name"], field_name))


def validate_metric_thresholds(variant):
    thresholds = variant.get("metric_thresholds")
    if thresholds is None:
        return
    if not isinstance(thresholds, dict):
        raise ValueError("suite variant {0} metric_thresholds must be an object".format(variant["name"]))
    for metric_name, threshold in thresholds.items():
        if not isinstance(threshold, dict):
            raise ValueError(
                "suite variant {0} metric_thresholds.{1} must be an object".format(
                    variant["name"],
                    metric_name,
                )
            )
        for key in threshold:
            if key not in ("min", "max"):
                raise ValueError(
                    "suite variant {0} metric_thresholds.{1} uses unsupported key {2}".format(
                        variant["name"],
                        metric_name,
                        key,
                    )
                )
        for key in ("min", "max"):
            value = threshold.get(key)
            if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool)):
                raise ValueError(
                    "suite variant {0} metric_thresholds.{1}.{2} must be a number".format(
                        variant["name"],
                        metric_name,
                        key,
                    )
                )


def validate_unique_variant_names(variants):
    seen_names = set()
    seen_safe_names = set()
    for variant in variants:
        name = variant["name"]
        safe_name = sanitize_variant_name(name)
        if name in seen_names:
            raise ValueError("suite variant name {0} is duplicated".format(name))
        if safe_name in seen_safe_names:
            raise ValueError("suite variant name {0} collides after sanitizing".format(name))
        seen_names.add(name)
        seen_safe_names.add(safe_name)


def build_variant_scenario(base_scenario, variant):
    scenario = copy.deepcopy(base_scenario)
    scenario["name"] = "{0}_{1}".format(base_scenario["name"], sanitize_variant_name(variant["name"]))
    scenario["suite_variant"] = variant["name"]
    deep_merge(scenario, copy.deepcopy(variant.get("overrides", {})))
    return scenario


def run_scenario_data(scenario, artifact_root, runtime_options):
    from sim_plane.runner import apply_runtime_options, get_backend, RunSink
    from sim_plane.artifacts import ArtifactWriter, build_artifact_dir

    scenario = apply_runtime_options(scenario, runtime_options)
    backend_name = scenario["backend"]
    backend = get_backend(backend_name)
    artifact_dir = build_artifact_dir(artifact_root, scenario["name"])
    writer = ArtifactWriter(artifact_dir, scenario, backend_name)
    writer.initialize()
    sink = RunSink(writer, None)
    sink.emit_event("info", "suite variant started", {"variant": scenario.get("suite_variant")})
    for issue in backend.validate_environment(scenario):
        sink.emit_event("warning", "environment issue", {"message": issue})
    try:
        result = backend.run(scenario, sink)
    except Exception as exc:
        result = {
            "status": "failed",
            "backend": backend_name,
            "vehicle": scenario["vehicle"],
            "scenario_name": scenario["name"],
            "error": str(exc),
        }
        sink.emit_event("error", "suite variant failed", {"error": str(exc)})
    writer.write_result(result)
    return {
        "artifact_dir": str(artifact_dir),
        "result": result,
    }


def build_variant_report(variant, outcome):
    result = outcome.get("result", {})
    issues = []
    expected_status = variant.get("required_status", "passed")
    if result.get("status") != expected_status:
        issues.append(
            "variant {0} status mismatch: expected {1}, got {2}".format(
                variant["name"],
                expected_status,
                result.get("status"),
            )
        )
    metrics = result.get("metrics", {})
    for metric_name, expected_value in variant.get("required_metrics", {}).items():
        actual_value = metrics.get(metric_name)
        if actual_value != expected_value:
            issues.append(
                "variant {0} metric {1} mismatch: expected {2}, got {3}".format(
                    variant["name"],
                    metric_name,
                    expected_value,
                    actual_value,
                )
            )
    for metric_name, threshold in variant.get("metric_thresholds", {}).items():
        actual_value = metrics.get(metric_name)
        if actual_value is None:
            issues.append("variant {0} metric {1} missing".format(variant["name"], metric_name))
            continue
        min_value = threshold.get("min")
        max_value = threshold.get("max")
        if min_value is not None and actual_value < min_value:
            issues.append(
                "variant {0} metric {1} value {2} is below min {3}".format(
                    variant["name"],
                    metric_name,
                    actual_value,
                    min_value,
                )
            )
        if max_value is not None and actual_value > max_value:
            issues.append(
                "variant {0} metric {1} value {2} exceeds max {3}".format(
                    variant["name"],
                    metric_name,
                    actual_value,
                    max_value,
                )
            )
    return {
        "name": variant["name"],
        "status": "passed" if not issues else "failed",
        "artifact_dir": outcome.get("artifact_dir"),
        "metrics": metrics,
        "factors": copy.deepcopy(variant.get("factors", [])),
        "issues": issues,
    }


def summarize_metrics(rows):
    metric_names = sorted(
        {
            name
            for row in rows
            for name, value in row.get("metrics", {}).items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
    )
    summary = {}
    for metric_name in metric_names:
        values = [
            row["metrics"][metric_name]
            for row in rows
            if isinstance(row.get("metrics", {}).get(metric_name), (int, float))
            and not isinstance(row.get("metrics", {}).get(metric_name), bool)
        ]
        if not values:
            continue
        summary[metric_name] = {
            "min": min(values),
            "max": max(values),
            "spread": max(values) - min(values),
        }
    return summary


def analyze_factors(rows):
    analysis = {}
    for row in rows:
        metrics = row.get("metrics", {})
        numeric_metrics = {
            name: value
            for name, value in metrics.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
        for factor in row.get("factors", []):
            factor_name = factor.get("name")
            if not factor_name:
                continue
            factor_entry = analysis.setdefault(
                factor_name,
                {
                    "path": factor.get("path", ""),
                    "values": {},
                    "metric_effects": {},
                },
            )
            value_key = json.dumps(factor.get("value"), ensure_ascii=False, sort_keys=True)
            value_entry = factor_entry["values"].setdefault(
                value_key,
                {
                    "value": factor.get("value"),
                    "row_count": 0,
                    "metrics": {},
                },
            )
            value_entry["row_count"] += 1
            for metric_name, metric_value in numeric_metrics.items():
                metric_entry = value_entry["metrics"].setdefault(metric_name, {"values": []})
                metric_entry["values"].append(metric_value)

    for factor_entry in analysis.values():
        for value_entry in factor_entry["values"].values():
            for metric_name, metric_entry in list(value_entry["metrics"].items()):
                values = metric_entry.pop("values")
                metric_entry.update(summarize_numeric_values(values))
        factor_entry["metric_effects"] = summarize_factor_effects(factor_entry["values"])
    return analysis


def summarize_numeric_values(values):
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": round(sum(values) / len(values), 6),
        "spread": max(values) - min(values),
    }


def summarize_factor_effects(value_entries):
    metric_names = sorted(
        {
            metric_name
            for value_entry in value_entries.values()
            for metric_name in value_entry.get("metrics", {})
        }
    )
    effects = {}
    for metric_name in metric_names:
        means = [
            value_entry["metrics"][metric_name]["mean"]
            for value_entry in value_entries.values()
            if metric_name in value_entry.get("metrics", {})
        ]
        if len(means) < 2:
            continue
        effects[metric_name] = {
            "mean_min": min(means),
            "mean_max": max(means),
            "mean_spread": round(max(means) - min(means), 6),
        }
    return effects


def summarize_top_metric_effects(factor_analysis):
    effects = []
    for factor_name, factor_entry in factor_analysis.items():
        for metric_name, metric_effect in factor_entry.get("metric_effects", {}).items():
            mean_spread = metric_effect.get("mean_spread")
            if not isinstance(mean_spread, (int, float)) or mean_spread <= 0:
                continue
            effects.append(
                {
                    "factor": factor_name,
                    "path": factor_entry.get("path", ""),
                    "metric": metric_name,
                    "mean_spread": mean_spread,
                    "mean_min": metric_effect.get("mean_min"),
                    "mean_max": metric_effect.get("mean_max"),
                }
            )
    return sorted(effects, key=lambda item: (-item["mean_spread"], item["factor"], item["metric"]))


def write_suite_report(report, report_root=None, keep_last=DEFAULT_KEEP_LAST):
    root = Path(report_root) if report_root is not None else DEFAULT_SUITE_REPORT_ROOT
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    suite_name = sanitize_variant_name(report.get("suite_name", "suite"))
    report_dir = root / "{0}_{1}".format(suite_name, stamp)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_json = report_dir / "report.json"
    latest_json = root / "latest_{0}.json".format(suite_name)
    history_jsonl = root / "history_{0}.jsonl".format(suite_name)
    serializable = dict(report)
    serializable.pop("saved_report", None)
    report_json.write_text(json.dumps(serializable, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    latest_json.write_text(json.dumps(serializable, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with history_jsonl.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "created_at_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "suite_name": report.get("suite_name"),
                    "status": report.get("status"),
                    "report_json": str(report_json),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    if keep_last and keep_last > 0:
        prune_suite_reports(root, suite_name, keep_last)
    return {
        "report_dir": str(report_dir),
        "report_json": str(report_json),
        "latest_json": str(latest_json),
        "history_jsonl": str(history_jsonl),
    }


def prune_suite_reports(report_root, suite_name, keep_last):
    pattern = "{0}_*".format(suite_name)
    report_dirs = sorted(
        [path for path in Path(report_root).glob(pattern) if path.is_dir()],
        key=lambda path: path.name,
    )
    for path in report_dirs[:-keep_last]:
        for child in sorted(path.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        path.rmdir()


def format_suite_report(report):
    lines = [
        "suite: {0} ({1})".format(report["suite_name"], report["status"]),
        "base_scenario: {0}".format(report["base_scenario"]),
        "artifact_root: {0}".format(report["artifact_root"]),
        "",
        "{0:<24} {1:<8} {2}".format("variant", "status", "artifact_dir"),
        "-" * 78,
    ]
    for row in report["rows"]:
        lines.append("{0:<24} {1:<8} {2}".format(row["name"], row["status"], row.get("artifact_dir") or "-"))
        if row.get("metrics"):
            lines.append("  metrics={0}".format(json.dumps(row["metrics"], ensure_ascii=False, sort_keys=True)))
        for issue in row.get("issues", []):
            lines.append("  issue={0}".format(issue))
    if report.get("metric_summary"):
        lines.append("")
        lines.append("metric_summary={0}".format(json.dumps(report["metric_summary"], ensure_ascii=False, sort_keys=True)))
    if report.get("factor_analysis"):
        lines.append("")
        lines.append("factor_analysis={0}".format(json.dumps(report["factor_analysis"], ensure_ascii=False, sort_keys=True)))
    if report.get("top_metric_effects"):
        lines.append("")
        lines.append("top_metric_effects={0}".format(json.dumps(report["top_metric_effects"], ensure_ascii=False, sort_keys=True)))
    saved = report.get("saved_report")
    if saved:
        lines.append("")
        lines.append("report_dir: {0}".format(saved["report_dir"]))
        lines.append("latest_json: {0}".format(saved["latest_json"]))
        lines.append("history_jsonl: {0}".format(saved["history_jsonl"]))
    return "\n".join(lines)


def deep_merge(target, overrides):
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_merge(target[key], value)
        else:
            target[key] = value


def sanitize_variant_name(value):
    safe = []
    for char in str(value):
        if char.isalnum() or char in ("_", "-"):
            safe.append(char)
        else:
            safe.append("_")
    return "".join(safe).strip("_") or "variant"
