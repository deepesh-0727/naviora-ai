# Pilot success metrics

Use these measures for the pilot review. Unless a metric says otherwise, use the pilot's agreed start and end in UTC, with a half-open interval (`:start_utc <= timestamp < :end_utc`). Use the same hospital, departments, and dates for every comparison. The current schema does not include a hospital/tenant key, so this method assumes the pilot deployment contains only the participating hospital's data. Do not combine other hospitals' data into the report.

Targets are goals, not observed results. Report the sample size beside every rate or duration. An empty sample is **no data**, never zero minutes, zero incidents, or 100% success. Preserve the raw query output and the reporting period with each review.

## Metric definitions

| Metric | Target | Measurement |
| --- | --- | --- |
| Average patient queue wait | < 15 minutes (baseline: 45 minutes) | Average of `queue_entries.served_at - queue_entries.entered_at` in minutes for queue entries served in the period. This measures time in the queue. `appointments.actual_time - scheduled_time` is not used: the application writes `actual_time` when a visit completes, so that difference includes appointment lateness and consultation time. |
| Emergency response time | < 3 minutes | Average of `emergency_cases.arrival_time - emergency_cases.created_at` in seconds for cases that arrived in the period. Show the arrival sample size and the number of cases created in the period that remain unresolved separately. |
| Voice intent accuracy | > 85% | Manually label a documented sample of voice interactions as correct/incorrect against the user's intended task; accuracy = correct / reviewed. `conversations` stores the predicted intent and confidence but no verified label, so SQL alone cannot calculate accuracy. The sample query below locates review candidates; record the labels in the pilot review worksheet until a reviewed-label table exists. |
| Patient satisfaction | > 85% favorable ratings (requested “NPS” target) | Favorable share = feedback ratings of 4 or 5 divided by all submitted 1–5 ratings in the period. This is not NPS. The API restricts ratings to 1–5, while NPS requires a 0–10 recommendation question; report this as satisfaction until the survey and schema collect the NPS scale. |
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

### Voice interactions and manual review candidates

Existing aggregate data (counts and confidence) can be queried, but confidence is not accuracy:

```sql
SELECT
    COUNT(*) AS interaction_count,
    AVG(confidence) AS avg_confidence
FROM conversations
WHERE created_at >= :start_utc
  AND created_at < :end_utc
  AND is_voice = TRUE;
```

For manual accuracy review, select a reproducible sample from the same period and have a reviewer compare each predicted `intent` with the intended task. Restrict access to transcript text and remove identifying details from the review copy.

```sql
SELECT id, intent, confidence, query
FROM conversations
WHERE created_at >= :start_utc
  AND created_at < :end_utc
  AND is_voice = TRUE
ORDER BY id;
```

The schema has no review-label column and the current voice orchestration path does not persist `ConversationHistory` rows. If this query returns no records, accuracy is not measurable from production data; do not report an accuracy percentage until voice interactions are persisted and reviewed labels are stored or documented.

### Patient satisfaction (favorable rating share)

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

## Baseline and reporting rules

- Treat the 45-minute wait and 25% no-show figures as supplied baseline claims until the hospital validates their source, definitions, cohort, and date range. Do not compare a newly defined measure against an incompatible baseline.
- Record period start/end, timezone, query run time, source system, sample size, exclusions, and reviewer for every reported value.
- Keep department breakdowns alongside hospital-wide aggregates so a busy department cannot hide a failing one.
- Do not publish patient-level rows in pilot reports. Aggregate results and keep any manual voice-review copy access-controlled and de-identified.
- Mark voice accuracy, actual NPS, and database-backed uptime as unavailable until their missing data sources are implemented. No placeholder percentages should appear in dashboards or reports.
