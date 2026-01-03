import os
from datetime import timezone as dt_timezone
from pathlib import Path

from django.shortcuts import render
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor


# load only the observability .env (NOT fx/.env)
OBS_ENV = Path(__file__).resolve().parents[2] / "jobs" / ".env"
load_dotenv(dotenv_path=OBS_ENV, override=False)


def _get_obs_db_url():
    url = os.getenv("OBS_DATABASE_URL")
    if not url:
        raise RuntimeError("Missing OBS_DATABASE_URL (expected in observability jobs/.env).")
    return url


def _to_utc_str(v, fmt="%Y-%m-%d %H:%M UTC"):
    """Format aware datetimes as UTC for consistent UI rendering."""
    if not v:
        return "—"
    try:
        return v.astimezone(dt_timezone.utc).strftime(fmt)
    except Exception:
        return str(v)


def _q(sql, params=None, many=True):
    """
    Legacy helper: run a SELECT and return dict rows.
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


def _q_cur(cur, sql, params=None, many=True):
    """Run a SELECT using an existing cursor (single-connection per request)."""
    cur.execute(sql, params or {})
    return cur.fetchall() if many else cur.fetchone()


def incidents(request):
    # NOTE: This pulls from the VIEW (safer) not the base table.
    items = _q(
        """
        select
          status,
          opened_at,
          severity,
          title,
          station_id,
          metric_id
        from public.vw_incident_summary
        order by opened_at desc nulls last
        limit 50
        """
    )

    for it in items:
        if it.get("opened_at"):
            it["opened_at"] = _to_utc_str(it["opened_at"], "%Y-%m-%d %H:%M")

    ctx = {"title": "Recent Incidents", "items": items}
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
                "last_seen": _to_utc_str(last_seen, "%H:%M") if last_seen else "—",
            }
        )

    ctx = {"title": "Station Health", "rows": ui_rows}
    return render(request, "observability/stations.html", ctx)


def control_tower(request):
    """
    Performance fixes:
    1) Single DB connection for the whole view (Supabase SSL handshakes are expensive)
    2) Remove heavy queries not used in the template (impact, trends)
    3) Select only needed columns (avoid pulling big JSONB/details via select *)
    """
    conn = psycopg2.connect(_get_obs_db_url(), connect_timeout=5)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            platform_status = _q_cur(
                cur,
                """
                select *
                from public.vw_platform_status
                limit 1
                """,
                many=False,
            ) or {}

            pipeline = _q_cur(
                cur,
                """
                select *
                from public.vw_pipeline_health
                order by last_run_at desc
                """,
            ) or []

            dq = _q_cur(
                cur,
                """
                select *
                from public.vw_dq_summary
                order by check_name
                """,
            ) or []

            anomalies = _q_cur(
                cur,
                """
                select
                  anomaly_type,
                  anomalies_24h
                from public.vw_anomaly_summary
                order by anomalies_24h desc nulls last
                """,
            ) or []

            incidents_kpis = _q_cur(
                cur,
                """
                select
                  open_count,
                  acknowledged_count,
                  resolved_count_total,
                  resolved_count_24h
                from public.vw_incident_kpis
                """,
                many=False,
            ) or {}

    finally:
        conn.close()

    # Force UTC display for pipeline & dq timestamps (so templates never auto-localize)
    for r in pipeline:
        if r.get("last_run_at"):
            r["last_run_at"] = _to_utc_str(r["last_run_at"], "%Y-%m-%d %H:%M")
        if r.get("started_at"):
            r["started_at"] = _to_utc_str(r["started_at"], "%Y-%m-%d %H:%M")
        if r.get("ended_at"):
            r["ended_at"] = _to_utc_str(r["ended_at"], "%Y-%m-%d %H:%M")

    for r in dq:
        if r.get("last_run_at"):
            r["last_run_at"] = _to_utc_str(r["last_run_at"], "%Y-%m-%d %H:%M")
        if r.get("checked_at"):
            r["checked_at"] = _to_utc_str(r["checked_at"], "%Y-%m-%d %H:%M")
        if r.get("run_at"):
            r["run_at"] = _to_utc_str(r["run_at"], "%Y-%m-%d %H:%M")

    def fmt_dt(v, fmt="%H:%M"):
        return _to_utc_str(v, fmt)

    status_text = platform_status.get("status_color") or platform_status.get("status") or "—"

    dot_color = "#64748b"
    if status_text == "GREEN":
        dot_color = "#22c55e"
    elif status_text == "AMBER":
        dot_color = "#f59e0b"
    elif status_text == "RED":
        dot_color = "#ef4444"

    ctx = {
        "title": "Control Tower",
        "status": {
            "status": status_text,
            "dot_color": dot_color,
            "last_ingest": fmt_dt(platform_status.get("last_ingest_at") or platform_status.get("last_ingest")),
            "window": platform_status.get("window") or "24h",
            "last_updated": fmt_dt(platform_status.get("as_of") or platform_status.get("last_updated_at")),
            "contracts": platform_status.get("contracts_version") or "v1",
            "rls": platform_status.get("rls_enforced"),
            "ci": platform_status.get("ci_passing"),
        },
        "pipeline": pipeline,
        "dq": dq,
        "anomalies": anomalies,
        "incidents": incidents_kpis,
    }

    return render(request, "observability/control_tower.html", ctx)


def overview(request):
    ctx = {"title": ""}
    return render(request, "observability/project_review.html", ctx)
