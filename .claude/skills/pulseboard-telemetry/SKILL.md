---
name: pulseboard-telemetry
description: How to add ArtSmoker telemetry events and deploy the PulseBoard dashboard. Use when adding/changing track_event calls or deploying PulseBoard.
---

# Telemetry (PulseBoard)

## How to add a telemetry event

```python
from backend.services.telemetry import track_event
track_event("event_name", key1="value1", cost_usd=0.01)
```

Events are sent to PulseBoard via `POST /ingest` with the project API key. Cost events use `.cost` suffix for aggregation (no double-counting with action events).

## PulseBoard deployment

```bash
cd /Users/niravdd/Documents/GitHub/PulseBoard
sam build && sam deploy --no-confirm-changeset
./deploy.sh  # Dashboard files to S3 + CloudFront invalidation
```
