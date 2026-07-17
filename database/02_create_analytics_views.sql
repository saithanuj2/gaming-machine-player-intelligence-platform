USE GamingIntelligenceDB;
GO

/* ============================================================
   Drop existing analytics views
   ============================================================ */

DROP VIEW IF EXISTS dbo.vw_executive_kpis;
GO

DROP VIEW IF EXISTS dbo.vw_location_performance;
GO

DROP VIEW IF EXISTS dbo.vw_machine_daily_performance;
GO

DROP VIEW IF EXISTS dbo.vw_machine_health;
GO

DROP VIEW IF EXISTS dbo.vw_player_summary;
GO


/* ============================================================
   View 1: Daily machine performance
   ============================================================ */

CREATE VIEW dbo.vw_machine_daily_performance
AS

WITH transaction_summary AS
(
    SELECT
        CAST(t.transaction_timestamp AS DATE) AS activity_date,
        t.machine_id,
        t.location_id,
        COUNT_BIG(*) AS transaction_count,
        COUNT(DISTINCT t.session_id) AS session_count,
        COUNT(DISTINCT t.player_id) AS unique_player_count,
        SUM(t.wager_amount) AS total_wager,
        SUM(t.payout_amount) AS total_payout,
        SUM(t.jackpot_amount) AS jackpot_amount,
        SUM(t.net_gaming_revenue) AS net_gaming_revenue
    FROM dbo.fact_gaming_transaction AS t
    GROUP BY
        CAST(t.transaction_timestamp AS DATE),
        t.machine_id,
        t.location_id
),

event_summary AS
(
    SELECT
        e.event_date AS activity_date,
        e.machine_id,
        e.location_id,
        COUNT_BIG(*) AS event_count,
        SUM(e.downtime_minutes) AS downtime_minutes,

        SUM(
            CASE
                WHEN e.severity = 'Critical'
                THEN 1
                ELSE 0
            END
        ) AS critical_event_count,

        SUM(
            CAST(
                e.requires_investigation
                AS INT
            )
        ) AS investigation_count

    FROM dbo.fact_machine_event AS e

    GROUP BY
        e.event_date,
        e.machine_id,
        e.location_id
)

SELECT
    t.activity_date,
    t.machine_id,
    t.location_id,
    m.manufacturer,
    m.game_title,
    m.game_category,
    m.software_version,
    t.transaction_count,
    t.session_count,
    t.unique_player_count,
    t.total_wager,
    t.total_payout,
    t.jackpot_amount,
    t.net_gaming_revenue,

    CAST(
        t.net_gaming_revenue
        / NULLIF(t.total_wager, 0)
        AS DECIMAL(10,4)
    ) AS actual_hold_pct,

    ISNULL(e.event_count, 0) AS event_count,
    ISNULL(e.downtime_minutes, 0) AS downtime_minutes,
    ISNULL(e.critical_event_count, 0) AS critical_event_count,
    ISNULL(e.investigation_count, 0) AS investigation_count,

    CASE
        WHEN ISNULL(e.downtime_minutes, 0) >= 1440
        THEN 0
        ELSE 1440 - ISNULL(e.downtime_minutes, 0)
    END AS active_minutes,

    CAST(
        CASE
            WHEN ISNULL(e.downtime_minutes, 0) >= 1440
            THEN 0
            ELSE
                (
                    1440.0
                    - ISNULL(e.downtime_minutes, 0)
                ) / 1440.0
        END
        AS DECIMAL(10,4)
    ) AS availability_pct,

    CAST(
        t.net_gaming_revenue
        / NULLIF(
            CASE
                WHEN ISNULL(e.downtime_minutes, 0) >= 1440
                THEN 0
                ELSE
                    (
                        1440.0
                        - ISNULL(e.downtime_minutes, 0)
                    ) / 60.0
            END,
            0
        )
        AS DECIMAL(18,2)
    ) AS revenue_per_active_hour

FROM transaction_summary AS t

INNER JOIN dbo.dim_machine AS m
    ON t.machine_id = m.machine_id

LEFT JOIN event_summary AS e
    ON t.activity_date = e.activity_date
    AND t.machine_id = e.machine_id
    AND t.location_id = e.location_id;
GO


/* ============================================================
   View 2: Location performance
   ============================================================ */

CREATE VIEW dbo.vw_location_performance
AS

SELECT
    l.location_id,
    l.location_name,
    l.city,
    l.state,
    l.region,
    l.location_type,
    COUNT(DISTINCT m.machine_id) AS machine_count,
    COUNT(DISTINCT s.session_id) AS session_count,
    COUNT(DISTINCT s.player_id) AS unique_player_count,
    SUM(ISNULL(s.total_rounds, 0)) AS total_rounds,
    SUM(ISNULL(s.total_wager, 0)) AS total_wager,
    SUM(ISNULL(s.total_payout, 0)) AS total_payout,
    SUM(ISNULL(s.net_gaming_revenue, 0)) AS net_gaming_revenue,

    CAST(
        SUM(ISNULL(s.net_gaming_revenue, 0))
        / NULLIF(
            SUM(ISNULL(s.total_wager, 0)),
            0
        )
        AS DECIMAL(10,4)
    ) AS actual_hold_pct,

    CAST(
        SUM(ISNULL(s.net_gaming_revenue, 0))
        / NULLIF(
            COUNT(DISTINCT s.session_id),
            0
        )
        AS DECIMAL(18,2)
    ) AS revenue_per_session,

    CAST(
        SUM(ISNULL(s.net_gaming_revenue, 0))
        / NULLIF(
            COUNT(DISTINCT m.machine_id),
            0
        )
        AS DECIMAL(18,2)
    ) AS revenue_per_machine

FROM dbo.dim_location AS l

LEFT JOIN dbo.dim_machine AS m
    ON l.location_id = m.location_id

LEFT JOIN dbo.fact_player_session AS s
    ON l.location_id = s.location_id
    AND m.machine_id = s.machine_id

GROUP BY
    l.location_id,
    l.location_name,
    l.city,
    l.state,
    l.region,
    l.location_type;
GO


/* ============================================================
   View 3: Player summary
   ============================================================ */

CREATE VIEW dbo.vw_player_summary
AS

SELECT
    p.player_id,
    p.loyalty_tier,
    p.age_band,
    p.home_region,
    p.marketing_opt_in,
    p.active_flag,
    MIN(s.session_start) AS first_session_date,
    MAX(s.session_start) AS latest_session_date,
    COUNT(DISTINCT s.session_id) AS session_count,
    COUNT(DISTINCT s.location_id) AS locations_visited,
    COUNT(DISTINCT s.machine_id) AS machines_played,
    SUM(ISNULL(s.session_duration_minutes, 0))
        AS total_session_minutes,
    SUM(ISNULL(s.total_rounds, 0))
        AS total_rounds,
    SUM(ISNULL(s.total_wager, 0))
        AS total_wager,
    SUM(ISNULL(s.total_payout, 0))
        AS total_payout,
    SUM(ISNULL(s.net_gaming_revenue, 0))
        AS player_net_revenue,

    CAST(
        AVG(
            CAST(
                s.session_duration_minutes
                AS DECIMAL(18,2)
            )
        )
        AS DECIMAL(18,2)
    ) AS average_session_minutes,

    CAST(
        SUM(ISNULL(s.total_wager, 0))
        / NULLIF(
            COUNT(DISTINCT s.session_id),
            0
        )
        AS DECIMAL(18,2)
    ) AS average_wager_per_session,

    CASE
        WHEN MAX(s.session_start) IS NULL
        THEN NULL
        ELSE
            DATEDIFF(
                DAY,
                MAX(s.session_start),
                (
                    SELECT MAX(session_start)
                    FROM dbo.fact_player_session
                )
            )
    END AS days_since_last_session

FROM dbo.dim_player AS p

LEFT JOIN dbo.fact_player_session AS s
    ON p.player_id = s.player_id

GROUP BY
    p.player_id,
    p.loyalty_tier,
    p.age_band,
    p.home_region,
    p.marketing_opt_in,
    p.active_flag;
GO


/* ============================================================
   View 4: Machine health
   ============================================================ */

CREATE VIEW dbo.vw_machine_health
AS

SELECT
    m.machine_id,
    m.location_id,
    l.location_name,
    m.manufacturer,
    m.game_title,
    m.game_category,
    m.software_version,
    m.machine_status,
    COUNT(e.event_id) AS total_event_count,

    SUM(
        CASE
            WHEN e.planned_event_flag = 0
            THEN 1
            ELSE 0
        END
    ) AS unplanned_event_count,

    SUM(
        CASE
            WHEN e.severity = 'Critical'
            THEN 1
            ELSE 0
        END
    ) AS critical_event_count,

    SUM(
        ISNULL(
            e.downtime_minutes,
            0
        )
    ) AS total_downtime_minutes,

    CAST(
        AVG(
            CAST(
                e.downtime_minutes
                AS DECIMAL(18,2)
            )
        )
        AS DECIMAL(18,2)
    ) AS average_downtime_minutes,

    SUM(
        CAST(
            ISNULL(
                e.requires_investigation,
                0
            )
            AS INT
        )
    ) AS investigation_count,

    CAST(
        CASE
            WHEN SUM(
                ISNULL(
                    e.downtime_minutes,
                    0
                )
            ) >= 525600
            THEN 0
            ELSE
                (
                    525600.0
                    - SUM(
                        ISNULL(
                            e.downtime_minutes,
                            0
                        )
                    )
                ) / 525600.0
        END
        AS DECIMAL(10,4)
    ) AS annual_availability_pct

FROM dbo.dim_machine AS m

INNER JOIN dbo.dim_location AS l
    ON m.location_id = l.location_id

LEFT JOIN dbo.fact_machine_event AS e
    ON m.machine_id = e.machine_id

GROUP BY
    m.machine_id,
    m.location_id,
    l.location_name,
    m.manufacturer,
    m.game_title,
    m.game_category,
    m.software_version,
    m.machine_status;
GO


/* ============================================================
   View 5: Executive KPIs
   ============================================================ */

CREATE VIEW dbo.vw_executive_kpis
AS

SELECT
    COUNT(DISTINCT t.location_id)
        AS active_location_count,

    COUNT(DISTINCT t.machine_id)
        AS revenue_generating_machine_count,

    COUNT(DISTINCT t.player_id)
        AS active_player_count,

    COUNT(DISTINCT t.session_id)
        AS total_session_count,

    COUNT_BIG(*)
        AS total_transaction_count,

    SUM(t.wager_amount)
        AS total_wager,

    SUM(t.payout_amount)
        AS total_payout,

    SUM(t.jackpot_amount)
        AS total_jackpot_amount,

    SUM(t.net_gaming_revenue)
        AS net_gaming_revenue,

    CAST(
        SUM(t.net_gaming_revenue)
        / NULLIF(
            SUM(t.wager_amount),
            0
        )
        AS DECIMAL(10,4)
    ) AS actual_hold_pct,

    CAST(
        SUM(t.net_gaming_revenue)
        / NULLIF(
            COUNT(DISTINCT t.session_id),
            0
        )
        AS DECIMAL(18,2)
    ) AS revenue_per_session,

    CAST(
        SUM(t.net_gaming_revenue)
        / NULLIF(
            COUNT(DISTINCT t.machine_id),
            0
        )
        AS DECIMAL(18,2)
    ) AS revenue_per_machine

FROM dbo.fact_gaming_transaction AS t;
GO


PRINT 'Analytics views created successfully.';
GO