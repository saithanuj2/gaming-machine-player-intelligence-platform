USE GamingIntelligenceDB;
GO

/* ============================================================
   Gaming Player Intelligence Analytics
   ============================================================ */


/* ============================================================
   Query 1: Executive player KPI summary
   ============================================================ */

SELECT
    COUNT(*) AS total_registered_players,

    SUM(
        CASE
            WHEN session_count > 0
            THEN 1
            ELSE 0
        END
    ) AS players_with_activity,

    SUM(
        CASE
            WHEN session_count = 0
            THEN 1
            ELSE 0
        END
    ) AS players_without_activity,

    SUM(
        CASE
            WHEN loyalty_tier = 'Platinum'
            THEN 1
            ELSE 0
        END
    ) AS platinum_players,

    SUM(
        CASE
            WHEN marketing_opt_in = 1
            THEN 1
            ELSE 0
        END
    ) AS marketing_opt_in_players,

    CAST(
        100.0
        * SUM(
            CASE
                WHEN marketing_opt_in = 1
                THEN 1
                ELSE 0
            END
        )
        / NULLIF(COUNT(*), 0)
        AS DECIMAL(10,2)
    ) AS marketing_opt_in_pct,

    CAST(
        AVG(
            CAST(
                session_count
                AS DECIMAL(18,2)
            )
        )
        AS DECIMAL(18,2)
    ) AS average_sessions_per_player,

    CAST(
        AVG(
            CAST(
                total_wager
                AS DECIMAL(18,2)
            )
        )
        AS DECIMAL(18,2)
    ) AS average_wager_per_player,

    CAST(
        AVG(
            CAST(
                player_net_revenue
                AS DECIMAL(18,2)
            )
        )
        AS DECIMAL(18,2)
    ) AS average_revenue_per_player

FROM dbo.vw_player_summary;
GO


/* ============================================================
   Query 2: Loyalty tier performance
   ============================================================ */

SELECT
    loyalty_tier,
    COUNT(*) AS registered_player_count,

    SUM(
        CASE
            WHEN session_count > 0
            THEN 1
            ELSE 0
        END
    ) AS active_player_count,

    SUM(session_count) AS total_sessions,
    SUM(total_wager) AS total_wager,
    SUM(total_payout) AS total_payout,
    SUM(player_net_revenue) AS player_net_revenue,

    CAST(
        SUM(player_net_revenue)
        / NULLIF(
            SUM(session_count),
            0
        )
        AS DECIMAL(18,2)
    ) AS revenue_per_session,

    CAST(
        SUM(total_wager)
        / NULLIF(
            COUNT(*),
            0
        )
        AS DECIMAL(18,2)
    ) AS wager_per_registered_player

FROM dbo.vw_player_summary

GROUP BY
    loyalty_tier

ORDER BY
    player_net_revenue DESC;
GO


/* ============================================================
   Query 3: Top 20 players by net gaming revenue
   ============================================================ */

SELECT TOP 20
    player_id,
    loyalty_tier,
    home_region,
    session_count,
    locations_visited,
    machines_played,
    total_wager,
    total_payout,
    player_net_revenue,
    average_session_minutes,
    average_wager_per_session,
    days_since_last_session

FROM dbo.vw_player_summary

WHERE
    session_count > 0

ORDER BY
    player_net_revenue DESC;
GO


/* ============================================================
   Query 4: Top players by wagering activity
   ============================================================ */

SELECT TOP 20
    player_id,
    loyalty_tier,
    session_count,
    total_rounds,
    total_wager,
    average_wager_per_session,
    player_net_revenue,

    CAST(
        player_net_revenue
        / NULLIF(total_wager, 0)
        AS DECIMAL(10,4)
    ) AS player_hold_pct

FROM dbo.vw_player_summary

WHERE
    session_count > 0

ORDER BY
    total_wager DESC;
GO


/* ============================================================
   Query 5: Player rankings using window functions
   ============================================================ */

WITH ranked_players AS
(
    SELECT
        player_id,
        loyalty_tier,
        session_count,
        total_wager,
        player_net_revenue,
        average_session_minutes,

        RANK() OVER
        (
            ORDER BY player_net_revenue DESC
        ) AS revenue_rank,

        DENSE_RANK() OVER
        (
            ORDER BY session_count DESC
        ) AS frequency_rank,

        NTILE(4) OVER
        (
            ORDER BY player_net_revenue DESC
        ) AS revenue_quartile,

        NTILE(4) OVER
        (
            ORDER BY total_wager DESC
        ) AS wagering_quartile

    FROM dbo.vw_player_summary

    WHERE
        session_count > 0
)

SELECT *
FROM ranked_players
ORDER BY revenue_rank;
GO


/* ============================================================
   Query 6: High-value player segmentation
   ============================================================ */

WITH player_value AS
(
    SELECT
        player_id,
        loyalty_tier,
        session_count,
        total_wager,
        player_net_revenue,
        average_wager_per_session,
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
)

SELECT
    player_id,
    loyalty_tier,
    session_count,
    total_wager,
    player_net_revenue,
    average_wager_per_session,
    days_since_last_session,

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

FROM player_value

ORDER BY
    player_net_revenue DESC;
GO


/* ============================================================
   Query 7: RFM scoring
   ============================================================ */

WITH rfm_base AS
(
    SELECT
        player_id,
        loyalty_tier,
        days_since_last_session AS recency_days,
        session_count AS frequency,
        player_net_revenue AS monetary_value

    FROM dbo.vw_player_summary

    WHERE
        session_count > 0
),

rfm_scores AS
(
    SELECT
        player_id,
        loyalty_tier,
        recency_days,
        frequency,
        monetary_value,

        NTILE(5) OVER
        (
            ORDER BY recency_days ASC
        ) AS recency_score,

        NTILE(5) OVER
        (
            ORDER BY frequency DESC
        ) AS frequency_score,

        NTILE(5) OVER
        (
            ORDER BY monetary_value DESC
        ) AS monetary_score

    FROM rfm_base
)

SELECT
    player_id,
    loyalty_tier,
    recency_days,
    frequency,
    monetary_value,
    recency_score,
    frequency_score,
    monetary_score,

    CONCAT(
        recency_score,
        frequency_score,
        monetary_score
    ) AS rfm_code,

    CASE
        WHEN recency_score >= 4
             AND frequency_score >= 4
             AND monetary_score >= 4
        THEN 'Champions'

        WHEN recency_score >= 3
             AND frequency_score >= 4
        THEN 'Loyal Players'

        WHEN recency_score >= 4
             AND frequency_score BETWEEN 2 AND 3
        THEN 'Potential Loyalists'

        WHEN recency_score <= 2
             AND frequency_score >= 3
        THEN 'At Risk'

        WHEN recency_score = 1
             AND frequency_score <= 2
        THEN 'Lost Players'

        ELSE 'Regular Players'
    END AS rfm_segment

FROM rfm_scores

ORDER BY
    monetary_value DESC;
GO


/* ============================================================
   Query 8: Churn-risk classification
   ============================================================ */

SELECT
    player_id,
    loyalty_tier,
    session_count,
    total_wager,
    player_net_revenue,
    latest_session_date,
    days_since_last_session,

    CASE
        WHEN session_count = 0
        THEN 'Never Activated'

        WHEN days_since_last_session >= 90
        THEN 'High Churn Risk'

        WHEN days_since_last_session >= 60
        THEN 'Medium Churn Risk'

        WHEN days_since_last_session >= 30
        THEN 'Low Churn Risk'

        ELSE 'Active'
    END AS churn_risk_level

FROM dbo.vw_player_summary

ORDER BY
    CASE
        WHEN session_count = 0
        THEN 1

        WHEN days_since_last_session >= 90
        THEN 2

        WHEN days_since_last_session >= 60
        THEN 3

        WHEN days_since_last_session >= 30
        THEN 4

        ELSE 5
    END,
    days_since_last_session DESC;
GO


/* ============================================================
   Query 9: Churn-risk summary
   ============================================================ */

WITH churn_segments AS
(
    SELECT
        player_id,

        CASE
            WHEN session_count = 0
            THEN 'Never Activated'

            WHEN days_since_last_session >= 90
            THEN 'High Churn Risk'

            WHEN days_since_last_session >= 60
            THEN 'Medium Churn Risk'

            WHEN days_since_last_session >= 30
            THEN 'Low Churn Risk'

            ELSE 'Active'
        END AS churn_risk_level,

        player_net_revenue

    FROM dbo.vw_player_summary
)

SELECT
    churn_risk_level,
    COUNT(*) AS player_count,
    SUM(player_net_revenue) AS associated_revenue,

    CAST(
        100.0 * COUNT(*)
        / SUM(COUNT(*)) OVER ()
        AS DECIMAL(10,2)
    ) AS player_pct

FROM churn_segments

GROUP BY
    churn_risk_level

ORDER BY
    player_count DESC;
GO


/* ============================================================
   Query 10: Player session frequency
   ============================================================ */

SELECT
    player_id,
    loyalty_tier,
    session_count,
    first_session_date,
    latest_session_date,

    DATEDIFF(
        DAY,
        first_session_date,
        latest_session_date
    ) AS active_span_days,

    CAST(
        session_count
        / NULLIF(
            DATEDIFF(
                DAY,
                first_session_date,
                latest_session_date
            ) + 1.0,
            0
        )
        AS DECIMAL(18,4)
    ) AS sessions_per_active_day,

    days_since_last_session

FROM dbo.vw_player_summary

WHERE
    session_count > 0

ORDER BY
    session_count DESC;
GO


/* ============================================================
   Query 11: Multi-location player analysis
   ============================================================ */

SELECT
    player_id,
    loyalty_tier,
    session_count,
    locations_visited,
    machines_played,
    total_wager,
    player_net_revenue,

    CASE
        WHEN locations_visited >= 5
        THEN 'Highly Mobile'

        WHEN locations_visited BETWEEN 3 AND 4
        THEN 'Multi-Location'

        WHEN locations_visited = 2
        THEN 'Dual-Location'

        ELSE 'Single-Location'
    END AS mobility_segment

FROM dbo.vw_player_summary

WHERE
    session_count > 0

ORDER BY
    locations_visited DESC,
    player_net_revenue DESC;
GO


/* ============================================================
   Query 12: Preferred location for each player
   ============================================================ */

WITH player_location_activity AS
(
    SELECT
        s.player_id,
        s.location_id,
        l.location_name,
        COUNT(*) AS session_count,
        SUM(s.total_wager) AS total_wager,
        SUM(s.net_gaming_revenue) AS player_net_revenue,

        ROW_NUMBER() OVER
        (
            PARTITION BY s.player_id
            ORDER BY
                COUNT(*) DESC,
                SUM(s.total_wager) DESC
        ) AS preference_rank

    FROM dbo.fact_player_session AS s

    INNER JOIN dbo.dim_location AS l
        ON s.location_id = l.location_id

    GROUP BY
        s.player_id,
        s.location_id,
        l.location_name
)

SELECT
    player_id,
    location_id,
    location_name,
    session_count,
    total_wager,
    player_net_revenue

FROM player_location_activity

WHERE
    preference_rank = 1

ORDER BY
    player_id;
GO


/* ============================================================
   Query 13: Preferred machine and game for each player
   ============================================================ */

WITH player_machine_activity AS
(
    SELECT
        s.player_id,
        s.machine_id,
        m.game_title,
        m.game_category,
        m.manufacturer,
        COUNT(*) AS session_count,
        SUM(s.total_wager) AS total_wager,

        ROW_NUMBER() OVER
        (
            PARTITION BY s.player_id
            ORDER BY
                COUNT(*) DESC,
                SUM(s.total_wager) DESC
        ) AS preference_rank

    FROM dbo.fact_player_session AS s

    INNER JOIN dbo.dim_machine AS m
        ON s.machine_id = m.machine_id

    GROUP BY
        s.player_id,
        s.machine_id,
        m.game_title,
        m.game_category,
        m.manufacturer
)

SELECT
    player_id,
    machine_id,
    game_title,
    game_category,
    manufacturer,
    session_count,
    total_wager

FROM player_machine_activity

WHERE
    preference_rank = 1

ORDER BY
    player_id;
GO


/* ============================================================
   Query 14: Weekend versus weekday player behavior
   ============================================================ */

SELECT
    CASE
        WHEN DATENAME(
            WEEKDAY,
            session_start
        ) IN ('Saturday', 'Sunday')
        THEN 'Weekend'

        ELSE 'Weekday'
    END AS day_type,

    COUNT(DISTINCT player_id) AS unique_players,
    COUNT(*) AS session_count,
    SUM(total_wager) AS total_wager,
    SUM(net_gaming_revenue) AS net_gaming_revenue,

    CAST(
        AVG(
            CAST(
                session_duration_minutes
                AS DECIMAL(18,2)
            )
        )
        AS DECIMAL(18,2)
    ) AS average_session_minutes

FROM dbo.fact_player_session

GROUP BY
    CASE
        WHEN DATENAME(
            WEEKDAY,
            session_start
        ) IN ('Saturday', 'Sunday')
        THEN 'Weekend'

        ELSE 'Weekday'
    END;
GO


/* ============================================================
   Query 15: Time-of-day behavior
   ============================================================ */

SELECT
    CASE
        WHEN DATEPART(
            HOUR,
            session_start
        ) BETWEEN 5 AND 11
        THEN 'Morning'

        WHEN DATEPART(
            HOUR,
            session_start
        ) BETWEEN 12 AND 16
        THEN 'Afternoon'

        WHEN DATEPART(
            HOUR,
            session_start
        ) BETWEEN 17 AND 21
        THEN 'Evening'

        ELSE 'Late Night'
    END AS time_of_day,

    COUNT(*) AS session_count,
    COUNT(DISTINCT player_id) AS unique_players,
    SUM(total_wager) AS total_wager,
    SUM(net_gaming_revenue) AS net_gaming_revenue,

    CAST(
        AVG(
            CAST(
                session_duration_minutes
                AS DECIMAL(18,2)
            )
        )
        AS DECIMAL(18,2)
    ) AS average_session_minutes

FROM dbo.fact_player_session

GROUP BY
    CASE
        WHEN DATEPART(
            HOUR,
            session_start
        ) BETWEEN 5 AND 11
        THEN 'Morning'

        WHEN DATEPART(
            HOUR,
            session_start
        ) BETWEEN 12 AND 16
        THEN 'Afternoon'

        WHEN DATEPART(
            HOUR,
            session_start
        ) BETWEEN 17 AND 21
        THEN 'Evening'

        ELSE 'Late Night'
    END

ORDER BY
    session_count DESC;
GO


/* ============================================================
   Query 16: Monthly player activity trend
   ============================================================ */

WITH monthly_activity AS
(
    SELECT
        DATEFROMPARTS(
            YEAR(session_start),
            MONTH(session_start),
            1
        ) AS activity_month,

        COUNT(DISTINCT player_id) AS active_players,
        COUNT(*) AS total_sessions,
        SUM(total_wager) AS total_wager,
        SUM(net_gaming_revenue) AS net_gaming_revenue

    FROM dbo.fact_player_session

    GROUP BY
        DATEFROMPARTS(
            YEAR(session_start),
            MONTH(session_start),
            1
        )
)

SELECT
    activity_month,
    active_players,
    total_sessions,
    total_wager,
    net_gaming_revenue,

    LAG(active_players) OVER
    (
        ORDER BY activity_month
    ) AS previous_month_players,

    active_players
    - LAG(active_players) OVER
    (
        ORDER BY activity_month
    ) AS player_change,

    LAG(net_gaming_revenue) OVER
    (
        ORDER BY activity_month
    ) AS previous_month_revenue,

    net_gaming_revenue
    - LAG(net_gaming_revenue) OVER
    (
        ORDER BY activity_month
    ) AS revenue_change

FROM monthly_activity

ORDER BY
    activity_month;
GO


/* ============================================================
   Query 17: Player cohort analysis
   ============================================================ */

WITH first_session AS
(
    SELECT
        player_id,

        DATEFROMPARTS(
            YEAR(MIN(session_start)),
            MONTH(MIN(session_start)),
            1
        ) AS cohort_month

    FROM dbo.fact_player_session

    GROUP BY
        player_id
),

player_activity AS
(
    SELECT
        s.player_id,
        f.cohort_month,

        DATEFROMPARTS(
            YEAR(s.session_start),
            MONTH(s.session_start),
            1
        ) AS activity_month

    FROM dbo.fact_player_session AS s

    INNER JOIN first_session AS f
        ON s.player_id = f.player_id
),

cohort_activity AS
(
    SELECT
        cohort_month,

        DATEDIFF(
            MONTH,
            cohort_month,
            activity_month
        ) AS cohort_index,

        COUNT(DISTINCT player_id)
            AS active_players

    FROM player_activity

    GROUP BY
        cohort_month,

        DATEDIFF(
            MONTH,
            cohort_month,
            activity_month
        )
),

cohort_size AS
(
    SELECT
        cohort_month,
        active_players AS cohort_player_count

    FROM cohort_activity

    WHERE
        cohort_index = 0
)

SELECT
    c.cohort_month,
    c.cohort_index,
    c.active_players,
    s.cohort_player_count,

    CAST(
        100.0
        * c.active_players
        / NULLIF(
            s.cohort_player_count,
            0
        )
        AS DECIMAL(10,2)
    ) AS retention_pct

FROM cohort_activity AS c

INNER JOIN cohort_size AS s
    ON c.cohort_month = s.cohort_month

ORDER BY
    c.cohort_month,
    c.cohort_index;
GO


/* ============================================================
   Query 18: Estimated player lifetime value
   ============================================================ */

WITH player_lifetime_metrics AS
(
    SELECT
        player_id,
        loyalty_tier,
        session_count,
        player_net_revenue,
        first_session_date,
        latest_session_date,

        DATEDIFF(
            DAY,
            first_session_date,
            latest_session_date
        ) + 1 AS observed_lifetime_days,

        CAST(
            player_net_revenue
            / NULLIF(
                DATEDIFF(
                    DAY,
                    first_session_date,
                    latest_session_date
                ) + 1.0,
                0
            )
            AS DECIMAL(18,4)
        ) AS daily_revenue_rate

    FROM dbo.vw_player_summary

    WHERE
        session_count > 0
)

SELECT
    player_id,
    loyalty_tier,
    session_count,
    player_net_revenue,
    observed_lifetime_days,
    daily_revenue_rate,

    CAST(
        daily_revenue_rate * 365
        AS DECIMAL(18,2)
    ) AS estimated_annual_value,

    CAST(
        daily_revenue_rate * 365 * 3
        AS DECIMAL(18,2)
    ) AS estimated_three_year_ltv

FROM player_lifetime_metrics

ORDER BY
    estimated_three_year_ltv DESC;
GO


/* ============================================================
   Query 19: Marketing opt-in performance comparison
   ============================================================ */

SELECT
    CASE
        WHEN marketing_opt_in = 1
        THEN 'Opted In'

        ELSE 'Not Opted In'
    END AS marketing_status,

    COUNT(*) AS player_count,
    SUM(session_count) AS session_count,
    SUM(total_wager) AS total_wager,
    SUM(player_net_revenue) AS player_net_revenue,

    CAST(
        SUM(player_net_revenue)
        / NULLIF(
            COUNT(*),
            0
        )
        AS DECIMAL(18,2)
    ) AS revenue_per_player,

    CAST(
        SUM(session_count) * 1.0
        / NULLIF(
            COUNT(*),
            0
        )
        AS DECIMAL(18,2)
    ) AS sessions_per_player

FROM dbo.vw_player_summary

GROUP BY
    marketing_opt_in;
GO


/* ============================================================
   Query 20: Power BI-ready player segmentation dataset
   ============================================================ */

WITH player_segments AS
(
    SELECT
        player_id,
        loyalty_tier,
        age_band,
        home_region,
        marketing_opt_in,
        session_count,
        locations_visited,
        machines_played,
        total_session_minutes,
        total_rounds,
        total_wager,
        total_payout,
        player_net_revenue,
        average_session_minutes,
        average_wager_per_session,
        days_since_last_session,

        NTILE(5) OVER
        (
            ORDER BY days_since_last_session ASC
        ) AS recency_score,

        NTILE(5) OVER
        (
            ORDER BY session_count DESC
        ) AS frequency_score,

        NTILE(5) OVER
        (
            ORDER BY player_net_revenue DESC
        ) AS monetary_score

    FROM dbo.vw_player_summary

    WHERE
        session_count > 0
)

SELECT
    player_id,
    loyalty_tier,
    age_band,
    home_region,
    marketing_opt_in,
    session_count,
    locations_visited,
    machines_played,
    total_session_minutes,
    total_rounds,
    total_wager,
    total_payout,
    player_net_revenue,
    average_session_minutes,
    average_wager_per_session,
    days_since_last_session,
    recency_score,
    frequency_score,
    monetary_score,

    recency_score
    + frequency_score
    + monetary_score AS total_rfm_score,

    CASE
        WHEN recency_score >= 4
             AND frequency_score >= 4
             AND monetary_score >= 4
        THEN 'Champions'

        WHEN recency_score >= 3
             AND frequency_score >= 4
        THEN 'Loyal Players'

        WHEN recency_score >= 4
             AND frequency_score BETWEEN 2 AND 3
        THEN 'Potential Loyalists'

        WHEN recency_score <= 2
             AND frequency_score >= 3
        THEN 'At Risk'

        WHEN recency_score = 1
             AND frequency_score <= 2
        THEN 'Lost Players'

        ELSE 'Regular Players'
    END AS rfm_segment,

    CASE
        WHEN days_since_last_session >= 90
        THEN 1
        ELSE 0
    END AS churn_flag

FROM player_segments;
GO