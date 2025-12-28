import os, sys, traceback
from datetime import datetime, timezone
import requests
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["OBS_DATABASE_URL"]
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

METRICS = {
    "temperature_2m":          ("temperature_2m",        "degrees Celsius",     "num"),
    "relative_humidity_2m":    ("relative_humidity_2m",  "percent",             "num"),
    "surface_pressure":        ("surface_pressure",      "hectopascals",        "num"),
    "wind_speed_10m":          ("wind_speed_10m",        "metres per second",   "num"),
    "wind_direction_10m":      ("wind_direction_10m",    "degrees",             "num"),
    "wind_gusts_10m":          ("wind_gusts_10m",        "metres per second",   "num"),
    "precipitation":           ("precipitation",         "millimetres",         "num"),
    "weather_code":            ("weather_code",          "dimensionless code",  "num"),
}

def start_job(cur, job_name: str) -> str:
    cur.execute("""
      insert into public.ops_job_run (job_name, status, started_at)
      values (%s, 'started', now())
      returning run_id
    """, (job_name,))
    return cur.fetchone()[0]

def finish_job(cur, run_id: str, status: str, error_message: str = None,
               rows_inserted: int = 0, rows_updated: int = 0, rows_deduped: int = 0):
    cur.execute("""
      update public.ops_job_run
      set status = %s,
          ended_at = now(),
          error_message = %s,
          rows_inserted = %s,
          rows_updated  = %s,
          rows_deduped  = %s
      where run_id = %s
    """, (status, error_message, rows_inserted, rows_updated, rows_deduped, run_id))

def fetch_open_meteo(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(v[0] for v in METRICS.values()),
        "timezone": "UTC",
        "past_days": 0,
        "forecast_days": 1,
    }
    r = requests.get(OPEN_METEO_URL, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def pick_hour_index(data: dict) -> int:
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return -1

    now = datetime.now(timezone.utc)

    for i, t in enumerate(times):
        dt = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
        if dt >= now:
            return i

    return len(times) - 1  # fallback

def build_rows_from_open_meteo(station_external_id: str, data: dict) -> list[dict]:
    """
    Store a *payload slice per row*:
    - Each row gets only what is relevant for that metric at that observed_at
    - No full API response, no full hourly series
    """
    rows = []
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return rows

    i = pick_hour_index(data)
    if i < 0:
        return rows

    chosen_time = times[i]
    observed_at = datetime.fromisoformat(chosen_time).replace(tzinfo=timezone.utc)

    # Stable provenance (small and useful)
    provider = "OpenMeteo"
    lat = data.get("latitude")
    lon = data.get("longitude")
    hourly_units = data.get("hourly_units", {}) or {}

    for metric_code, (field, unit, kind) in METRICS.items():
        series = hourly.get(field)
        if not series or i >= len(series):
            continue

        v = series[i]
        if v is None:
            continue

        # Per-row payload slice (only what you need to trace/debug THIS metric at THIS time)
        source_payload = {
            "provider": provider,
            "station_external_id": str(station_external_id),
            "latitude": lat,
            "longitude": lon,
            "observed_at": chosen_time,          # ISO string
            "field": field,                      # upstream field name
            "metric_code": metric_code,          # your internal metric code
            "unit": hourly_units.get(field, unit) or unit,
            "value": v,                          # raw value as returned
        }

        row = {
            "source": provider,
            "station_external_id": str(station_external_id),
            "observed_at": observed_at,
            "metric_code": metric_code,
            "unit": unit,            # keep your canonical unit column
            "quality_flag": None,
            "source_payload": source_payload,
        }

        if kind == "num":
            row["value_num"] = float(v)
            row["value_text"] = None
        else:
            row["value_num"] = None
            row["value_text"] = str(v)

        rows.append(row)

    return rows

def upsert_raw(cur, run_id: str, rows: list[dict]) -> tuple[int, int, int]:
    inserted = updated = deduped = 0

    for row in rows:
        cur.execute("""
          insert into public.raw_observations
            (source, station_external_id, observed_at, metric_code,
             value_num, value_text, unit, quality_flag, source_payload,
             ingested_at, ingest_run_id)
          values
            (%s, %s, %s, %s,
             %s, %s, %s, %s, %s,
             now(), %s)
          on conflict (source, station_external_id, observed_at, metric_code)
          do update set
             value_num      = excluded.value_num,
             value_text     = excluded.value_text,
             unit           = excluded.unit,
             quality_flag   = excluded.quality_flag,
             source_payload = excluded.source_payload,
             ingested_at    = now(),
             ingest_run_id  = excluded.ingest_run_id
          returning (xmax = 0) as inserted_row
        """, (
            row["source"],
            row["station_external_id"],
            row["observed_at"],
            row["metric_code"],
            row.get("value_num"),
            row.get("value_text"),
            row["unit"],
            row.get("quality_flag"),
            Json(row["source_payload"]),
            run_id
        ))
        was_insert = cur.fetchone()[0]
        if was_insert:
            inserted += 1
        else:
            updated += 1

    return inserted, updated, deduped

def main():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    run_id = None

    try:
        with conn.cursor() as cur:
            run_id = start_job(cur, "ingest_openmeteo_all_stations")
        conn.commit()

        total_ins = total_upd = total_ded = 0

        with conn.cursor() as cur:
            cur.execute("""
              select station_external_id, lat, lon
              from public.dim_station
              where is_current = true
                and lat is not null
                and lon is not null
                and is_smoketest = false;
            """)
            stations = cur.fetchall()

        for station_external_id, lat, lon in stations:
            data = fetch_open_meteo(float(lat), float(lon))
            rows = build_rows_from_open_meteo(station_external_id, data)

            with conn.cursor() as cur:
                ins, upd, ded = upsert_raw(cur, run_id, rows)
                total_ins += ins
                total_upd += upd
                total_ded += ded

        with conn.cursor() as cur:
            finish_job(cur, run_id, "succeeded",
                       rows_inserted=total_ins, rows_updated=total_upd, rows_deduped=total_ded)
        conn.commit()
        print("OK")
        return 0

    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        tb = traceback.format_exc(limit=5)
        try:
            if conn and run_id:
                with conn.cursor() as cur:
                    finish_job(cur, run_id, "failed", error_message=(err + "\n" + tb)[:4000])
                conn.commit()
        except Exception:
            pass
        print(err, file=sys.stderr)
        print(tb, file=sys.stderr)
        return 1

    finally:
        conn.close()

if __name__ == "__main__":
    raise SystemExit(main())
