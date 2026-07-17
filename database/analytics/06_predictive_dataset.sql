USE GamingIntelligenceDB;
GO

/* ============================================================
   Predictive Analytics Datasets
   Creates reusable, ML-ready SQL views
   ============================================================ */

DROP VIEW IF EXISTS dbo.vw_ml_player_churn;
GO

DROP VIEW IF EXISTS dbo.vw_ml_machine_failure;
GO

DROP VIEW IF EXISTS dbo.vw_ml_revenue_forecast;
GO

DROP VIEW IF EXISTS dbo.vw_ml_machine_anomaly;
GO


/* ============================================================
   View 1: Player churn prediction dataset

   Observation window:
   All activity through 60 days before the latest session date.

   Target window:
   The final 60 days in the dataset.

   churn_flag:
   1 = no session during the target window
   0 = returned during the target window
   ============================================================ */

CREATE VIEW dbo.vw_ml_player_churn
AS

WITH date_parameters AS
(
    SELECT
        CAST(MAX(session_start) AS DATE)
            AS dataset_end_date,

        DATEADD(
            DAY,
            -60,
            CAST(MAX(session_start) AS DATE)
        ) AS observation_cutoff_date

    FROM dbo.fact_player_session
),

historical_activity AS
(
    SELECT
        s.player_id,

        MIN(CAST(s.session_start AS DATE))
            AS first_session_date,

        MAX(CAST(s.session_start AS DATE))
            AS latest_historical_session_date,

        COUNT(DISTINCT s.session_id)
            AS total_historical_sessions,

        COUNT(
            DISTINCT CASE
                WHEN s.session_start >= DATEADD(
                    DAY,
                    -30,
                    p.observation_cutoff_date
                )
                THEN s.session_id
            END
        ) AS sessions_last_30_days,

        COUNT(
            DISTINCT CASE
                WHEN s.session_start >= DATEADD(
                    DAY,
                    -90,
                    p.observation_cutoff_date
                )
                THEN s.session_id
            END
        ) AS sessions_last_90_days,

        COUNT(DISTINCT s.location_id)
            AS locations_visited,

        COUNT(DISTINCT s.machine_id)
            AS machines_played,

        SUM(s.session_duration_minutes)
            AS total_session_minutes,

        AVG(
            CAST(
                s.session_duration_minutes
                AS DECIMAL(18,2)
            )
        ) AS average_session_minutes,

        SUM(s.total_rounds)
            AS total_rounds,

        SUM(s.total_wager)
            AS total_wager,

        SUM(s.total_payout)
            AS total_payout,

        SUM(s.net_gaming_revenue)
            AS player_net_revenue,

        AVG(
            CAST(
                s.total_wager
                AS DECIMAL(18,2)
            )
        ) AS average_wager_per_session,

        SUM(
            CASE
                WHEN s.session_start >= DATEADD(
                    DAY,
                    -30,
                    p.observation_cutoff_date
                )
                THEN s.total_wager
                ELSE 0
            END
        ) AS wager_last_30_days,

        SUM(
            CASE
                WHEN s.session_start >= DATEADD(
                    DAY,
                    -90,
                    p.observation_cutoff_date
                )
                THEN s.total_wager
                ELSE 0
            END
        ) AS wager_last_90_days,

        SUM(
            CASE
                WHEN s.session_start >= DATEADD(
                    DAY,
                    -30,
                    p.observation_cutoff_date
                )
                THEN s.net_gaming_revenue
                ELSE 0
            END
        ) AS revenue_last_30_days,

        SUM(
            CASE
                WHEN s.session_start >= DATEADD(
                    DAY,
                    -90,
                    p.observation_cutoff_date
                )
                THEN s.net_gaming_revenue
                ELSE 0
            END
        ) AS revenue_last_90_days

    FROM dbo.fact_player_session AS s

    CROSS JOIN date_parameters AS p

    WHERE
        CAST(s.session_start AS DATE)
        <= p.observation_cutoff_date

    GROUP BY
        s.player_id
),

future_activity AS
(
    SELECT
        s.player_id,
        COUNT(DISTINCT s.session_id)
            AS future_session_count

    FROM dbo.fact_player_session AS s

    CROSS JOIN date_parameters AS p

    WHERE
        CAST(s.session_start AS DATE)
            > p.observation_cutoff_date

        AND CAST(s.session_start AS DATE)
            <= p.dataset_end_date

    GROUP BY
        s.player_id
)

SELECT
    p.player_id,
    p.loyalty_tier,
    p.age_band,
    p.home_region,
    CAST(p.marketing_opt_in AS INT)
        AS marketing_opt_in,
    CAST(p.active_flag AS INT)
        AS registered_active_flag,

    d.observation_cutoff_date,
    d.dataset_end_date,

    h.first_session_date,
    h.latest_historical_session_date,

    DATEDIFF(
        DAY,
        h.latest_historical_session_date,
        d.observation_cutoff_date
    ) AS days_since_last_session,

    DATEDIFF(
        DAY,
        h.first_session_date,
        d.observation_cutoff_date
    ) + 1 AS observed_player_lifetime_days,

    h.total_historical_sessions,
    h.sessions_last_30_days,
    h.sessions_last_90_days,
    h.locations_visited,
    h.machines_played,
    h.total_session_minutes,
    h.average_session_minutes,
    h.total_rounds,
    h.total_wager,
    h.total_payout,
    h.player_net_revenue,
    h.average_wager_per_session,
    h.wager_last_30_days,
    h.wager_last_90_days,
    h.revenue_last_30_days,
    h.revenue_last_90_days,

    CAST(
        h.total_historical_sessions * 1.0
        / NULLIF(
            DATEDIFF(
                DAY,
                h.first_session_date,
                d.observation_cutoff_date
            ) + 1,
            0
        )
        AS DECIMAL(18,4)
    ) AS sessions_per_observed_day,

    ISNULL(f.future_session_count, 0)
        AS future_session_count,

    CASE
        WHEN ISNULL(f.future_session_count, 0) = 0
        THEN 1
        ELSE 0
    END AS churn_flag

FROM dbo.dim_player AS p

INNER JOIN historical_activity AS h
    ON p.player_id = h.player_id

CROSS JOIN date_parameters AS d

LEFT JOIN future_activity AS f
    ON p.player_id = f.player_id;
GO


/* ============================================================
   View 2: Machine failure prediction dataset

   Observation window:
   All data through 30 days before the latest event date.

   Target window:
   Final 30 days.

   failure_target_flag:
   1 = high/critical unplanned failure in target window
   0 = no qualifying target failure
   ============================================================ */

CREATE VIEW dbo.vw_ml_machine_failure
AS

WITH date_parameters AS
(
    SELECT
        MAX(event_date) AS dataset_end_date,

        DATEADD(
            DAY,
            -30,
            MAX(event_date)
        ) AS observation_cutoff_date

    FROM dbo.fact_machine_event
),

historical_events AS
(
    SELECT
        e.machine_id,

        COUNT_BIG(*)
            AS total_historical_events,

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
            CASE
                WHEN e.severity = 'High'
                THEN 1
                ELSE 0
            END
        ) AS high_severity_event_count,

        SUM(e.downtime_minutes)
            AS total_downtime_minutes,

        AVG(
            CAST(
                e.downtime_minutes
                AS DECIMAL(18,2)
            )
        ) AS average_downtime_minutes,

        MAX(e.event_date)
            AS latest_historical_event_date,

        COUNT(
            CASE
                WHEN e.event_date >= DATEADD(
                    DAY,
                    -30,
                    p.observation_cutoff_date
                )
                THEN 1
            END
        ) AS events_last_30_days,

        SUM(
            CASE
                WHEN e.event_date >= DATEADD(
                    DAY,
                    -30,
                    p.observation_cutoff_date
                )
                THEN e.downtime_minutes
                ELSE 0
            END
        ) AS downtime_last_30_days,

        COUNT(
            CASE
                WHEN e.event_date >= DATEADD(
                    DAY,
                    -90,
                    p.observation_cutoff_date
                )
                THEN 1
            END
        ) AS events_last_90_days,

        SUM(
            CASE
                WHEN e.event_date >= DATEADD(
                    DAY,
                    -90,
                    p.observation_cutoff_date
                )
                THEN e.downtime_minutes
                ELSE 0
            END
        ) AS downtime_last_90_days

    FROM dbo.fact_machine_event AS e

    CROSS JOIN date_parameters AS p

    WHERE
        e.event_date
        <= p.observation_cutoff_date

    GROUP BY
        e.machine_id
),

historical_revenue AS
(
    SELECT
        t.machine_id,

        COUNT(DISTINCT t.session_id)
            AS historical_session_count,

        COUNT(DISTINCT t.player_id)
            AS historical_unique_players,

        SUM(t.wager_amount)
            AS historical_total_wager,

        SUM(t.net_gaming_revenue)
            AS historical_net_revenue,

        SUM(
            CASE
                WHEN CAST(t.transaction_timestamp AS DATE)
                    >= DATEADD(
                        DAY,
                        -30,
                        p.observation_cutoff_date
                    )
                THEN t.net_gaming_revenue
                ELSE 0
            END
        ) AS revenue_last_30_days,

        COUNT(
            DISTINCT CASE
                WHEN CAST(t.transaction_timestamp AS DATE)
                    >= DATEADD(
                        DAY,
                        -30,
                        p.observation_cutoff_date
                    )
                THEN t.session_id
            END
        ) AS sessions_last_30_days

    FROM dbo.fact_gaming_transaction AS t

    CROSS JOIN date_parameters AS p

    WHERE
        CAST(t.transaction_timestamp AS DATE)
        <= p.observation_cutoff_date

    GROUP BY
        t.machine_id
),

future_failures AS
(
    SELECT
        e.machine_id,

        SUM(
            CASE
                WHEN e.planned_event_flag = 0
                     AND e.severity IN (
                         'High',
                         'Critical'
                     )
                THEN 1
                ELSE 0
            END
        ) AS future_failure_count

    FROM dbo.fact_machine_event AS e

    CROSS JOIN date_parameters AS p

    WHERE
        e.event_date
            > p.observation_cutoff_date

        AND e.event_date
            <= p.dataset_end_date

    GROUP BY
        e.machine_id
)

SELECT
    m.machine_id,
    m.location_id,
    m.manufacturer,
    m.cabinet_type,
    m.game_title,
    m.game_category,
    m.software_version,
    m.machine_status,
    m.theoretical_hold_pct,
    m.install_date,

    DATEDIFF(
        DAY,
        m.install_date,
        p.observation_cutoff_date
    ) AS machine_age_days,

    p.observation_cutoff_date,
    p.dataset_end_date,

    ISNULL(e.total_historical_events, 0)
        AS total_historical_events,

    ISNULL(e.unplanned_event_count, 0)
        AS unplanned_event_count,

    ISNULL(e.critical_event_count, 0)
        AS critical_event_count,

    ISNULL(e.high_severity_event_count, 0)
        AS high_severity_event_count,

    ISNULL(e.total_downtime_minutes, 0)
        AS total_downtime_minutes,

    ISNULL(e.average_downtime_minutes, 0)
        AS average_downtime_minutes,

    e.latest_historical_event_date,

    CASE
        WHEN e.latest_historical_event_date IS NULL
        THEN NULL

        ELSE DATEDIFF(
            DAY,
            e.latest_historical_event_date,
            p.observation_cutoff_date
        )
    END AS days_since_last_event,

    ISNULL(e.events_last_30_days, 0)
        AS events_last_30_days,

    ISNULL(e.downtime_last_30_days, 0)
        AS downtime_last_30_days,

    ISNULL(e.events_last_90_days, 0)
        AS events_last_90_days,

    ISNULL(e.downtime_last_90_days, 0)
        AS downtime_last_90_days,

    ISNULL(r.historical_session_count, 0)
        AS historical_session_count,

    ISNULL(r.historical_unique_players, 0)
        AS historical_unique_players,

    ISNULL(r.historical_total_wager, 0)
        AS historical_total_wager,

    ISNULL(r.historical_net_revenue, 0)
        AS historical_net_revenue,

    ISNULL(r.revenue_last_30_days, 0)
        AS revenue_last_30_days,

    ISNULL(r.sessions_last_30_days, 0)
        AS sessions_last_30_days,

    ISNULL(f.future_failure_count, 0)
        AS future_failure_count,

    CASE
        WHEN ISNULL(f.future_failure_count, 0) > 0
        THEN 1
        ELSE 0
    END AS failure_target_flag

FROM dbo.dim_machine AS m

CROSS JOIN date_parameters AS p

LEFT JOIN historical_events AS e
    ON m.machine_id = e.machine_id

LEFT JOIN historical_revenue AS r
    ON m.machine_id = r.machine_id

LEFT JOIN future_failures AS f
    ON m.machine_id = f.machine_id;
GO


/* ============================================================
   View 3: Revenue forecasting dataset

   Grain:
   One row per location per activity date.

   Includes:
   Lag revenue, rolling averages, player/session activity,
   calendar features and operational downtime.
   ============================================================ */

CREATE VIEW dbo.vw_ml_revenue_forecast
AS

WITH daily_revenue AS
(
    SELECT
        CAST(t.transaction_timestamp AS DATE)
            AS activity_date,

        t.location_id,

        COUNT_BIG(*)
            AS transaction_count,

        COUNT(DISTINCT t.session_id)
            AS session_count,

        COUNT(DISTINCT t.player_id)
            AS unique_player_count,

        COUNT(DISTINCT t.machine_id)
            AS active_machine_count,

        SUM(t.wager_amount)
            AS total_wager,

        SUM(t.payout_amount)
            AS total_payout,

        SUM(t.jackpot_amount)
            AS jackpot_amount,

        SUM(t.net_gaming_revenue)
            AS net_gaming_revenue

    FROM dbo.fact_gaming_transaction AS t

    GROUP BY
        CAST(t.transaction_timestamp AS DATE),
        t.location_id
),

daily_events AS
(
    SELECT
        e.event_date AS activity_date,
        e.location_id,

        COUNT_BIG(*)
            AS event_count,

        SUM(e.downtime_minutes)
            AS downtime_minutes,

        SUM(
            CASE
                WHEN e.severity = 'Critical'
                THEN 1
                ELSE 0
            END
        ) AS critical_event_count

    FROM dbo.fact_machine_event AS e

    GROUP BY
        e.event_date,
        e.location_id
),

combined_daily AS
(
    SELECT
        r.activity_date,
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
        ISNULL(e.event_count, 0)
            AS event_count,
        ISNULL(e.downtime_minutes, 0)
            AS downtime_minutes,
        ISNULL(e.critical_event_count, 0)
            AS critical_event_count

    FROM daily_revenue AS r

    INNER JOIN dbo.dim_location AS l
        ON r.location_id = l.location_id

    LEFT JOIN daily_events AS e
        ON r.activity_date = e.activity_date
        AND r.location_id = e.location_id
)

SELECT
    activity_date,
    location_id,
    location_name,
    region,
    location_type,

    YEAR(activity_date)
        AS activity_year,

    MONTH(activity_date)
        AS activity_month,

    DATEPART(
        QUARTER,
        activity_date
    ) AS activity_quarter,

    DATEPART(
        WEEKDAY,
        activity_date
    ) AS day_of_week_number,

    DATENAME(
        WEEKDAY,
        activity_date
    ) AS day_of_week_name,

    CASE
        WHEN DATENAME(
            WEEKDAY,
            activity_date
        ) IN ('Saturday', 'Sunday')
        THEN 1
        ELSE 0
    END AS is_weekend,

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

    LAG(
        net_gaming_revenue,
        1
    ) OVER
    (
        PARTITION BY location_id
        ORDER BY activity_date
    ) AS revenue_lag_1_day,

    LAG(
        net_gaming_revenue,
        7
    ) OVER
    (
        PARTITION BY location_id
        ORDER BY activity_date
    ) AS revenue_lag_7_days,

    LAG(
        net_gaming_revenue,
        14
    ) OVER
    (
        PARTITION BY location_id
        ORDER BY activity_date
    ) AS revenue_lag_14_days,

    CAST(
        AVG(net_gaming_revenue) OVER
        (
            PARTITION BY location_id
            ORDER BY activity_date
            ROWS BETWEEN 7 PRECEDING
            AND 1 PRECEDING
        )
        AS DECIMAL(18,2)
    ) AS previous_7_day_average_revenue,

    CAST(
        AVG(net_gaming_revenue) OVER
        (
            PARTITION BY location_id
            ORDER BY activity_date
            ROWS BETWEEN 30 PRECEDING
            AND 1 PRECEDING
        )
        AS DECIMAL(18,2)
    ) AS previous_30_day_average_revenue,

    CAST(
        AVG(session_count * 1.0) OVER
        (
            PARTITION BY location_id
            ORDER BY activity_date
            ROWS BETWEEN 7 PRECEDING
            AND 1 PRECEDING
        )
        AS DECIMAL(18,2)
    ) AS previous_7_day_average_sessions

FROM combined_daily;
GO


/* ============================================================
   View 4: Machine anomaly-detection dataset

   Grain:
   Machine per day.

   Includes:
   Revenue, hold, player, session, downtime features and
   date-level z-scores.
   ============================================================ */

CREATE VIEW dbo.vw_ml_machine_anomaly
AS

WITH daily_statistics AS
(
    SELECT
        p.*,

        AVG(
            CAST(
                p.net_gaming_revenue
                AS FLOAT
            )
        ) OVER
        (
            PARTITION BY p.activity_date
        ) AS daily_average_revenue,

        STDEV(
            CAST(
                p.net_gaming_revenue
                AS FLOAT
            )
        ) OVER
        (
            PARTITION BY p.activity_date
        ) AS daily_revenue_stddev,

        AVG(
            CAST(
                p.total_wager
                AS FLOAT
            )
        ) OVER
        (
            PARTITION BY p.activity_date
        ) AS daily_average_wager,

        STDEV(
            CAST(
                p.total_wager
                AS FLOAT
            )
        ) OVER
        (
            PARTITION BY p.activity_date
        ) AS daily_wager_stddev,

        AVG(
            CAST(
                p.downtime_minutes
                AS FLOAT
            )
        ) OVER
        (
            PARTITION BY p.activity_date
        ) AS daily_average_downtime,

        STDEV(
            CAST(
                p.downtime_minutes
                AS FLOAT
            )
        ) OVER
        (
            PARTITION BY p.activity_date
        ) AS daily_downtime_stddev

    FROM dbo.vw_machine_daily_performance AS p
)

SELECT
    activity_date,
    machine_id,
    location_id,
    manufacturer,
    game_title,
    game_category,
    software_version,
    transaction_count,
    session_count,
    unique_player_count,
    total_wager,
    total_payout,
    jackpot_amount,
    net_gaming_revenue,
    actual_hold_pct,
    event_count,
    downtime_minutes,
    critical_event_count,
    investigation_count,
    active_minutes,
    availability_pct,
    revenue_per_active_hour,

    CAST(
        (
            net_gaming_revenue
            - daily_average_revenue
        )
        / NULLIF(
            daily_revenue_stddev,
            0
        )
        AS DECIMAL(18,4)
    ) AS revenue_z_score,

    CAST(
        (
            total_wager
            - daily_average_wager
        )
        / NULLIF(
            daily_wager_stddev,
            0
        )
        AS DECIMAL(18,4)
    ) AS wager_z_score,

    CAST(
        (
            downtime_minutes
            - daily_average_downtime
        )
        / NULLIF(
            daily_downtime_stddev,
            0
        )
        AS DECIMAL(18,4)
    ) AS downtime_z_score,

    CASE
        WHEN ABS(
            (
                net_gaming_revenue
                - daily_average_revenue
            )
            / NULLIF(
                daily_revenue_stddev,
                0
            )
        ) >= 3
        THEN 1

        WHEN ABS(
            (
                total_wager
                - daily_average_wager
            )
            / NULLIF(
                daily_wager_stddev,
                0
            )
        ) >= 3
        THEN 1

        WHEN (
            (
                downtime_minutes
                - daily_average_downtime
            )
            / NULLIF(
                daily_downtime_stddev,
                0
            )
        ) >= 3
        THEN 1

        WHEN critical_event_count > 0
        THEN 1

        ELSE 0
    END AS rule_based_anomaly_flag

FROM daily_statistics;
GO


PRINT 'Predictive analytics views created successfully.';
GO