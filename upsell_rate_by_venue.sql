/*
================================================================================
  Upsell Rate by Venue
================================================================================

  OBJECTIVE:
    Calculate the upsell rate (upsell tickets sold / concert tickets sold) for
    each venue, and show how many distinct upsell products each venue offers.
    Results are ordered by the number of upsell options (descending).

  DEFINITIONS:
    - Concert: any event where event_name contains "Super Awesome Tour"
    - Upsell:  every other event at the same venue on the same date
    - Upsell rate: SUM(upsell tickets) / SUM(concert tickets) for the venue
    - Upsell options: COUNT of distinct upsell event names at the venue

  NOTES:
    - Venues with zero concert ticket sales are excluded (no division by zero).
    - Orphaned upsells (no matching concert) are excluded since there is no
      concert denominator to calculate a rate against.
    - ticket_sales is joined via event_id to get tickets_sold_in_minute totals.

================================================================================
*/

WITH concerts AS (
    SELECT
        e.event_id,
        e.venue_id,
        e.event_dt
    FROM events e
    WHERE LOWER(e.event_name) LIKE '%super awesome tour%'
),

upsells AS (
    SELECT
        e.event_id,
        e.event_name,
        e.venue_id,
        e.event_dt
    FROM events e
    WHERE LOWER(e.event_name) NOT LIKE '%super awesome tour%'
),

-- Only upsells that have a matching concert (same venue + date)
matched_upsells AS (
    SELECT
        u.event_id,
        u.event_name,
        c.venue_id
    FROM upsells u
    INNER JOIN concerts c
        ON  u.venue_id = c.venue_id
        AND u.event_dt = c.event_dt
),

concert_sales AS (
    SELECT
        c.venue_id,
        SUM(ts.tickets_sold_in_minute) AS concert_tickets
    FROM concerts c
    INNER JOIN ticket_sales ts
        ON c.event_id = ts.event_id
    GROUP BY c.venue_id
),

upsell_sales AS (
    SELECT
        mu.venue_id,
        COUNT(DISTINCT mu.event_name)  AS upsell_options,
        SUM(ts.tickets_sold_in_minute) AS upsell_tickets
    FROM matched_upsells mu
    INNER JOIN ticket_sales ts
        ON mu.event_id = ts.event_id
    GROUP BY mu.venue_id
)

SELECT
    cs.venue_id,
    cs.concert_tickets,
    COALESCE(us.upsell_tickets, 0)                              AS upsell_tickets,
    COALESCE(us.upsell_options, 0)                               AS upsell_options,
    ROUND(COALESCE(us.upsell_tickets, 0) * 100.0
          / cs.concert_tickets, 2)                               AS upsell_rate_pct
FROM concert_sales cs
LEFT JOIN upsell_sales us
    ON cs.venue_id = us.venue_id
WHERE cs.concert_tickets > 0
ORDER BY upsell_options DESC, upsell_rate_pct DESC;
