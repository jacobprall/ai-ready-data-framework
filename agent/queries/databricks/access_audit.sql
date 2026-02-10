-- factor: compliant
-- requirement: access_auditing
-- requires: databricks
-- target_type: database
-- description: Checks Unity Catalog audit logs for data access tracking. Verifies that access events are being recorded.

SELECT
    COUNT(*) AS total_access_events,
    COUNT(DISTINCT action_name) AS distinct_actions,
    MIN(event_date) AS earliest_event,
    MAX(event_date) AS latest_event,
    DATEDIFF(DAY, MAX(event_date), CURRENT_DATE()) AS days_since_last_event
FROM system.access.audit
WHERE event_date >= DATEADD(DAY, -30, CURRENT_DATE())
  AND action_name IN ('getTable', 'createTable', 'deleteTable', 'commandSubmit')
