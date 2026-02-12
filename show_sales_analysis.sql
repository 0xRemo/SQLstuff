/*
================================================================================
  Neon Harbor - Super Awesome Tour: Show-Level Ticket Sales Analysis
================================================================================

  OBJECTIVE:
    Aggregate ticket sales at the SHOW level (concert + all its upsells combined)
    using the minute-level time-series data from ticket_sales, then identify the
    top 2 and bottom 2 performing shows on the tour.

  DEPENDENCIES:
    - Uses the same concert/upsell classification from concert_upsells.sql
    - Joins to ticket_sales via event_id

  ASSUMPTIONS:
    - "Show" = one concert event plus all upsell events at the same venue_id
      and event_dt. Total show sales = concert ticket sales + upsell ticket sales.
    - 6 of 33 shows have zero rows in ticket_sales. These are excluded from the
      bottom ranking since they likely represent shows that haven't gone on sale
      yet (or have missing data), not genuinely poor performers.
    - ticket_sales.tickets_sold_in_minute values are additive counts per minute.

================================================================================
*/


-- =============================================================================
-- Step 1: Classify events and link upsells to their parent concert
-- =============================================================================

WITH concerts AS (
    SELECT
        event_id   AS concert_event_id,
        event_name AS concert_event_name,
        venue_id,
        event_dt
    FROM events
    WHERE LOWER(event_name) LIKE '%super awesome tour%'
),

upsells AS (
    SELECT
        event_id   AS upsell_event_id,
        event_name AS upsell_event_name,
        venue_id,
        event_dt
    FROM events
    WHERE LOWER(event_name) NOT LIKE '%super awesome tour%'
),

-- =============================================================================
-- Step 2: Map every event_id (concert or upsell) to its parent concert
-- =============================================================================
-- This creates a unified mapping so we can aggregate all ticket_sales rows
-- under the correct show, whether the sale was for the concert itself or an upsell.

event_to_show AS (
    -- Concert events map to themselves
    SELECT
        concert_event_id AS event_id,
        concert_event_id,
        concert_event_name,
        venue_id,
        event_dt,
        'concert' AS event_type
    FROM concerts

    UNION ALL

    -- Upsell events map to their parent concert (via venue_id + event_dt)
    SELECT
        u.upsell_event_id AS event_id,
        c.concert_event_id,
        c.concert_event_name,
        c.venue_id,
        c.event_dt,
        'upsell' AS event_type
    FROM upsells u
    INNER JOIN concerts c
        ON  u.venue_id = c.venue_id
        AND u.event_dt = c.event_dt
),

-- =============================================================================
-- Step 3: Aggregate ticket sales at the show level
-- =============================================================================

show_sales AS (
    SELECT
        ets.concert_event_id,
        ets.concert_event_name,
        ets.venue_id,
        ets.event_dt,
        SUM(CASE WHEN ets.event_type = 'concert' THEN ts.tickets_sold_in_minute ELSE 0 END) AS concert_tickets,
        SUM(CASE WHEN ets.event_type = 'upsell'  THEN ts.tickets_sold_in_minute ELSE 0 END) AS upsell_tickets,
        SUM(ts.tickets_sold_in_minute) AS total_tickets
    FROM event_to_show ets
    INNER JOIN ticket_sales ts
        ON ets.event_id = ts.event_id
    GROUP BY
        ets.concert_event_id,
        ets.concert_event_name,
        ets.venue_id,
        ets.event_dt
),

-- =============================================================================
-- Step 4: Rank shows by total ticket sales
-- =============================================================================

ranked_shows AS (
    SELECT
        *,
        RANK() OVER (ORDER BY total_tickets DESC) AS rank_top,
        RANK() OVER (ORDER BY total_tickets ASC)  AS rank_bottom
    FROM show_sales
)

-- =============================================================================
-- Final output: All shows ranked, with top 2 and bottom 2 flagged
-- =============================================================================

SELECT
    concert_event_id,
    concert_event_name,
    venue_id,
    event_dt,
    concert_tickets,
    upsell_tickets,
    total_tickets,
    ROUND(upsell_tickets * 100.0 / NULLIF(total_tickets, 0), 1) AS upsell_pct,
    rank_top,
    rank_bottom,
    CASE
        WHEN rank_top    <= 2 THEN 'TOP 2'
        WHEN rank_bottom <= 2 THEN 'BOTTOM 2'
        ELSE NULL
    END AS ranking_flag
FROM ranked_shows
ORDER BY total_tickets DESC;
