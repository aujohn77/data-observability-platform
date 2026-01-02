# Data Contracts (Minimal)

## 1. Observation Contract
An observation represents **one metric value** for **one station** at a **specific time**.

**Grain**
- `(station_id, metric_id, observed_at)`

---

## 2. Canonical Metrics & Units
All metrics are defined centrally and normalized to **canonical units**.

| Metric Code    | Description          | Unit | Type    | Expected Range |
|---|---|---:|---|---|
| temp_air_c     | Air temperature      | °C   | numeric | -10 → 55 |
| rain_mm        | Rainfall             | mm   | numeric | 0 → 500 |
| wind_speed_ms  | Wind speed           | m/s  | numeric | 0 → 60 |
| wind_gust_ms   | Wind gust speed      | m/s  | numeric | 0 → 80 |
| humidity_pct   | Relative humidity    | %    | numeric | 0 → 100 |
| pressure_hpa   | Atmospheric pressure | hPa  | numeric | 850 → 1100 |

**Rules**
- Metric codes are **stable** and never renamed.
- Units are normalized during transformation.
- Raw source units are preserved for auditability.

---

## 3. Time & Lateness
- `observed_at`: when the measurement occurred
- `ingested_at`: when the platform stored the record

**Allowed lateness**
- 24 hours

Late data is accepted and flagged.

---

## 4. Identity & Validation

**Identity**
- `(source, station_external_id, observed_at, metric_code)`

**Validation rules**
- Ingestion is idempotent.
- Exactly one of `value_num` or `value_text` must be present.
- Out-of-range values generate warnings, not failures.
