USE GamingIntelligenceDB;
GO

/* ============================================================
   Gaming Machine Performance Analytics
   ============================================================ */


/* ============================================================
   Query 1: Overall machine performance summary
   ============================================================ */

SELECT
    machine_id,
    manufacturer,
    game_title,
    game_category,
    software_version,
    SUM(transaction_count) AS total_transactions,
    SUM(session_count) AS total_sessions,
    SUM(unique_player_count) AS total_unique_players,
    SUM(total_wager) AS total_wager,
    SUM(total_payout) AS total_payout,
    SUM(jackpot_amount) AS total_jackpot_amount,
    SUM(net_gaming_revenue) AS net_gaming_revenue,

    CAST(
        SUM(net_gaming_revenue)
        / NULLIF(SUM(total_wager), 0)
        AS DECIMAL(10,4)
    ) AS actual_hold_pct,

    SUM(downtime_minutes) AS total_downtime_minutes,
    SUM(event_count) AS total_events,
    SUM(critical_event_count) AS critical_events,

    CAST(
        AVG(availability_pct)
        AS DECIMAL(10,4)
    ) AS average_availability_pct

FROM dbo.vw_machine_daily_performance

GROUP BY
    machine_id,
    manufacturer,
    game_title,
    game_category,
    software_version

ORDER BY
    net_gaming_revenue DESC;
GO


/* ============================================================
   Query 2: Top 10 revenue-generating machines
   ============================================================ */

SELECT TOP 10
    machine_id,
    manufacturer,
    game_title,
    game_category,
    SUM(total_wager) AS total_wager,
    SUM(net_gaming_revenue) AS net_gaming_revenue,

    CAST(
        SUM(net_gaming_revenue)
        / NULLIF(SUM(total_wager), 0)
        AS DECIMAL(10,4)
    ) AS actual_hold_pct,

    SUM(session_count) AS total_sessions,
    SUM(downtime_minutes) AS downtime_minutes

FROM dbo.vw_machine_daily_performance

GROUP BY
    machine_id,
    manufacturer,
    game_title,
    game_category

ORDER BY
    net_gaming_revenue DESC;
GO


/* ============================================================
   Query 3: Bottom 10 revenue-generating machines
   ============================================================ */

SELECT TOP 10
    machine_id,
    manufacturer,
    game_title,
    game_category,
    SUM(total_wager) AS total_wager,
    SUM(net_gaming_revenue) AS net_gaming_revenue,

    CAST(
        SUM(net_gaming_revenue)
        / NULLIF(SUM(total_wager), 0)
        AS DECIMAL(10,4)
    ) AS actual_hold_pct,

    SUM(session_count) AS total_sessions,
    SUM(downtime_minutes) AS downtime_minutes

FROM dbo.vw_machine_daily_performance

GROUP BY
    machine_id,
    manufacturer,
    game_title,
    game_category

ORDER BY
    net_gaming_revenue ASC;
GO


/* ============================================================
   Query 4: Machine ranking using window functions
   ============================================================ */

WITH machine_revenue AS
(
    SELECT
        machine_id,
        manufacturer,
        game_title,
        SUM(net_gaming_revenue) AS net_gaming_revenue,
        SUM(total_wager) AS total_wager,
        SUM(session_count) AS total_sessions
    FROM dbo.vw_machine_daily_performance
    GROUP BY
        machine_id,
        manufacturer,
        game_title
)

SELECT
    machine_id,
    manufacturer,
    game_title,
    net_gaming_revenue,
    total_wager,
    total_sessions,

    RANK() OVER
    (
        ORDER BY net_gaming_revenue DESC
    ) AS revenue_rank,

    DENSE_RANK() OVER
    (
        ORDER BY total_sessions DESC
    ) AS session_rank,

    NTILE(4) OVER
    (
        ORDER BY net_gaming_revenue DESC
    ) AS performance_quartile

FROM machine_revenue

ORDER BY
    revenue_rank;
GO


/* ============================================================
   Query 5: Machine performance by manufacturer
   ============================================================ */

SELECT
    manufacturer,
    COUNT(DISTINCT machine_id) AS machine_count,
    SUM(transaction_count) AS total_transactions,
    SUM(session_count) AS total_sessions,
    SUM(total_wager) AS total_wager,
    SUM(net_gaming_revenue) AS net_gaming_revenue,

    CAST(
        SUM(net_gaming_revenue)
        / NULLIF(SUM(total_wager), 0)
        AS DECIMAL(10,4)
    ) AS actual_hold_pct,

    CAST(
        SUM(net_gaming_revenue)
        / NULLIF(COUNT(DISTINCT machine_id), 0)
        AS DECIMAL(18,2)
    ) AS revenue_per_machine,

    SUM(downtime_minutes) AS total_downtime_minutes

FROM dbo.vw_machine_daily_performance

GROUP BY
    manufacturer

ORDER BY
    net_gaming_revenue DESC;
GO


/* ============================================================
   Query 6: Machine performance by game category
   ============================================================ */

SELECT
    game_category,
    COUNT(DISTINCT machine_id) AS machine_count,
    SUM(session_count) AS total_sessions,
    SUM(unique_player_count) AS unique_players,
    SUM(total_wager) AS total_wager,
    SUM(total_payout) AS total_payout,
    SUM(net_gaming_revenue) AS net_gaming_revenue,

    CAST(
        SUM(net_gaming_revenue)
        / NULLIF(SUM(total_wager), 0)
        AS DECIMAL(10,4)
    ) AS actual_hold_pct,

    CAST(
        SUM(net_gaming_revenue)
        / NULLIF(SUM(session_count), 0)
        AS DECIMAL(18,2)
    ) AS revenue_per_session

FROM dbo.vw_machine_daily_performance

GROUP BY
    game_category

ORDER BY
    net_gaming_revenue DESC;
GO


/* ============================================================
   Query 7: Machines with highest downtime
   ============================================================ */

SELECT TOP 10
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
    annual_availability_pct

FROM dbo.vw_machine_health

ORDER BY
    total_downtime_minutes DESC;
GO


/* ============================================================
   Query 8: Machines with the lowest availability
   ============================================================ */

SELECT TOP 10
    machine_id,
    location_name,
    manufacturer,
    game_title,
    software_version,
    total_downtime_minutes,
    critical_event_count,
    annual_availability_pct

FROM dbo.vw_machine_health

ORDER BY
    annual_availability_pct ASC,
    total_downtime_minutes DESC;
GO


/* ============================================================
   Query 9: Revenue and downtime combined
   ============================================================ */

WITH machine_revenue AS
(
    SELECT
        machine_id,
        SUM(net_gaming_revenue) AS net_gaming_revenue,
        SUM(total_wager) AS total_wager,
        SUM(session_count) AS session_count
    FROM dbo.vw_machine_daily_performance
    GROUP BY machine_id
)

SELECT
    r.machine_id,
    h.location_name,
    h.manufacturer,
    h.game_title,
    r.session_count,
    r.total_wager,
    r.net_gaming_revenue,
    h.total_downtime_minutes,
    h.critical_event_count,
    h.annual_availability_pct,

    CAST(
        r.net_gaming_revenue
        / NULLIF(
            8760.0
            - h.total_downtime_minutes / 60.0,
            0
        )
        AS DECIMAL(18,2)
    ) AS revenue_per_available_hour

FROM machine_revenue AS r

INNER JOIN dbo.vw_machine_health AS h
    ON r.machine_id = h.machine_id

ORDER BY
    revenue_per_available_hour DESC;
GO


/* ============================================================
   Query 10: Daily machine revenue trend
   ============================================================ */

SELECT
    activity_date,
    SUM(total_wager) AS total_wager,
    SUM(total_payout) AS total_payout,
    SUM(net_gaming_revenue) AS net_gaming_revenue,
    SUM(session_count) AS total_sessions,
    SUM(downtime_minutes) AS total_downtime_minutes,

    CAST(
        SUM(net_gaming_revenue)
        / NULLIF(SUM(total_wager), 0)
        AS DECIMAL(10,4)
    ) AS actual_hold_pct

FROM dbo.vw_machine_daily_performance

GROUP BY
    activity_date

ORDER BY
    activity_date;
GO


/* ============================================================
   Query 11: Seven-day moving average revenue
   ============================================================ */

WITH daily_revenue AS
(
    SELECT
        activity_date,
        SUM(net_gaming_revenue) AS daily_revenue
    FROM dbo.vw_machine_daily_performance
    GROUP BY activity_date
)

SELECT
    activity_date,
    daily_revenue,

    CAST(
        AVG(daily_revenue) OVER
        (
            ORDER BY activity_date
            ROWS BETWEEN 6 PRECEDING
            AND CURRENT ROW
        )
        AS DECIMAL(18,2)
    ) AS seven_day_moving_average,

    SUM(daily_revenue) OVER
    (
        ORDER BY activity_date
        ROWS BETWEEN UNBOUNDED PRECEDING
        AND CURRENT ROW
    ) AS cumulative_revenue

FROM daily_revenue

ORDER BY
    activity_date;
GO


/* ============================================================
   Query 12: Day-over-day revenue change
   ============================================================ */

WITH daily_revenue AS
(
    SELECT
        activity_date,
        SUM(net_gaming_revenue) AS daily_revenue
    FROM dbo.vw_machine_daily_performance
    GROUP BY activity_date
),

revenue_comparison AS
(
    SELECT
        activity_date,
        daily_revenue,

        LAG(daily_revenue) OVER
        (
            ORDER BY activity_date
        ) AS previous_day_revenue

    FROM daily_revenue
)

SELECT
    activity_date,
    daily_revenue,
    previous_day_revenue,
    daily_revenue - previous_day_revenue
        AS revenue_change,

    CAST(
        (
            daily_revenue
            - previous_day_revenue
        )
        / NULLIF(previous_day_revenue, 0)
        AS DECIMAL(10,4)
    ) AS revenue_change_pct

FROM revenue_comparison

ORDER BY
    activity_date;
GO


/* ============================================================
   Query 13: Software version performance
   ============================================================ */

SELECT
    software_version,
    COUNT(DISTINCT machine_id) AS machine_count,
    SUM(session_count) AS total_sessions,
    SUM(total_wager) AS total_wager,
    SUM(net_gaming_revenue) AS net_gaming_revenue,
    SUM(event_count) AS total_events,
    SUM(critical_event_count) AS critical_events,
    SUM(downtime_minutes) AS downtime_minutes,

    CAST(
        SUM(net_gaming_revenue)
        / NULLIF(SUM(total_wager), 0)
        AS DECIMAL(10,4)
    ) AS actual_hold_pct,

    CAST(
        AVG(availability_pct)
        AS DECIMAL(10,4)
    ) AS average_availability_pct

FROM dbo.vw_machine_daily_performance

GROUP BY
    software_version

ORDER BY
    net_gaming_revenue DESC;
GO


/* ============================================================
   Query 14: Machines requiring investigation
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
    investigation_count,
    total_downtime_minutes,
    annual_availability_pct,

    CASE
        WHEN critical_event_count >= 8
             OR total_downtime_minutes >= 5000
        THEN 'High Risk'

        WHEN critical_event_count >= 4
             OR total_downtime_minutes >= 3500
        THEN 'Medium Risk'

        ELSE 'Low Risk'
    END AS machine_risk_level

FROM dbo.vw_machine_health

WHERE
    investigation_count > 0

ORDER BY
    CASE
        WHEN critical_event_count >= 8
             OR total_downtime_minutes >= 5000
        THEN 1

        WHEN critical_event_count >= 4
             OR total_downtime_minutes >= 3500
        THEN 2

        ELSE 3
    END,
    total_downtime_minutes DESC;
GO


/* ============================================================
   Query 15: Best and worst machine in each location
   ============================================================ */

WITH machine_location_revenue AS
(
    SELECT
        location_id,
        machine_id,
        SUM(net_gaming_revenue) AS net_gaming_revenue
    FROM dbo.vw_machine_daily_performance
    GROUP BY
        location_id,
        machine_id
),

ranked_machines AS
(
    SELECT
        location_id,
        machine_id,
        net_gaming_revenue,

        ROW_NUMBER() OVER
        (
            PARTITION BY location_id
            ORDER BY net_gaming_revenue DESC
        ) AS best_machine_rank,

        ROW_NUMBER() OVER
        (
            PARTITION BY location_id
            ORDER BY net_gaming_revenue ASC
        ) AS worst_machine_rank

    FROM machine_location_revenue
)

SELECT
    r.location_id,
    l.location_name,
    r.machine_id,
    r.net_gaming_revenue,

    CASE
        WHEN r.best_machine_rank = 1
        THEN 'Best Machine'

        WHEN r.worst_machine_rank = 1
        THEN 'Worst Machine'
    END AS performance_label

FROM ranked_machines AS r

INNER JOIN dbo.dim_location AS l
    ON r.location_id = l.location_id

WHERE
    r.best_machine_rank = 1
    OR r.worst_machine_rank = 1

ORDER BY
    r.location_id,
    performance_label;
GO