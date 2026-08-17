-- Business question:
-- Is the project ready for go-live, which SAP Activate phases are behind, and
-- which task, change-request, or data-quality records need attention?
--
-- The final readiness classification is selected directly from
-- `vw_project_readiness_summary`; its precedence logic is not duplicated here.

-- Result set 1: project-level readiness scorecard from the existing view.
SELECT
    pre_go_live_task_count,
    completed_pre_go_live_task_count,
    pre_go_live_task_completion_rate_pct,
    incomplete_critical_pre_go_live_task_count,
    blocking_critical_pre_go_live_task_count,
    open_change_request_count,
    high_critical_open_change_request_count,
    unresolved_high_critical_data_quality_issue_count,
    data_quality_resolution_rate_pct,
    data_quality_disposition_rate_pct,
    go_live_readiness_classification
FROM vw_project_readiness_summary;
-- Result set 2: phase-level task, change-request, and DQ workload.
WITH phase_order(activate_phase, phase_sequence) AS (
    VALUES
        ('discover', 1),
        ('prepare', 2),
        ('explore', 3),
        ('realize', 4),
        ('deploy', 5),
        ('run', 6)
),
task_metrics AS (
    SELECT
        activate_phase,
        COUNT(*) AS task_count,
        SUM(
            CASE
                WHEN task_status = 'completed' AND completion_percent = 100
                THEN 1
                ELSE 0
            END
        ) AS completed_task_count,
        ROUND(AVG(completion_percent), 1) AS average_completion_pct,
        SUM(
            CASE
                WHEN critical_flag = 1
                    AND (task_status <> 'completed' OR completion_percent < 100)
                THEN 1
                ELSE 0
            END
        ) AS incomplete_critical_task_count
    FROM sap_activate_project_tasks
    GROUP BY activate_phase
),
dq_metrics AS (
    SELECT
        task.activate_phase,
        SUM(
            CASE
                WHEN issue.issue_status IN ('open', 'in progress') THEN 1
                ELSE 0
            END
        ) AS unresolved_dq_issue_count,
        SUM(
            CASE
                WHEN issue.issue_status IN ('open', 'in progress')
                    AND issue.severity IN ('high', 'critical')
                THEN 1
                ELSE 0
            END
        ) AS unresolved_high_critical_dq_issue_count
    FROM data_quality_issues AS issue
    LEFT JOIN sap_activate_project_tasks AS task
        ON task.task_id = issue.related_task_id
    GROUP BY task.activate_phase
)
SELECT
    phase.activate_phase,
    COALESCE(task.task_count, 0) AS task_count,
    COALESCE(task.completed_task_count, 0) AS completed_task_count,
    task.average_completion_pct,
    COALESCE(task.incomplete_critical_task_count, 0)
        AS incomplete_critical_task_count,
    change_request.total_request_count,
    change_request.open_request_count,
    change_request.high_critical_open_request_count,
    COALESCE(dq.unresolved_dq_issue_count, 0) AS unresolved_dq_issue_count,
    COALESCE(dq.unresolved_high_critical_dq_issue_count, 0)
        AS unresolved_high_critical_dq_issue_count
FROM phase_order AS phase
LEFT JOIN task_metrics AS task
    ON task.activate_phase = phase.activate_phase
JOIN vw_change_request_phase_summary AS change_request
    ON change_request.activate_phase = phase.activate_phase
LEFT JOIN dq_metrics AS dq
    ON dq.activate_phase = phase.activate_phase
ORDER BY phase.phase_sequence;

-- Result set 3: management action register. This drill-down lists source
-- records; it does not recalculate the project readiness classification.
WITH management_actions AS (
    SELECT
        'critical task' AS action_source,
        task.task_id AS action_id,
        task.activate_phase,
        'critical' AS priority_or_severity,
        task.task_status AS action_status,
        task.task_name AS action_description
    FROM sap_activate_project_tasks AS task
    WHERE task.activate_phase <> 'run'
        AND task.critical_flag = 1
        AND (task.task_status <> 'completed' OR task.completion_percent < 100)

    UNION ALL

    SELECT
        'open change request' AS action_source,
        request.change_request_id AS action_id,
        request.activate_phase,
        request.priority AS priority_or_severity,
        request.status AS action_status,
        request.change_title AS action_description
    FROM change_requests AS request
    WHERE request.status IN ('submitted', 'under review', 'approved')

    UNION ALL

    SELECT
        'data quality risk' AS action_source,
        issue.data_quality_issue_id AS action_id,
        COALESCE(task.activate_phase, 'unassigned') AS activate_phase,
        issue.severity AS priority_or_severity,
        issue.issue_status AS action_status,
        issue.issue_description AS action_description
    FROM data_quality_issues AS issue
    LEFT JOIN sap_activate_project_tasks AS task
        ON task.task_id = issue.related_task_id
    WHERE issue.issue_status IN ('open', 'in progress', 'accepted risk')
        AND issue.severity IN ('high', 'critical')
)
SELECT
    action_source,
    action_id,
    activate_phase,
    priority_or_severity,
    action_status,
    action_description
FROM management_actions
ORDER BY
    CASE priority_or_severity
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
        ELSE 5
    END,
    action_source,
    action_id;

-- FINAL HEADLINE: compact Seed-42 validation result from the existing view.
SELECT
    pre_go_live_task_count,
    completed_pre_go_live_task_count,
    open_change_request_count,
    unresolved_high_critical_data_quality_issue_count
        AS unresolved_high_critical_dq_issue_count,
    go_live_readiness_classification
FROM vw_project_readiness_summary;
