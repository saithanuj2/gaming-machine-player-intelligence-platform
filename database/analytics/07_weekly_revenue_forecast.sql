USE GamingIntelligenceDB;
GO

DROP VIEW IF EXISTS dbo.vw_ml_weekly_revenue_forecast;
GO

CREATE VIEW dbo.vw_ml_weekly_revenue_forecast
AS

WITH weekly_revenue AS
(
    SELECT
        DATEADD(
            DAY,
            1 - DATEPART(WEEKDAY, CAST(t.transaction_timestamp AS DATE)),
            CAST(t.transaction_timestamp AS DATE)
        ) AS week_start_date,

        t.location_id,

        COUNT_BIG(*) AS transaction_count,
        COUNT(DISTINCT t.session_id) AS session_count,
        COUNT(DISTINCT t.player_id) AS unique_player_count,
        COUNT(DISTINCT t.machine_id) AS active_machine_count,
        SUM(t.wager_amount) AS total_wager,
        SUM(t.payout_amount) AS total_payout,
        SUM(t.jackpot_amount) AS jackpot_amount,
        SUM(t.net_gaming_revenue) AS net_gaming_revenue

    FROM dbo.fact_gaming_transaction AS t

    GROUP BY
        DATEADD(
            DAY,
            1 - DATEPART(WEEKDAY, CAST(t.transaction_timestamp AS DATE)),
            CAST(t.transaction_timestamp AS DATE)
        ),
        t.location_id
),

weekly_events AS
(
    SELECT
        DATEADD(
            DAY,
            1 - DATEPART(WEEKDAY, e.event_date),
            e.event_date
        ) AS week_start_date,

        e.location_id,

        COUNT_BIG(*) AS event_count,
        SUM(e.downtime_minutes) AS downtime_minutes,

        SUM(
            CASE
                WHEN e.severity = 'Critical'
                THEN 1
                ELSE 0
            END
        ) AS critical_event_count

    FROM dbo.fact_machine_event AS e

    GROUP BY
        DATEADD(
            DAY,
            1 - DATEPART(WEEKDAY, e.event_date),
            e.event_date
        ),
        e.location_id
),

combined_weekly AS
(
    SELECT
        r.week_start_date,
        r.location_id,
        l.location_name,
        l.region,
        l.location_type,
        r.transaction_count,
        r.session_count,
        r.unique_player_count,
        r.active_machine_count,
        r.total_wager,
        r.total_payout,
        r.jackpot_amount,
        r.net_gaming_revenue,
        ISNULL(e.event_count, 0) AS event_count,
        ISNULL(e.downtime_minutes, 0) AS downtime_minutes,
        ISNULL(e.critical_event_count, 0) AS critical_event_count

    FROM weekly_revenue AS r

    INNER JOIN dbo.dim_location AS l
        ON r.location_id = l.location_id

    LEFT JOIN weekly_events AS e
        ON r.week_start_date = e.week_start_date
        AND r.location_id = e.location_id
)

SELECT
    week_start_date,
    location_id,
    location_name,
    region,
    location_type,

    YEAR(week_start_date) AS activity_year,
    DATEPART(QUARTER, week_start_date) AS activity_quarter,
    DATEPART(MONTH, week_start_date) AS activity_month,
    DATEPART(ISO_WEEK, week_start_date) AS iso_week_number,

    transaction_count,
    session_count,
    unique_player_count,
    active_machine_count,
    total_wager,
    total_payout,
    jackpot_amount,
    net_gaming_revenue,
    event_count,
    downtime_minutes,
    critical_event_count,

    LAG(net_gaming_revenue, 1) OVER
    (
        PARTITION BY location_id
        ORDER BY week_start_date
    ) AS revenue_lag_1_week,

    LAG(net_gaming_revenue, 2) OVER
    (
        PARTITION BY location_id
        ORDER BY week_start_date
    ) AS revenue_lag_2_weeks,

    LAG(net_gaming_revenue, 4) OVER
    (
        PARTITION BY location_id
        ORDER BY week_start_date
    ) AS revenue_lag_4_weeks,

    CAST(
        AVG(net_gaming_revenue) OVER
        (
            PARTITION BY location_id
            ORDER BY week_start_date
            ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING
        )
        AS DECIMAL(18,2)
    ) AS previous_4_week_average_revenue,

    CAST(
        AVG(net_gaming_revenue) OVER
        (
            PARTITION BY location_id
            ORDER BY week_start_date
            ROWS BETWEEN 8 PRECEDING AND 1 PRECEDING
        )
        AS DECIMAL(18,2)
    ) AS previous_8_week_average_revenue,

    CAST(
        AVG(session_count * 1.0) OVER
        (
            PARTITION BY location_id
            ORDER BY week_start_date
            ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING
        )
        AS DECIMAL(18,2)
    ) AS previous_4_week_average_sessions

FROM combined_weekly;
GO

PRINT 'Weekly revenue forecast view created successfully.';
GO