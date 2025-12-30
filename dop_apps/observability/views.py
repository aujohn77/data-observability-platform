import os
from datetime import timezone
from django.shortcuts import render

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from pathlib import Path


# load only the observability .env (NOT fx/.env)
OBS_ENV = Path(__file__).resolve().parents[2] / "jobs" / ".env"
load_dotenv(dotenv_path=OBS_ENV, override=False)

def _get_obs_db_url():
    url = os.getenv("OBS_DATABASE_URL")
    if not url:
        raise RuntimeError("Missing OBS_DATABASE_URL (expected in observability jobs/.env).")
    return url


def _q(sql, params=None, many=True):
    """
    Small helper: run a SELECT and return dict rows.
    many=True -> fetchall
    many=False -> fetchone
    """
    conn = psycopg2.connect(_get_obs_db_url())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or {})
            return cur.fetchall() if many else cur.fetchone()
    finally:
        conn.close()


def status(request):
    # 1) KPIs from public view
    health = _q(
        """
        select last_success_at, failures_7d, anomalies_24h
        from public.public_platform_health
        order by last_success_at desc
        limit 1
        """,
        many=False,
    ) or {}

    last_success = health.get("last_success_at")
    if last_success is not None:
        # Make it readable in UI
        last_success_str = last_success.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    else:
        last_success_str = "—"

    # 2) Optional: recent job runs (may be RLS-protected). If blocked, just show empty.
    runs = []
    try:
        runs = _q(
            """
            select job_name, started_at, ended_at, status
            from public.ops_job_run
            order by started_at desc
            limit 10
            """
        )
        # Normalize times to short strings
        for r in runs:
            for k in ("started_at", "ended_at"):
                if r.get(k):
                    r[k] = r[k].astimezone(timezone.utc).strftime("%H:%M")
    except Exception:
        runs = []

    ctx = {
        "title": "Platform Status",
        "kpis": [
            {"label": "Last success", "value": last_success_str},
            {"label": "Failures (7d)", "value": health.get("failures_7d", 0)},
            {"label": "Anomalies (24h)", "value": health.get("anomalies_24h", 0)},
        ],
        "runs": runs,
    }
    return render(request, "observability/status.html", ctx)


def incidents(request):
    items = _q(
        """
        select
          status,
          opened_at,
          severity,
          title,
          station_id,
          metric_id
        from public.public_incidents
        order by opened_at desc
        limit 50
        """
    )

    # Format opened_at for display
    for it in items:
        if it.get("opened_at"):
            it["opened_at"] = it["opened_at"].astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")

    ctx = {
        "title": "Recent Incidents",
        "items": items,
    }
    return render(request, "observability/incidents.html", ctx)


def stations(request):
    rows = _q(
        """
        select
          station_id,
          station_name,
          last_observed_at,
          staleness
        from public.public_station_freshness
        order by station_id
        """
    )

    def freshness_label(staleness):
        # staleness is an interval -> comes back as timedelta
        if staleness is None:
            return "UNKNOWN"
        secs = staleness.total_seconds()
        if secs <= 3600:
            return "OK"
        if secs <= 6 * 3600:
            return "WARN"
        return "STALE"

    ui_rows = []
    for r in rows:
        last_seen = r.get("last_observed_at")
        ui_rows.append(
            {
                "station_id": r.get("station_id"),
                "name": r.get("station_name"),
                "freshness": freshness_label(r.get("staleness")),
                "last_seen": last_seen.astimezone(timezone.utc).strftime("%H:%M") if last_seen else "—",
            }
        )

    ctx = {
        "title": "Station Health",
        "rows": ui_rows,
    }
    return render(request, "observability/stations.html", ctx)


def freshness(request):
    # Hourly view: bucket, fresh_1h, stations_total
    points = _q(
        """
        select bucket, fresh_1h, stations_total
        from public.public_freshness_hourly
        order by bucket desc
        limit 24
        """
    )

    # Build chart series oldest->newest
    points = list(reversed(points))

    series = []
    for p in points:
        total = p.get("stations_total") or 0
        fresh = p.get("fresh_1h") or 0
        pct = round((fresh / total) * 100) if total else 0
        bucket = p.get("bucket")
        label = bucket.astimezone(timezone.utc).strftime("%m-%d %H:%M") if bucket else ""
        series.append({"bucket": label, "pct": pct})

    # Summary buckets from the same hourly data
    def avg_last(n):
        if not series:
            return 0
        tail = series[-n:] if len(series) >= n else series
        return round(sum(x["pct"] for x in tail) / len(tail)) if tail else 0

    ctx = {
        "title": "Freshness",
        "series": [
            {"bucket": "last 1h", "pct": avg_last(1)},
            {"bucket": "last 6h", "pct": avg_last(6)},
            {"bucket": "last 24h", "pct": avg_last(24)},
        ],
        # If you later create a public view for late rate, we’ll swap this to real data.
        "late_rate": "—",
    }
    return render(request, "observability/freshness.html", ctx)




def control_tower(request):
    # Top status bar
    platform_status = _q(
        """
        select *
        from public.vw_platform_status
        limit 1
        """,
        many=False,
    ) or {}

    # KPI tiles
    kpis = _q(
        """
        select *
        from public.vw_platform_kpis
        limit 1
        """,
        many=False,
    ) or {}

    # Panels
    pipeline = _q(
        """
        select *
        from public.vw_pipeline_health
        order by last_run_at desc
        """
    ) or []

    dq = _q(
        """
        select *
        from public.vw_dq_summary
        order by check_name
        """
    ) or []


    anomalies = _q(
        """
        select *
        from public.vw_anomaly_summary
        order by anomalies_24h desc nulls last
        """
    ) or []



    incidents = _q(
        """
        select *
        from public.vw_incident_summary
        limit 1
        """,
        many=False,
    ) or {}

    impact = _q(
        """
        select *
        from public.vw_station_metric_impact
        limit 10
        """
    ) or []

    trends = _q(
        """
        select *
        from public.vw_trends_24h
        order by hour_start asc
        """
    ) or []

    # Basic formatting helpers
    def fmt_dt(v, fmt="%H:%M UTC"):
        if not v:
            return "—"
        try:
            return v.astimezone(timezone.utc).strftime(fmt)
        except Exception:
            return str(v)

    ctx = {
        "title": "Control Tower",
        "status": {
            "status": platform_status.get("status_color") or platform_status.get("status") or "—",
            "last_ingest": fmt_dt(platform_status.get("last_ingest_at") or platform_status.get("last_ingest")),
            "window": platform_status.get("window") or "24h",
            "last_updated": fmt_dt(platform_status.get("as_of") or platform_status.get("last_updated_at")),
            "contracts": platform_status.get("contracts_version") or "v1",
            "rls": platform_status.get("rls_enforced"),
            "ci": platform_status.get("ci_passing"),
        },
        "kpis": {
            "freshness_worst": kpis.get("worst_freshness_minutes"),
            "ingest_success_pct": kpis.get("ingest_success_rate_pct"),
            "active_anomalies": kpis.get("active_anomaly_count"),
            "open_incidents": kpis.get("open_incident_count"),
            "dq_score_pct": kpis.get("dq_pass_rate_pct"),
            "evaluated_at": fmt_dt(kpis.get("evaluated_at"), fmt="%H:%M UTC"),
        },
        "pipeline": pipeline,
        "dq": dq,
        "anomalies": anomalies,
        "incidents": incidents,
        "impact": impact,
        "trends": trends,
    }

    return render(request, "observability/control_tower.html", ctx)







# Keep index as a simple alias if you still reference it somewhere
def index(request):
    return status(request)
