USE GamingIntelligenceDB;
GO

/* ============================================================
   Executive Dashboard Analytics
   Power BI-ready datasets
   ============================================================ */


/* ============================================================
   Query 1: Executive KPI summary
   ============================================================ */

SELECT
    k.active_location_count,
    k.revenue_generating_machine_count,
    k.active_player_count,
    k.total_session_count,
    k.total_transaction_count,
    k.total_wager,
    k.total_payout,
    k.total_jackpot_amount,
    k.net_gaming_revenue,
    k.actual_hold_pct,
    k.revenue_per_session,
    k.revenue_per_machine,

    (
        SELECT COUNT(*)
        FROM dbo.dim_machine
    ) AS total_registered_machines,

    (
        SELECT COUNT(*)
        FROM dbo.dim_player
    ) AS total_registered_players,

    (
        SELECT SUM(total_downtime_minutes)
        FROM dbo.vw_machine_health
    ) AS total_downtime_minutes,

    (
        SELECT SUM(critical_event_count)
        FROM dbo.vw_machine_health
    ) AS total_critical_events,

    (
        SELECT
            CAST(
                AVG(annual_availability_pct)
                AS DECIMAL(10,4)
            )
        FROM dbo.vw_machine_health
    ) AS average_machine_availability_pct

FROM dbo.vw_executive_kpis AS k;
GO


/* ============================================================
   Query 2: Daily executive revenue trend
   ============================================================ */

WITH daily_metrics AS
(
    SELECT
        CAST(transaction_timestamp AS DATE) AS activity_date,
        COUNT_BIG(*) AS transaction_count,
        COUNT(DISTINCT session_id) AS session_count,
        COUNT(DISTINCT player_id) AS active_player_count,
        COUNT(DISTINCT machine_id) AS active_machine_count,
        SUM(wager_amount) AS total_wager,
        SUM(payout_amount) AS total_payout,
        SUM(jackpot_amount) AS jackpot_amount,
        SUM(net_gaming_revenue) AS net_gaming_revenue

    FROM dbo.fact_gaming_transaction

    GROUP BY
        CAST(transaction_timestamp AS DATE)
)

SELECT
    activity_date,
    transaction_count,
    session_count,
    active_player_count,
    active_machine_count,
    total_wager,
    total_payout,
    jackpot_amount,
    net_gaming_revenue,

    CAST(
        net_gaming_revenue
        / NULLIF(total_wager, 0)
        AS DECIMAL(10,4)
    ) AS actual_hold_pct,

    CAST(
        AVG(net_gaming_revenue) OVER
        (
            ORDER BY activity_date
            ROWS BETWEEN 6 PRECEDING
            AND CURRENT ROW
        )
        AS DECIMAL(18,2)
    ) AS seven_day_revenue_moving_average,

    SUM(net_gaming_revenue) OVER
    (
        ORDER BY activity_date
        ROWS BETWEEN UNBOUNDED PRECEDING
        AND CURRENT ROW
    ) AS cumulative_revenue

FROM daily_metrics

ORDER BY
    activity_date;
GO


/* ============================================================
   Query 3: Monthly executive performance
   ============================================================ */

WITH monthly_metrics AS
(
    SELECT
        DATEFROMPARTS(
            YEAR(transaction_timestamp),
            MONTH(transaction_timestamp),
            1
        ) AS activity_month,

        COUNT_BIG(*) AS transaction_count,
        COUNT(DISTINCT session_id) AS session_count,
        COUNT(DISTINCT player_id) AS active_player_count,
        COUNT(DISTINCT machine_id) AS active_machine_count,
        SUM(wager_amount) AS total_wager,
        SUM(payout_amount) AS total_payout,
        SUM(jackpot_amount) AS jackpot_amount,
        SUM(net_gaming_revenue) AS net_gaming_revenue

    FROM dbo.fact_gaming_transaction

    GROUP BY
        DATEFROMPARTS(
            YEAR(transaction_timestamp),
            MONTH(transaction_timestamp),
            1
        )
),

monthly_comparison AS
(
    SELECT
        *,
        LAG(net_gaming_revenue) OVER
        (
            ORDER BY activity_month
        ) AS previous_month_revenue,

        LAG(active_player_count) OVER
        (
            ORDER BY activity_month
        ) AS previous_month_players

    FROM monthly_metrics
)

SELECT
    activity_month,
    transaction_count,
    session_count,
    active_player_count,
    active_machine_count,
    total_wager,
    total_payout,
    jackpot_amount,
    net_gaming_revenue,
    previous_month_revenue,

    net_gaming_revenue
    - previous_month_revenue
        AS revenue_change,

    CAST(
        (
            net_gaming_revenue
            - previous_month_revenue
        )
        / NULLIF(previous_month_revenue, 0)
        AS DECIMAL(10,4)
    ) AS revenue_growth_pct,

    active_player_count
    - previous_month_players
        AS player_change

FROM monthly_comparison

ORDER BY
    activity_month;
GO


/* ============================================================
   Query 4: Top and bottom location performance
   ============================================================ */

WITH ranked_locations AS
(
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
        net_gaming_revenue,
        revenue_per_machine,
        revenue_per_session,

        ROW_NUMBER() OVER
        (
            ORDER BY net_gaming_revenue DESC
        ) AS best_rank,

        ROW_NUMBER() OVER
        (
            ORDER BY net_gaming_revenue ASC
        ) AS worst_rank

    FROM dbo.vw_location_performance
)

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
    net_gaming_revenue,
    revenue_per_machine,
    revenue_per_session,

    CASE
        WHEN best_rank <= 5
        THEN 'Top Location'

        WHEN worst_rank <= 5
        THEN 'Bottom Location'

        ELSE 'Middle Performer'
    END AS performance_group

FROM ranked_locations

WHERE
    best_rank <= 5
    OR worst_rank <= 5

ORDER BY
    net_gaming_revenue DESC;
GO


/* ============================================================
   Query 5: Top machine performance
   ============================================================ */

WITH machine_metrics AS
(
    SELECT
        machine_id,
        manufacturer,
        game_title,
        game_category,
        software_version,
        SUM(session_count) AS session_count,
        SUM(total_wager) AS total_wager,
        SUM(net_gaming_revenue) AS net_gaming_revenue,
        SUM(downtime_minutes) AS downtime_minutes,
        SUM(critical_event_count) AS critical_event_count,

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
)

SELECT TOP 20
    machine_id,
    manufacturer,
    game_title,
    game_category,
    software_version,
    session_count,
    total_wager,
    net_gaming_revenue,
    downtime_minutes,
    critical_event_count,
    average_availability_pct,

    RANK() OVER
    (
        ORDER BY net_gaming_revenue DESC
    ) AS revenue_rank

FROM machine_metrics

ORDER BY
    net_gaming_revenue DESC;
GO


/* ============================================================
   Query 6: Player executive summary by segment
   ============================================================ */

WITH player_segments AS
(
    SELECT
        player_id,
        loyalty_tier,
        session_count,
        total_wager,
        player_net_revenue,
        days_since_last_session,

        NTILE(5) OVER
        (
            ORDER BY player_net_revenue DESC
        ) AS revenue_bucket,

        NTILE(5) OVER
        (
            ORDER BY session_count DESC
        ) AS frequency_bucket

    FROM dbo.vw_player_summary

    WHERE
        session_count > 0
),

classified_players AS
(
    SELECT
        *,

        CASE
            WHEN revenue_bucket = 1
                 AND frequency_bucket = 1
            THEN 'VIP'

            WHEN revenue_bucket <= 2
                 AND frequency_bucket <= 2
            THEN 'High Value'

            WHEN revenue_bucket <= 3
            THEN 'Medium Value'

            ELSE 'Low Value'
        END AS player_value_segment

    FROM player_segments
)

SELECT
    player_value_segment,
    COUNT(*) AS player_count,
    SUM(session_count) AS total_sessions,
    SUM(total_wager) AS total_wager,
    SUM(player_net_revenue) AS net_gaming_revenue,

    CAST(
        SUM(player_net_revenue)
        / NULLIF(COUNT(*), 0)
        AS DECIMAL(18,2)
    ) AS revenue_per_player,

    CAST(
        100.0 * COUNT(*)
        / SUM(COUNT(*)) OVER ()
        AS DECIMAL(10,2)
    ) AS player_distribution_pct

FROM classified_players

GROUP BY
    player_value_segment

ORDER BY
    net_gaming_revenue DESC;
GO


/* ============================================================
   Query 7: Churn-risk executive summary
   ============================================================ */

WITH churn_classification AS
(
    SELECT
        player_id,
        session_count,
        player_net_revenue,

        CASE
            WHEN session_count = 0
            THEN 'Never Activated'

            WHEN days_since_last_session >= 90
            THEN 'High Risk'

            WHEN days_since_last_session >= 60
            THEN 'Medium Risk'

            WHEN days_since_last_session >= 30
            THEN 'Low Risk'

            ELSE 'Active'
        END AS churn_status

    FROM dbo.vw_player_summary
)

SELECT
    churn_status,
    COUNT(*) AS player_count,
    SUM(player_net_revenue) AS associated_revenue,

    CAST(
        100.0 * COUNT(*)
        / SUM(COUNT(*)) OVER ()
        AS DECIMAL(10,2)
    ) AS player_pct,

    CAST(
        100.0 * SUM(player_net_revenue)
        / NULLIF(
            SUM(SUM(player_net_revenue)) OVER (),
            0
        )
        AS DECIMAL(10,2)
    ) AS revenue_pct

FROM churn_classification

GROUP BY
    churn_status

ORDER BY
    CASE churn_status
        WHEN 'High Risk' THEN 1
        WHEN 'Medium Risk' THEN 2
        WHEN 'Low Risk' THEN 3
        WHEN 'Active' THEN 4
        ELSE 5
    END;
GO


/* ============================================================
   Query 8: Machine health executive summary
   ============================================================ */

WITH health_segments AS
(
    SELECT
        machine_id,
        total_event_count,
        critical_event_count,
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
        END AS health_risk_level

    FROM dbo.vw_machine_health
)

SELECT
    health_risk_level,
    COUNT(*) AS machine_count,
    SUM(total_event_count) AS total_events,
    SUM(critical_event_count) AS critical_events,
    SUM(total_downtime_minutes) AS total_downtime_minutes,

    CAST(
        AVG(annual_availability_pct)
        AS DECIMAL(10,4)
    ) AS average_availability_pct,

    CAST(
        100.0 * COUNT(*)
        / SUM(COUNT(*)) OVER ()
        AS DECIMAL(10,2)
    ) AS machine_distribution_pct

FROM health_segments

GROUP BY
    health_risk_level

ORDER BY
    CASE health_risk_level
        WHEN 'High Risk' THEN 1
        WHEN 'Medium Risk' THEN 2
        ELSE 3
    END;
GO


/* ============================================================
   Query 9: Revenue and operational efficiency by location
   ============================================================ */

WITH location_downtime AS
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
    l.location_id,
    l.location_name,
    l.region,
    l.machine_count,
    l.session_count,
    l.unique_player_count,
    l.net_gaming_revenue,
    l.revenue_per_machine,
    ISNULL(d.downtime_minutes, 0) AS downtime_minutes,
    ISNULL(d.event_count, 0) AS event_count,
    ISNULL(d.critical_events, 0) AS critical_events,

    CAST(
        l.net_gaming_revenue
        / NULLIF(
            l.machine_count * 8760.0
            - ISNULL(d.downtime_minutes, 0) / 60.0,
            0
        )
        AS DECIMAL(18,2)
    ) AS revenue_per_available_machine_hour

FROM dbo.vw_location_performance AS l

LEFT JOIN location_downtime AS d
    ON l.location_id = d.location_id

ORDER BY
    revenue_per_available_machine_hour DESC;
GO


/* ============================================================
   Query 10: Manufacturer executive comparison
   ============================================================ */

WITH manufacturer_revenue AS
(
    SELECT
        manufacturer,
        COUNT(DISTINCT machine_id) AS revenue_machine_count,
        SUM(session_count) AS session_count,
        SUM(total_wager) AS total_wager,
        SUM(net_gaming_revenue) AS net_gaming_revenue

    FROM dbo.vw_machine_daily_performance

    GROUP BY
        manufacturer
),

manufacturer_health AS
(
    SELECT
        manufacturer,
        COUNT(*) AS machine_count,
        SUM(total_event_count) AS event_count,
        SUM(critical_event_count) AS critical_event_count,
        SUM(total_downtime_minutes) AS downtime_minutes,

        CAST(
            AVG(annual_availability_pct)
            AS DECIMAL(10,4)
        ) AS availability_pct

    FROM dbo.vw_machine_health

    GROUP BY
        manufacturer
)

SELECT
    h.manufacturer,
    h.machine_count,
    r.session_count,
    r.total_wager,
    r.net_gaming_revenue,
    h.event_count,
    h.critical_event_count,
    h.downtime_minutes,
    h.availability_pct,

    CAST(
        r.net_gaming_revenue
        / NULLIF(h.machine_count, 0)
        AS DECIMAL(18,2)
    ) AS revenue_per_machine,

    CAST(
        h.downtime_minutes * 1.0
        / NULLIF(h.machine_count, 0)
        AS DECIMAL(18,2)
    ) AS downtime_per_machine

FROM manufacturer_health AS h

LEFT JOIN manufacturer_revenue AS r
    ON h.manufacturer = r.manufacturer

ORDER BY
    r.net_gaming_revenue DESC;
GO


/* ============================================================
   Query 11: Software version executive comparison
   ============================================================ */

SELECT
    software_version,
    COUNT(DISTINCT machine_id) AS machine_count,
    SUM(session_count) AS session_count,
    SUM(total_wager) AS total_wager,
    SUM(net_gaming_revenue) AS net_gaming_revenue,
    SUM(event_count) AS event_count,
    SUM(critical_event_count) AS critical_event_count,
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
   Query 12: Power BI dashboard master dataset
   ============================================================ */

WITH revenue_summary AS
(
    SELECT
        COUNT(DISTINCT location_id) AS active_locations,
        COUNT(DISTINCT machine_id) AS active_machines,
        COUNT(DISTINCT player_id) AS active_players,
        COUNT(DISTINCT session_id) AS total_sessions,
        COUNT_BIG(*) AS total_transactions,
        SUM(wager_amount) AS total_wager,
        SUM(payout_amount) AS total_payout,
        SUM(jackpot_amount) AS jackpot_amount,
        SUM(net_gaming_revenue) AS net_gaming_revenue

    FROM dbo.fact_gaming_transaction
),

machine_summary AS
(
    SELECT
        COUNT(*) AS registered_machines,
        SUM(total_event_count) AS total_events,
        SUM(critical_event_count) AS critical_events,
        SUM(total_downtime_minutes) AS downtime_minutes,

        CAST(
            AVG(annual_availability_pct)
            AS DECIMAL(10,4)
        ) AS availability_pct

    FROM dbo.vw_machine_health
),

player_summary AS
(
    SELECT
        COUNT(*) AS registered_players,

        SUM(
            CASE
                WHEN session_count > 0
                THEN 1
                ELSE 0
            END
        ) AS activated_players,

        SUM(
            CASE
                WHEN days_since_last_session >= 90
                THEN 1
                ELSE 0
            END
        ) AS high_churn_risk_players,

        SUM(
            CASE
                WHEN loyalty_tier = 'Platinum'
                THEN 1
                ELSE 0
            END
        ) AS platinum_players

    FROM dbo.vw_player_summary
)

SELECT
    r.active_locations,
    r.active_machines,
    m.registered_machines,
    r.active_players,
    p.registered_players,
    p.activated_players,
    p.high_churn_risk_players,
    p.platinum_players,
    r.total_sessions,
    r.total_transactions,
    r.total_wager,
    r.total_payout,
    r.jackpot_amount,
    r.net_gaming_revenue,

    CAST(
        r.net_gaming_revenue
        / NULLIF(r.total_wager, 0)
        AS DECIMAL(10,4)
    ) AS actual_hold_pct,

    CAST(
        r.net_gaming_revenue
        / NULLIF(r.total_sessions, 0)
        AS DECIMAL(18,2)
    ) AS revenue_per_session,

    CAST(
        r.net_gaming_revenue
        / NULLIF(r.active_machines, 0)
        AS DECIMAL(18,2)
    ) AS revenue_per_active_machine,

    m.total_events,
    m.critical_events,
    m.downtime_minutes,
    m.availability_pct

FROM revenue_summary AS r

CROSS JOIN machine_summary AS m

CROSS JOIN player_summary AS p;
GO