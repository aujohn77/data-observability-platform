from django.shortcuts import render

def index(request):
    return render(request, "observability/status.html")

def status(request):
    ctx = {
        "title": "Platform Status",
        "kpis": [
            {"label": "Last success", "value": "2025-12-28 12:34"},
            {"label": "Failures (7d)", "value": 1},
            {"label": "Anomalies (24h)", "value": 406},
        ],
        "runs": [
            {"job_name": "ingest_openmeteo_all_stations", "started_at": "12:00", "ended_at": "12:02", "status": "success"},
            {"job_name": "transform_raw_to_fact", "started_at": "12:03", "ended_at": "12:04", "status": "success"},
        ],
    }
    return render(request, "observability/status.html", ctx)

def incidents(request):
    ctx = {
        "title": "Recent Incidents",
        "items": [
            {"status": "open", "opened_at": "2025-12-28 09:10", "severity": "high", "title": "Station silent", "station_id": 1003, "metric_id": None},
            {"status": "resolved", "opened_at": "2025-12-27 21:05", "severity": "med", "title": "Spike detected", "station_id": 2001, "metric_id": 3},
        ],
    }
    return render(request, "observability/incidents.html", ctx)

def stations(request):
    ctx = {
        "title": "Station Health",
        "rows": [
            {"station_id": 1001, "name": "SMOKE TEST 1001", "freshness": "OK", "last_seen": "12:33"},
            {"station_id": 1003, "name": "Station 1003", "freshness": "STALE", "last_seen": "08:10"},
        ],
    }
    return render(request, "observability/stations.html", ctx)

def freshness(request):
    ctx = {
        "title": "Freshness",
        "series": [
            {"bucket": "last 1h", "pct": 92},
            {"bucket": "last 6h", "pct": 97},
            {"bucket": "last 24h", "pct": 99},
        ],
        "late_rate": "3.4%",
    }
    return render(request, "observability/freshness.html", ctx)
