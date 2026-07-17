USE GamingIntelligenceDB;
GO

/* ============================================================
   Gaming Machine Health & Reliability Analytics
   ============================================================ */


/* ============================================================
   Query 1: Overall machine health summary
   ============================================================ */

SELECT
    COUNT(*) AS total_machines,
    SUM(total_event_count) AS total_events,
    SUM(unplanned_event_count) AS total_unplanned_events,
    SUM(critical_event_count) AS total_critical_events,
    SUM(total_downtime_minutes) AS total_downtime_minutes,

    CAST(
        AVG(
            CAST(
                total_downtime_minutes
                AS DECIMAL(18,2)
            )
        )
        AS DECIMAL(18,2)
    ) AS average_downtime_per_machine,

    CAST(
        AVG(annual_availability_pct)
        AS DECIMAL(10,4)
    ) AS average_availability_pct,

    SUM(investigation_count)
        AS total_investigations

FROM dbo.vw_machine_health;
GO


/* ============================================================
   Query 2: Machine health ranking
   ============================================================ */

SELECT
    machine_id,
    location_name,
    manufacturer,
    game_title,
    software_version,
    total_event_count,
    unplanned_event_count,
    critical_event_count,
    total_downtime_minutes,
    average_downtime_minutes,
    investigation_count,
    annual_availability_pct,

    RANK() OVER
    (
        ORDER BY total_downtime_minutes DESC
    ) AS downtime_rank,

    DENSE_RANK() OVER
    (
        ORDER BY critical_event_count DESC
    ) AS critical_event_rank,

    NTILE(4) OVER
    (
        ORDER BY annual_availability_pct ASC
    ) AS health_risk_quartile

FROM dbo.vw_machine_health

ORDER BY
    downtime_rank;
GO


/* ============================================================
   Query 3: Machines with highest downtime
   ============================================================ */

SELECT TOP 20
    machine_id,
    location_id,
    location_name,
    manufacturer,
    game_title,
    game_category,
    software_version,
    total_event_count,
    unplanned_event_count,
    critical_event_count,
    total_downtime_minutes,
    annual_availability_pct

FROM dbo.vw_machine_health

ORDER BY
    total_downtime_minutes DESC;
GO


/* ============================================================
   Query 4: Machines with most critical failures
   ============================================================ */

SELECT TOP 20
    machine_id,
    location_name,
    manufacturer,
    game_title,
    software_version,
    total_event_count,
    critical_event_count,
    investigation_count,
    total_downtime_minutes,
    annual_availability_pct

FROM dbo.vw_machine_health

WHERE
    critical_event_count > 0

ORDER BY
    critical_event_count DESC,
    total_downtime_minutes DESC;
GO


/* ============================================================
   Query 5: Event distribution by type and severity
   ============================================================ */

SELECT
    event_type,
    severity,
    COUNT_BIG(*) AS event_count,
    SUM(downtime_minutes) AS total_downtime_minutes,

    CAST(
        AVG(
            CAST(
                downtime_minutes
                AS DECIMAL(18,2)
            )
        )
        AS DECIMAL(18,2)
    ) AS average_downtime_minutes,

    SUM(
        CAST(
            requires_investigation
            AS INT
        )
    ) AS investigation_count

FROM dbo.fact_machine_event

GROUP BY
    event_type,
    severity

ORDER BY
    total_downtime_minutes DESC;
GO


/* ============================================================
   Query 6: Root-cause analysis by event type
   ============================================================ */

SELECT
    event_type,
    COUNT_BIG(*) AS event_count,

    SUM(
        CASE
            WHEN planned_event_flag = 0
            THEN 1
            ELSE 0
        END
    ) AS unplanned_event_count,

    SUM(
        CASE
            WHEN severity = 'Critical'
            THEN 1
            ELSE 0
        END
    ) AS critical_event_count,

    SUM(downtime_minutes)
        AS total_downtime_minutes,

    CAST(
        100.0 * COUNT_BIG(*)
        / NULLIF(
            SUM(COUNT_BIG(*)) OVER (),
            0
        )
        AS DECIMAL(10,2)
    ) AS event_share_pct,

    CAST(
        100.0 * SUM(downtime_minutes)
        / NULLIF(
            SUM(SUM(downtime_minutes)) OVER (),
            0
        )
        AS DECIMAL(10,2)
    ) AS downtime_share_pct

FROM dbo.fact_machine_event

GROUP BY
    event_type

ORDER BY
    total_downtime_minutes DESC;
GO


/* ============================================================
   Query 7: Mean Time To Repair (MTTR) by machine
   Assumption: downtime_minutes represents repair duration.
   ============================================================ */

SELECT
    machine_id,
    COUNT_BIG(*) AS repair_event_count,
    SUM(downtime_minutes) AS total_repair_minutes,

    CAST(
        AVG(
            CAST(
                downtime_minutes
                AS DECIMAL(18,2)
            )
        )
        AS DECIMAL(18,2)
    ) AS mttr_minutes

FROM dbo.fact_machine_event

WHERE
    planned_event_flag = 0
    AND downtime_minutes > 0

GROUP BY
    machine_id

ORDER BY
    mttr_minutes DESC;
GO


/* ============================================================
   Query 8: Mean Time Between Failures (MTBF) by machine
   Calculated from elapsed minutes between unplanned events.
   ============================================================ */

WITH failure_events AS
(
    SELECT
        machine_id,
        event_timestamp,

        LAG(event_timestamp) OVER
        (
            PARTITION BY machine_id
            ORDER BY event_timestamp
        ) AS previous_failure_timestamp

    FROM dbo.fact_machine_event

    WHERE
        planned_event_flag = 0
),

failure_intervals AS
(
    SELECT
        machine_id,

        DATEDIFF(
            MINUTE,
            previous_failure_timestamp,
            event_timestamp
        ) AS minutes_between_failures

    FROM failure_events

    WHERE
        previous_failure_timestamp IS NOT NULL
)

SELECT
    machine_id,
    COUNT(*) AS measured_failure_intervals,

    CAST(
        AVG(
            CAST(
                minutes_between_failures
                AS DECIMAL(18,2)
            )
        )
        AS DECIMAL(18,2)
    ) AS mtbf_minutes,

    CAST(
        AVG(
            CAST(
                minutes_between_failures
                AS DECIMAL(18,2)
            )
        ) / 60.0
        AS DECIMAL(18,2)
    ) AS mtbf_hours

FROM failure_intervals

GROUP BY
    machine_id

ORDER BY
    mtbf_minutes ASC;
GO


/* ============================================================
   Query 9: MTTR and MTBF combined
   ============================================================ */

WITH mttr AS
(
    SELECT
        machine_id,

        CAST(
            AVG(
                CAST(
                    downtime_minutes
                    AS DECIMAL(18,2)
                )
            )
            AS DECIMAL(18,2)
        ) AS mttr_minutes

    FROM dbo.fact_machine_event

    WHERE
        planned_event_flag = 0
        AND downtime_minutes > 0

    GROUP BY
        machine_id
),

failure_events AS
(
    SELECT
        machine_id,
        event_timestamp,

        LAG(event_timestamp) OVER
        (
            PARTITION BY machine_id
            ORDER BY event_timestamp
        ) AS previous_failure_timestamp

    FROM dbo.fact_machine_event

    WHERE
        planned_event_flag = 0
),

mtbf AS
(
    SELECT
        machine_id,

        CAST(
            AVG(
                CAST(
                    DATEDIFF(
                        MINUTE,
                        previous_failure_timestamp,
                        event_timestamp
                    )
                    AS DECIMAL(18,2)
                )
            )
            AS DECIMAL(18,2)
        ) AS mtbf_minutes

    FROM failure_events

    WHERE
        previous_failure_timestamp IS NOT NULL

    GROUP BY
        machine_id
)

SELECT
    h.machine_id,
    h.location_name,
    h.manufacturer,
    h.game_title,
    h.software_version,
    h.total_event_count,
    h.total_downtime_minutes,
    m1.mttr_minutes,
    m2.mtbf_minutes,

    CAST(
        m2.mtbf_minutes
        / NULLIF(
            m2.mtbf_minutes
            + m1.mttr_minutes,
            0
        )
        AS DECIMAL(10,4)
    ) AS reliability_availability_ratio

FROM dbo.vw_machine_health AS h

LEFT JOIN mttr AS m1
    ON h.machine_id = m1.machine_id

LEFT JOIN mtbf AS m2
    ON h.machine_id = m2.machine_id

ORDER BY
    reliability_availability_ratio ASC;
GO


/* ============================================================
   Query 10: Manufacturer reliability comparison
   ============================================================ */

SELECT
    manufacturer,
    COUNT(*) AS machine_count,
    SUM(total_event_count) AS total_events,
    SUM(unplanned_event_count) AS unplanned_events,
    SUM(critical_event_count) AS critical_events,
    SUM(total_downtime_minutes) AS total_downtime_minutes,

    CAST(
        SUM(total_downtime_minutes) * 1.0
        / NULLIF(COUNT(*), 0)
        AS DECIMAL(18,2)
    ) AS downtime_per_machine,

    CAST(
        SUM(total_event_count) * 1.0
        / NULLIF(COUNT(*), 0)
        AS DECIMAL(18,2)
    ) AS events_per_machine,

    CAST(
        AVG(annual_availability_pct)
        AS DECIMAL(10,4)
    ) AS average_availability_pct

FROM dbo.vw_machine_health

GROUP BY
    manufacturer

ORDER BY
    average_availability_pct ASC;
GO


/* ============================================================
   Query 11: Software version reliability comparison
   ============================================================ */

SELECT
    software_version,
    COUNT(*) AS machine_count,
    SUM(total_event_count) AS total_events,
    SUM(unplanned_event_count) AS unplanned_events,
    SUM(critical_event_count) AS critical_events,
    SUM(total_downtime_minutes) AS total_downtime_minutes,

    CAST(
        SUM(total_downtime_minutes) * 1.0
        / NULLIF(COUNT(*), 0)
        AS DECIMAL(18,2)
    ) AS downtime_per_machine,

    CAST(
        AVG(annual_availability_pct)
        AS DECIMAL(10,4)
    ) AS average_availability_pct

FROM dbo.vw_machine_health

GROUP BY
    software_version

ORDER BY
    total_downtime_minutes DESC;
GO


/* ============================================================
   Query 12: Daily downtime trend
   ============================================================ */

WITH daily_downtime AS
(
    SELECT
        event_date,
        COUNT_BIG(*) AS event_count,
        SUM(downtime_minutes) AS downtime_minutes,

        SUM(
            CASE
                WHEN severity = 'Critical'
                THEN 1
                ELSE 0
            END
        ) AS critical_events

    FROM dbo.fact_machine_event

    GROUP BY
        event_date
)

SELECT
    event_date,
    event_count,
    downtime_minutes,
    critical_events,

    CAST(
        AVG(
            CAST(
                downtime_minutes
                AS DECIMAL(18,2)
            )
        ) OVER
        (
            ORDER BY event_date
            ROWS BETWEEN 6 PRECEDING
            AND CURRENT ROW
        )
        AS DECIMAL(18,2)
    ) AS seven_day_downtime_moving_average,

    LAG(downtime_minutes) OVER
    (
        ORDER BY event_date
    ) AS previous_day_downtime,

    downtime_minutes
    - LAG(downtime_minutes) OVER
    (
        ORDER BY event_date
    ) AS downtime_change

FROM daily_downtime

ORDER BY
    event_date;
GO


/* ============================================================
   Query 13: Repeat-failure machines
   ============================================================ */

WITH repeat_failures AS
(
    SELECT
        machine_id,
        event_type,
        COUNT(*) AS repeated_event_count,
        SUM(downtime_minutes) AS event_type_downtime,

        ROW_NUMBER() OVER
        (
            PARTITION BY machine_id
            ORDER BY
                COUNT(*) DESC,
                SUM(downtime_minutes) DESC
        ) AS event_rank

    FROM dbo.fact_machine_event

    WHERE
        planned_event_flag = 0

    GROUP BY
        machine_id,
        event_type
)

SELECT
    r.machine_id,
    h.location_name,
    h.manufacturer,
    h.game_title,
    r.event_type AS most_common_failure,
    r.repeated_event_count,
    r.event_type_downtime,
    h.total_event_count,
    h.total_downtime_minutes

FROM repeat_failures AS r

INNER JOIN dbo.vw_machine_health AS h
    ON r.machine_id = h.machine_id

WHERE
    r.event_rank = 1
    AND r.repeated_event_count >= 5

ORDER BY
    r.repeated_event_count DESC,
    r.event_type_downtime DESC;
GO


/* ============================================================
   Query 14: Preventive-maintenance priority score
   ============================================================ */

WITH machine_scores AS
(
    SELECT
        machine_id,
        location_name,
        manufacturer,
        game_title,
        software_version,
        total_event_count,
        unplanned_event_count,
        critical_event_count,
        total_downtime_minutes,
        investigation_count,
        annual_availability_pct,

        NTILE(5) OVER
        (
            ORDER BY total_downtime_minutes DESC
        ) AS downtime_score,

        NTILE(5) OVER
        (
            ORDER BY critical_event_count DESC
        ) AS critical_score,

        NTILE(5) OVER
        (
            ORDER BY unplanned_event_count DESC
        ) AS failure_score,

        NTILE(5) OVER
        (
            ORDER BY annual_availability_pct ASC
        ) AS availability_risk_score

    FROM dbo.vw_machine_health
)

SELECT
    machine_id,
    location_name,
    manufacturer,
    game_title,
    software_version,
    total_event_count,
    unplanned_event_count,
    critical_event_count,
    total_downtime_minutes,
    annual_availability_pct,
    downtime_score,
    critical_score,
    failure_score,
    availability_risk_score,

    downtime_score
    + critical_score
    + failure_score
    + availability_risk_score
        AS maintenance_priority_score,

    CASE
        WHEN
            downtime_score
            + critical_score
            + failure_score
            + availability_risk_score >= 17
        THEN 'Immediate Maintenance'

        WHEN
            downtime_score
            + critical_score
            + failure_score
            + availability_risk_score >= 13
        THEN 'High Priority'

        WHEN
            downtime_score
            + critical_score
            + failure_score
            + availability_risk_score >= 9
        THEN 'Medium Priority'

        ELSE 'Routine Monitoring'
    END AS maintenance_priority

FROM machine_scores

ORDER BY
    maintenance_priority_score DESC,
    total_downtime_minutes DESC;
GO


/* ============================================================
   Query 15: Replacement candidates
   ============================================================ */

WITH machine_revenue AS
(
    SELECT
        machine_id,
        SUM(net_gaming_revenue)
            AS net_gaming_revenue,
        SUM(session_count)
            AS total_sessions

    FROM dbo.vw_machine_daily_performance

    GROUP BY
        machine_id
),

combined_metrics AS
(
    SELECT
        h.machine_id,
        h.location_name,
        h.manufacturer,
        h.game_title,
        h.software_version,
        h.total_event_count,
        h.critical_event_count,
        h.total_downtime_minutes,
        h.annual_availability_pct,
        ISNULL(r.net_gaming_revenue, 0)
            AS net_gaming_revenue,
        ISNULL(r.total_sessions, 0)
            AS total_sessions,

        PERCENT_RANK() OVER
        (
            ORDER BY ISNULL(r.net_gaming_revenue, 0)
        ) AS revenue_percentile,

        PERCENT_RANK() OVER
        (
            ORDER BY h.total_downtime_minutes
        ) AS downtime_percentile

    FROM dbo.vw_machine_health AS h

    LEFT JOIN machine_revenue AS r
        ON h.machine_id = r.machine_id
)

SELECT
    machine_id,
    location_name,
    manufacturer,
    game_title,
    software_version,
    total_sessions,
    net_gaming_revenue,
    total_event_count,
    critical_event_count,
    total_downtime_minutes,
    annual_availability_pct,

    CASE
        WHEN revenue_percentile <= 0.25
             AND downtime_percentile >= 0.75
        THEN 'Replacement Candidate'

        WHEN revenue_percentile <= 0.40
             AND downtime_percentile >= 0.60
        THEN 'Review for Replacement'

        ELSE 'Retain'
    END AS replacement_recommendation

FROM combined_metrics

ORDER BY
    CASE
        WHEN revenue_percentile <= 0.25
             AND downtime_percentile >= 0.75
        THEN 1

        WHEN revenue_percentile <= 0.40
             AND downtime_percentile >= 0.60
        THEN 2

        ELSE 3
    END,
    total_downtime_minutes DESC;
GO


/* ============================================================
   Query 16: Power BI-ready machine health dataset
   ============================================================ */

WITH latest_event AS
(
    SELECT
        machine_id,
        event_timestamp,
        event_type,
        severity,

        ROW_NUMBER() OVER
        (
            PARTITION BY machine_id
            ORDER BY event_timestamp DESC
        ) AS latest_event_rank

    FROM dbo.fact_machine_event
),

machine_failure_metrics AS
(
    SELECT
        machine_id,

        SUM(
            CASE
                WHEN planned_event_flag = 0
                THEN 1
                ELSE 0
            END
        ) AS unplanned_failure_count,

        SUM(
            CASE
                WHEN severity = 'Critical'
                THEN 1
                ELSE 0
            END
        ) AS critical_failure_count,

        SUM(downtime_minutes)
            AS total_downtime_minutes

    FROM dbo.fact_machine_event

    GROUP BY
        machine_id
)

SELECT
    h.machine_id,
    h.location_id,
    h.location_name,
    h.manufacturer,
    h.game_title,
    h.game_category,
    h.software_version,
    h.machine_status,
    h.total_event_count,
    h.unplanned_event_count,
    h.critical_event_count,
    h.total_downtime_minutes,
    h.average_downtime_minutes,
    h.investigation_count,
    h.annual_availability_pct,
    l.event_timestamp AS latest_event_timestamp,
    l.event_type AS latest_event_type,
    l.severity AS latest_event_severity,

    CASE
        WHEN h.critical_event_count >= 8
             OR h.total_downtime_minutes >= 5000
        THEN 'High Risk'

        WHEN h.critical_event_count >= 4
             OR h.total_downtime_minutes >= 3500
        THEN 'Medium Risk'

        ELSE 'Low Risk'
    END AS health_risk_level,

    CASE
        WHEN h.total_downtime_minutes >= 5000
        THEN 1
        ELSE 0
    END AS maintenance_required_flag

FROM dbo.vw_machine_health AS h

LEFT JOIN latest_event AS l
    ON h.machine_id = l.machine_id
    AND l.latest_event_rank = 1

LEFT JOIN machine_failure_metrics AS f
    ON h.machine_id = f.machine_id;
GO