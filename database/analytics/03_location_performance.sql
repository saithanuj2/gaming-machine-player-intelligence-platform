USE GamingIntelligenceDB;
GO

/* ============================================================
   Gaming Location Performance Analytics
   ============================================================ */


/* ============================================================
   Query 1: Overall location performance
   ============================================================ */

SELECT
    location_id,
    location_name,
    city,
    state,
    region,
    location_type,
    machine_count,
    session_count,
    unique_player_count,
    total_rounds,
    total_wager,
    total_payout,
    net_gaming_revenue,
    actual_hold_pct,
    revenue_per_session,
    revenue_per_machine
FROM dbo.vw_location_performance
ORDER BY
    net_gaming_revenue DESC;
GO


/* ============================================================
   Query 2: Location ranking using window functions
   ============================================================ */

SELECT
    location_id,
    location_name,
    region,
    machine_count,
    session_count,
    unique_player_count,
    net_gaming_revenue,
    revenue_per_machine,

    RANK() OVER
    (
        ORDER BY net_gaming_revenue DESC
    ) AS revenue_rank,

    DENSE_RANK() OVER
    (
        ORDER BY session_count DESC
    ) AS session_rank,

    NTILE(4) OVER
    (
        ORDER BY net_gaming_revenue DESC
    ) AS revenue_quartile

FROM dbo.vw_location_performance

ORDER BY
    revenue_rank;
GO


/* ============================================================
   Query 3: Revenue contribution by location
   ============================================================ */

SELECT
    location_id,
    location_name,
    region,
    net_gaming_revenue,

    CAST(
        100.0
        * net_gaming_revenue
        / NULLIF(
            SUM(net_gaming_revenue) OVER (),
            0
        )
        AS DECIMAL(10,2)
    ) AS revenue_contribution_pct,

    SUM(net_gaming_revenue) OVER
    (
        ORDER BY net_gaming_revenue DESC
        ROWS BETWEEN UNBOUNDED PRECEDING
        AND CURRENT ROW
    ) AS cumulative_revenue,

    CAST(
        100.0
        * SUM(net_gaming_revenue) OVER
        (
            ORDER BY net_gaming_revenue DESC
            ROWS BETWEEN UNBOUNDED PRECEDING
            AND CURRENT ROW
        )
        / NULLIF(
            SUM(net_gaming_revenue) OVER (),
            0
        )
        AS DECIMAL(10,2)
    ) AS cumulative_revenue_pct

FROM dbo.vw_location_performance

ORDER BY
    net_gaming_revenue DESC;
GO


/* ============================================================
   Query 4: Revenue per machine and utilization
   ============================================================ */

SELECT
    location_id,
    location_name,
    machine_count,
    session_count,
    unique_player_count,
    net_gaming_revenue,
    revenue_per_machine,

    CAST(
        session_count * 1.0
        / NULLIF(machine_count, 0)
        AS DECIMAL(18,2)
    ) AS sessions_per_machine,

    CAST(
        unique_player_count * 1.0
        / NULLIF(machine_count, 0)
        AS DECIMAL(18,2)
    ) AS players_per_machine,

    CASE
        WHEN revenue_per_machine >= 7000
        THEN 'High Productivity'

        WHEN revenue_per_machine >= 6000
        THEN 'Medium Productivity'

        ELSE 'Low Productivity'
    END AS machine_productivity_segment

FROM dbo.vw_location_performance

ORDER BY
    revenue_per_machine DESC;
GO


/* ============================================================
   Query 5: Location performance by region
   ============================================================ */

SELECT
    region,
    COUNT(*) AS location_count,
    SUM(machine_count) AS total_machines,
    SUM(session_count) AS total_sessions,
    SUM(unique_player_count) AS total_location_player_counts,
    SUM(total_wager) AS total_wager,
    SUM(net_gaming_revenue) AS net_gaming_revenue,

    CAST(
        SUM(net_gaming_revenue)
        / NULLIF(SUM(machine_count), 0)
        AS DECIMAL(18,2)
    ) AS revenue_per_machine,

    CAST(
        SUM(net_gaming_revenue)
        / NULLIF(SUM(session_count), 0)
        AS DECIMAL(18,2)
    ) AS revenue_per_session

FROM dbo.vw_location_performance

GROUP BY
    region

ORDER BY
    net_gaming_revenue DESC;
GO


/* ============================================================
   Query 6: Performance by location type
   ============================================================ */

SELECT
    location_type,
    COUNT(*) AS location_count,
    SUM(machine_count) AS total_machines,
    SUM(session_count) AS total_sessions,
    SUM(unique_player_count) AS total_location_player_counts,
    SUM(total_wager) AS total_wager,
    SUM(net_gaming_revenue) AS net_gaming_revenue,

    CAST(
        SUM(net_gaming_revenue)
        / NULLIF(SUM(machine_count), 0)
        AS DECIMAL(18,2)
    ) AS revenue_per_machine,

    CAST(
        SUM(net_gaming_revenue)
        / NULLIF(SUM(session_count), 0)
        AS DECIMAL(18,2)
    ) AS revenue_per_session

FROM dbo.vw_location_performance

GROUP BY
    location_type

ORDER BY
    net_gaming_revenue DESC;
GO


/* ============================================================
   Query 7: Daily location revenue trend
   ============================================================ */

SELECT
    t.location_id,
    l.location_name,
    CAST(t.transaction_timestamp AS DATE) AS activity_date,
    COUNT_BIG(*) AS transaction_count,
    COUNT(DISTINCT t.session_id) AS session_count,
    COUNT(DISTINCT t.player_id) AS unique_player_count,
    SUM(t.wager_amount) AS total_wager,
    SUM(t.payout_amount) AS total_payout,
    SUM(t.net_gaming_revenue) AS net_gaming_revenue,

    CAST(
        SUM(t.net_gaming_revenue)
        / NULLIF(SUM(t.wager_amount), 0)
        AS DECIMAL(10,4)
    ) AS actual_hold_pct

FROM dbo.fact_gaming_transaction AS t

INNER JOIN dbo.dim_location AS l
    ON t.location_id = l.location_id

GROUP BY
    t.location_id,
    l.location_name,
    CAST(t.transaction_timestamp AS DATE)

ORDER BY
    activity_date,
    net_gaming_revenue DESC;
GO


/* ============================================================
   Query 8: Monthly location performance
   ============================================================ */

WITH monthly_location_performance AS
(
    SELECT
        t.location_id,
        l.location_name,

        DATEFROMPARTS(
            YEAR(t.transaction_timestamp),
            MONTH(t.transaction_timestamp),
            1
        ) AS activity_month,

        COUNT(DISTINCT t.session_id) AS session_count,
        COUNT(DISTINCT t.player_id) AS unique_player_count,
        SUM(t.wager_amount) AS total_wager,
        SUM(t.net_gaming_revenue) AS net_gaming_revenue

    FROM dbo.fact_gaming_transaction AS t

    INNER JOIN dbo.dim_location AS l
        ON t.location_id = l.location_id

    GROUP BY
        t.location_id,
        l.location_name,

        DATEFROMPARTS(
            YEAR(t.transaction_timestamp),
            MONTH(t.transaction_timestamp),
            1
        )
)

SELECT
    location_id,
    location_name,
    activity_month,
    session_count,
    unique_player_count,
    total_wager,
    net_gaming_revenue,

    LAG(net_gaming_revenue) OVER
    (
        PARTITION BY location_id
        ORDER BY activity_month
    ) AS previous_month_revenue,

    net_gaming_revenue
    - LAG(net_gaming_revenue) OVER
    (
        PARTITION BY location_id
        ORDER BY activity_month
    ) AS revenue_change,

    CAST(
        (
            net_gaming_revenue
            - LAG(net_gaming_revenue) OVER
            (
                PARTITION BY location_id
                ORDER BY activity_month
            )
        )
        / NULLIF(
            LAG(net_gaming_revenue) OVER
            (
                PARTITION BY location_id
                ORDER BY activity_month
            ),
            0
        )
        AS DECIMAL(10,4)
    ) AS revenue_growth_pct

FROM monthly_location_performance

ORDER BY
    location_id,
    activity_month;
GO


/* ============================================================
   Query 9: Three-month moving average by location
   ============================================================ */

WITH monthly_location_revenue AS
(
    SELECT
        location_id,

        DATEFROMPARTS(
            YEAR(transaction_timestamp),
            MONTH(transaction_timestamp),
            1
        ) AS activity_month,

        SUM(net_gaming_revenue) AS monthly_revenue

    FROM dbo.fact_gaming_transaction

    GROUP BY
        location_id,

        DATEFROMPARTS(
            YEAR(transaction_timestamp),
            MONTH(transaction_timestamp),
            1
        )
)

SELECT
    location_id,
    activity_month,
    monthly_revenue,

    CAST(
        AVG(monthly_revenue) OVER
        (
            PARTITION BY location_id
            ORDER BY activity_month
            ROWS BETWEEN 2 PRECEDING
            AND CURRENT ROW
        )
        AS DECIMAL(18,2)
    ) AS three_month_moving_average,

    SUM(monthly_revenue) OVER
    (
        PARTITION BY location_id
        ORDER BY activity_month
        ROWS BETWEEN UNBOUNDED PRECEDING
        AND CURRENT ROW
    ) AS cumulative_location_revenue

FROM monthly_location_revenue

ORDER BY
    location_id,
    activity_month;
GO


/* ============================================================
   Query 10: Best and worst location in each region
   ============================================================ */

WITH regional_location_rankings AS
(
    SELECT
        location_id,
        location_name,
        region,
        net_gaming_revenue,
        revenue_per_machine,

        ROW_NUMBER() OVER
        (
            PARTITION BY region
            ORDER BY net_gaming_revenue DESC
        ) AS best_location_rank,

        ROW_NUMBER() OVER
        (
            PARTITION BY region
            ORDER BY net_gaming_revenue ASC
        ) AS worst_location_rank

    FROM dbo.vw_location_performance
)

SELECT
    location_id,
    location_name,
    region,
    net_gaming_revenue,
    revenue_per_machine,

    CASE
        WHEN best_location_rank = 1
        THEN 'Best in Region'

        WHEN worst_location_rank = 1
        THEN 'Worst in Region'
    END AS regional_performance_label

FROM regional_location_rankings

WHERE
    best_location_rank = 1
    OR worst_location_rank = 1

ORDER BY
    region,
    regional_performance_label;
GO


/* ============================================================
   Query 11: Location machine mix analysis
   ============================================================ */

SELECT
    l.location_id,
    l.location_name,
    m.manufacturer,
    m.game_category,
    COUNT(*) AS machine_count,

    CAST(
        100.0 * COUNT(*)
        / NULLIF(
            SUM(COUNT(*)) OVER
            (
                PARTITION BY l.location_id
            ),
            0
        )
        AS DECIMAL(10,2)
    ) AS machine_mix_pct

FROM dbo.dim_location AS l

INNER JOIN dbo.dim_machine AS m
    ON l.location_id = m.location_id

GROUP BY
    l.location_id,
    l.location_name,
    m.manufacturer,
    m.game_category

ORDER BY
    l.location_id,
    machine_count DESC;
GO


/* ============================================================
   Query 12: Location player mobility analysis
   ============================================================ */

WITH player_location_counts AS
(
    SELECT
        player_id,
        COUNT(DISTINCT location_id) AS locations_visited

    FROM dbo.fact_player_session

    GROUP BY
        player_id
),

location_player_summary AS
(
    SELECT
        s.location_id,
        COUNT(DISTINCT s.player_id) AS total_players,

        COUNT(
            DISTINCT CASE
                WHEN p.locations_visited > 1
                THEN s.player_id
            END
        ) AS multi_location_players

    FROM dbo.fact_player_session AS s

    INNER JOIN player_location_counts AS p
        ON s.player_id = p.player_id

    GROUP BY
        s.location_id
)

SELECT
    l.location_id,
    l.location_name,
    s.total_players,
    s.multi_location_players,

    CAST(
        100.0
        * s.multi_location_players
        / NULLIF(s.total_players, 0)
        AS DECIMAL(10,2)
    ) AS multi_location_player_pct

FROM location_player_summary AS s

INNER JOIN dbo.dim_location AS l
    ON s.location_id = l.location_id

ORDER BY
    multi_location_player_pct DESC;
GO


/* ============================================================
   Query 13: Location downtime and operational risk
   ============================================================ */

SELECT
    l.location_id,
    l.location_name,
    COUNT(DISTINCT e.machine_id) AS machines_with_events,
    COUNT_BIG(*) AS total_events,

    SUM(
        CASE
            WHEN e.planned_event_flag = 0
            THEN 1
            ELSE 0
        END
    ) AS unplanned_events,

    SUM(
        CASE
            WHEN e.severity = 'Critical'
            THEN 1
            ELSE 0
        END
    ) AS critical_events,

    SUM(e.downtime_minutes) AS total_downtime_minutes,

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
            e.requires_investigation
            AS INT
        )
    ) AS investigation_count

FROM dbo.fact_machine_event AS e

INNER JOIN dbo.dim_location AS l
    ON e.location_id = l.location_id

GROUP BY
    l.location_id,
    l.location_name

ORDER BY
    total_downtime_minutes DESC;
GO


/* ============================================================
   Query 14: Revenue and downtime combined by location
   ============================================================ */

WITH location_revenue AS
(
    SELECT
        location_id,
        SUM(net_gaming_revenue) AS net_gaming_revenue,
        SUM(wager_amount) AS total_wager,
        COUNT(DISTINCT session_id) AS session_count

    FROM dbo.fact_gaming_transaction

    GROUP BY
        location_id
),

location_downtime AS
(
    SELECT
        location_id,
        SUM(downtime_minutes) AS downtime_minutes,
        COUNT_BIG(*) AS event_count,

        SUM(
            CASE
                WHEN severity = 'Critical'
                THEN 1
                ELSE 0
            END
        ) AS critical_events

    FROM dbo.fact_machine_event

    GROUP BY
        location_id
)

SELECT
    r.location_id,
    l.location_name,
    r.session_count,
    r.total_wager,
    r.net_gaming_revenue,
    ISNULL(d.downtime_minutes, 0) AS downtime_minutes,
    ISNULL(d.event_count, 0) AS event_count,
    ISNULL(d.critical_events, 0) AS critical_events,

    CAST(
        r.net_gaming_revenue
        / NULLIF(
            8760.0
            * COUNT(m.machine_id)
            - ISNULL(d.downtime_minutes, 0) / 60.0,
            0
        )
        AS DECIMAL(18,2)
    ) AS revenue_per_available_machine_hour

FROM location_revenue AS r

INNER JOIN dbo.dim_location AS l
    ON r.location_id = l.location_id

INNER JOIN dbo.dim_machine AS m
    ON r.location_id = m.location_id

LEFT JOIN location_downtime AS d
    ON r.location_id = d.location_id

GROUP BY
    r.location_id,
    l.location_name,
    r.session_count,
    r.total_wager,
    r.net_gaming_revenue,
    d.downtime_minutes,
    d.event_count,
    d.critical_events

ORDER BY
    revenue_per_available_machine_hour DESC;
GO


/* ============================================================
   Query 15: Location performance classification
   ============================================================ */

WITH location_metrics AS
(
    SELECT
        location_id,
        location_name,
        region,
        machine_count,
        session_count,
        unique_player_count,
        net_gaming_revenue,
        revenue_per_machine,

        AVG(net_gaming_revenue) OVER ()
            AS average_location_revenue,

        AVG(revenue_per_machine) OVER ()
            AS average_revenue_per_machine

    FROM dbo.vw_location_performance
)

SELECT
    location_id,
    location_name,
    region,
    machine_count,
    session_count,
    unique_player_count,
    net_gaming_revenue,
    revenue_per_machine,

    CASE
        WHEN net_gaming_revenue >= average_location_revenue
             AND revenue_per_machine >= average_revenue_per_machine
        THEN 'High Revenue / High Efficiency'

        WHEN net_gaming_revenue >= average_location_revenue
             AND revenue_per_machine < average_revenue_per_machine
        THEN 'High Revenue / Low Efficiency'

        WHEN net_gaming_revenue < average_location_revenue
             AND revenue_per_machine >= average_revenue_per_machine
        THEN 'Low Revenue / High Efficiency'

        ELSE 'Low Revenue / Low Efficiency'
    END AS performance_segment

FROM location_metrics

ORDER BY
    net_gaming_revenue DESC;
GO