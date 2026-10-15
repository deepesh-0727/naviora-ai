# Pilot success metrics

Use these measures for the pilot review. Unless a metric says otherwise, use the pilot's agreed start and end in UTC, with a half-open interval (`:start_utc <= timestamp < :end_utc`). Use the same hospital, departments, and dates for every comparison. The current schema does not include a hospital/tenant key, so this method assumes the pilot deployment contains only the participating hospital's data. Do not combine other hospitals' data into the report.

Targets are goals, not observed results. Report the sample size beside every rate or duration. An empty sample is **no data**, never zero minutes, zero incidents, or 100% success. Preserve the raw query output and the reporting period with each review.

## Metric definitions

| Metric | Target | Measurement |
| --- | --- | --- |
| Average patient queue wait | < 15 minutes (baseline: 45 minutes) | Average of `queue_entries.served_at - queue_entries.entered_at` in minutes for queue entries served in the period. This measures time in the queue. `appointments.actual_time - scheduled_time` is not used: the application writes `actual_time` when a visit completes, so that difference includes appointment lateness and consultation time. |
| Emergency response time | < 3 minutes | Average of `emergency_cases.arrival_time - emergency_cases.created_at` in seconds for cases that arrived in the period. Show the arrival sample size and the number of cases created in the period that remain unresolved separately. |
| Voice intent accuracy | > 85% | Manually review persisted `voice_interactions` and mark `reviewed_correct` against the user's intended task; accuracy = correct / reviewed. Report the reviewed sample size and average classifier confidence separately. |
| Patient satisfaction / NPS | NPS > 85 | Collect a separate 0–10 recommendation score in `feedback.nps_score`. NPS = percentage of promoters (9–10) minus percentage of detractors (0–6); 7–8 are passives. Keep 1–5 satisfaction ratings separate. |
| No-show rate | < 10% (baseline: 25%) | Appointments marked `no_show` divided by appointments scheduled in the period whose scheduled time has passed and were not cancelled. Include the numerator and denominator. |
| Staff adoption | > 80% | Active staff accounts with `last_login` in the period divided by active staff accounts assigned to the pilot. Staff roles currently represented by `users.role` are `doctor` and `staff`; confirm the pilot roster before interpreting the denominator. |
| Uptime | > 99.5% over the prior 30 days | Read the availability percentage and incident history from UptimeRobot for the production `/health` monitor. The application has no uptime-history SQL table; do not derive this from current health checks or service logs. Archive the monitor export with the monthly report. |
| Security incidents | 0 confirmed incidents | Review Sentry security-related events and the audit log for the period, then classify incidents under the incident-response process. SQL below surfaces failed audited requests for triage; a failed HTTP request is not automatically a security incident. Sentry events are external and do not have a database query in this application. |

## SQL measurement queries

These PostgreSQL queries use existing application tables and columns. Bind `:start_utc` and `:end_utc` as UTC timestamps. They return actual counts and measurements; they do not synthesize sample values.

### Average queue wait, median, p95, and sample size

`queue_entries.served_at` is populated when an appointment is completed. Rows with no `served_at` are still waiting and are not completed observations.

```sql
SELECT
    COUNT(*) AS sample_size,
    AVG(EXTRACT(EPOCH FROM (served_at - entered_at)) / 60.0) AS avg_minutes,
    percentile_cont(0.50) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (served_at - entered_at)) / 60.0
    ) AS p50_minutes,
    percentile_cont(0.95) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (served_at - entered_at)) / 60.0
    ) AS p95_minutes
FROM queue_entries
WHERE served_at >= :start_utc
  AND served_at < :end_utc
  AND served_at >= entered_at;
```

### Emergency response time

```sql
SELECT
    COUNT(*) FILTER (
        WHERE arrival_time >= :start_utc AND arrival_time < :end_utc
    ) AS sample_size,
    AVG(EXTRACT(EPOCH FROM (arrival_time - created_at))) FILTER (
        WHERE arrival_time >= :start_utc AND arrival_time < :end_utc
    ) AS avg_seconds,
    COUNT(*) FILTER (
        WHERE created_at >= :start_utc
          AND created_at < :end_utc
          AND arrival_time IS NULL
    ) AS created_in_period_not_yet_arrived
FROM emergency_cases
WHERE (arrival_time >= :start_utc AND arrival_time < :end_utc)
   OR (created_at >= :start_utc AND created_at < :end_utc AND arrival_time IS NULL);
```

The average covers responses completed during the period, including cases created before it. The unresolved count covers only cases created during the period. Those are separate cohorts and must not be combined into one denominator.

### Voice intent accuracy and interactions

Voice interactions are persisted in `voice_interactions`. Confidence is not accuracy; only manually reviewed records with `reviewed_correct` set contribute to accuracy:

```sql
SELECT
    COUNT(*) AS reviewed_sample_size,
    COUNT(*) FILTER (WHERE reviewed_correct = TRUE) AS correct,
    COUNT(*) FILTER (WHERE reviewed_correct = FALSE) AS incorrect,
    COUNT(*) FILTER (WHERE reviewed_correct = TRUE)::decimal
        / NULLIF(COUNT(*), 0) AS accuracy,
    AVG(confidence) AS avg_confidence
FROM voice_interactions
WHERE created_at >= :start_utc
  AND created_at < :end_utc
  AND reviewed_correct IS NOT NULL;
```

Select an unreviewed sample for labeling and have an authorized reviewer compare predicted `intent` with the intended task. Restrict transcript access and mark the review fields after evaluation.

```sql
SELECT id, intent, confidence, transcript
FROM voice_interactions
WHERE created_at >= :start_utc
  AND created_at < :end_utc
  AND reviewed_correct IS NULL
ORDER BY id;
```

The persisted transcript column is encrypted at rest and decrypted by the ORM for authorized application use. No reviewed rows means accuracy is unavailable, not zero.

### Patient satisfaction and NPS

```sql
SELECT
    COUNT(*) AS responses,
    COUNT(*) FILTER (WHERE rating >= 4) AS favorable_responses,
    100.0 * COUNT(*) FILTER (WHERE rating >= 4) / NULLIF(COUNT(*), 0)
        AS favorable_percent,
    AVG(rating) AS average_rating
FROM feedback
WHERE created_at >= :start_utc
  AND created_at < :end_utc;
```

This reports the existing 1–5-star feedback measure, not NPS. Do not relabel it as NPS.

Query the NPS measure separately:

```sql
SELECT
    COUNT(*) AS responses,
    COUNT(*) FILTER (WHERE nps_score >= 9) AS promoters,
    COUNT(*) FILTER (WHERE nps_score BETWEEN 7 AND 8) AS passives,
    COUNT(*) FILTER (WHERE nps_score <= 6) AS detractors,
    100.0 * (
        COUNT(*) FILTER (WHERE nps_score >= 9)
        - COUNT(*) FILTER (WHERE nps_score <= 6)
    ) / NULLIF(COUNT(*), 0) AS nps
FROM feedback
WHERE created_at >= :start_utc
  AND created_at < :end_utc
  AND nps_score IS NOT NULL;
```

### No-show rate

```sql
SELECT
    COUNT(*) AS eligible_appointments,
    COUNT(*) FILTER (WHERE status = 'no_show') AS no_shows,
    COUNT(*) FILTER (WHERE status = 'no_show')::decimal
        / NULLIF(COUNT(*), 0) AS rate
FROM appointments
WHERE scheduled_time >= :start_utc
  AND scheduled_time < :end_utc
  AND scheduled_time < CURRENT_TIMESTAMP
  AND status <> 'cancelled';
```

The denominator excludes cancelled and future appointments. Review whether rescheduled appointments should be excluded as well; the current appointment model does not preserve a reschedule history.

### Daily and weekly staff adoption

Run with `:start_utc` / `:end_utc` set to the daily reporting window or the seven-day reporting window. The denominator is active doctor/staff accounts because no separate pilot roster table exists yet.

```sql
SELECT
    COUNT(*) AS eligible_staff,
    COUNT(*) FILTER (
        WHERE last_login >= :start_utc AND last_login < :end_utc
    ) AS active_staff,
    COUNT(*) FILTER (
        WHERE last_login >= :start_utc AND last_login < :end_utc
    )::decimal / NULLIF(COUNT(*), 0) AS adoption_rate
FROM users
WHERE is_active = TRUE
  AND role IN ('doctor', 'staff');
```

Use the hospital's agreed timezone to choose local-day boundaries, then convert those boundaries to UTC before binding. `last_login` measures account use, not completion of a clinical workflow.

### Audit-log triage for security review

```sql
SELECT
    COUNT(*) AS failed_audited_requests,
    COUNT(DISTINCT user_id) AS affected_users
FROM audit_logs
WHERE created_at >= :start_utc
  AND created_at < :end_utc
  AND status ~ '^[45][0-9][0-9]$';
```

This is a triage queue, not a confirmed-incident count. Review the associated audit rows and Sentry events with the security owner; record confirmed incident count and disposition in the pilot incident register. `audit_logs` records selected audited API requests, not all security telemetry.

## Admin metrics endpoint

Administrators can retrieve the computed metrics from `GET /api/v1/admin/pilot/metrics`. Optional ISO-8601 `start` and `end` query parameters select a half-open UTC period; when omitted, the endpoint uses the preceding 30 days. Supplying `start >= end` returns `422`.

The endpoint returns database-derived queue wait percentiles, emergency response, no-show rate, voice volume/confidence/review accuracy, NPS and 1–5 satisfaction, and daily/weekly staff login counts. It returns `null` for a statistic with no observations. Uptime is reported as `null` with source `manual_uptimerobot_review`; include the independently exported monitor result in the pilot report rather than treating null as zero or healthy.

## Baseline and reporting rules

- Treat the 45-minute wait and 25% no-show figures as supplied baseline claims until the hospital validates their source, definitions, cohort, and date range. Do not compare a newly defined measure against an incompatible baseline.
- Record period start/end, timezone, query run time, source system, sample size, exclusions, and reviewer for every reported value.
- Keep department breakdowns alongside hospital-wide aggregates so a busy department cannot hide a failing one.
- Do not publish patient-level rows in pilot reports. Aggregate results and keep any manual voice-review copy access-controlled and de-identified.
- Mark voice accuracy unavailable when no interactions have been reviewed. Mark NPS unavailable when no 0–10 responses exist. Uptime remains an external UptimeRobot measure and has no application SQL query. No placeholder percentages should appear in dashboards or reports.
