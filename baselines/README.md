# Versioned Acceptance Baselines

This directory contains the compact evidence required by the checked-in
acceptance matrices. It deliberately does not contain simulator logs, raw
telemetry, ROS logs, ULog files, or other large run output.

Artifact baselines retain only:

- `manifest.json`
- `result.json`
- `events.jsonl`
- `baseline.json` with source identity and SHA-256 checksums

Suite baselines retain the accepted report plus the same provenance metadata.
The original full evidence remains under ignored `runs/` on the machine that
created the baseline.

Refresh baselines only as an explicit acceptance-contract operation:

```bash
python3 scripts/freeze_acceptance_baselines.py
```

Review the matrix, baseline payload, source artifact, checksums, and resulting
acceptance delta before committing a refreshed baseline.
