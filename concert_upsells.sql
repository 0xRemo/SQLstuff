/*
================================================================================
  Neon Harbor - Super Awesome Tour: Concert-to-Upsell Association Query
================================================================================

  OBJECTIVE:
    Link each primary concert event with its associated upsell events
    (parking, VIP access, coat check, etc.) from the events dataset for
    Neon Harbor's Super Awesome Tour.

  APPROACH:
    1. Classify each event as either a "concert" or an "upsell" based on
       the event_name field.
    2. Join concerts to upsells using the composite key (venue_id, event_dt),
       since upsells for a concert occur at the same venue on the same date.

  ASSUMPTIONS:
    - Concert events are identified by the presence of "Super Awesome Tour"
      (case-insensitive) in the event_name. This covers both naming variants
      observed in the data:
        * "Neon Harbor - Super Awesome Tour"  (dash separator)
        * "Neon Harbor: Super Awesome Tour"   (colon separator)
    - All other events are classified as upsells. This includes items like
      parking, VIP club access, lounge access, coat check, fast lane, lawn
      chair rental, blanket, pre-show passes, premium seating, lockers,
      suite access, commemorative tickets, "Upgrades & Extras" bundles, etc.
    - A concert and its upsells share the same venue_id AND event_dt.
      Each (venue_id, event_dt) pair has at most one concert in the dataset.
    - Some upsells may be "orphaned" -- they exist at a venue_id that has no
      matching concert in this dataset. For example, venue 1365 has upsell
      events on 10/24 and 10/25 but no concert; the concerts on those dates
      are at venue 1372. These may represent sub-venues, satellite lots, or
      secondary spaces associated with the main concert venue. The query uses
      a LEFT JOIN from upsells so these are still visible (with NULLs for
      concert columns) for investigation.
    - There is one known data quality issue: event_id 402C88B95432DDBD
      appears twice in events.csv with different venue_id, event_dt, and
      event_name values. This is treated as-is (both rows are included).
    - The event_id column is the shared key between events.csv and
      ticket_sales.csv, enabling sales analysis per event if needed.

================================================================================
*/


-- =============================================================================
-- MAIN QUERY: Associate each concert with its upsell events
-- =============================================================================

WITH concerts AS (
    -- Identify primary concert events by the tour name in event_name.
    -- This is the most reliable discriminator: no upsell event contains
    -- "Super Awesome Tour", and every actual concert does.
    SELECT
        event_id   AS concert_event_id,
        event_name AS concert_event_name,
        venue_id,
        event_dt
    FROM events
    WHERE LOWER(event_name) LIKE '%super awesome tour%'
),
upsells AS (
    -- Everything not identified as a concert is an upsell.
    -- This includes parking, VIP, lounge, coat check, fast lane,
    -- premium seating, blankets, lockers, pre-show passes,
    -- "Upgrades & Extras" bundles, commemorative tickets, etc.
    SELECT
        event_id   AS upsell_event_id,
        event_name AS upsell_event_name,
        venue_id,
        event_dt
    FROM events
    WHERE LOWER(event_name) NOT LIKE '%super awesome tour%'
)

SELECT
    c.concert_event_id,
    c.concert_event_name,
    c.venue_id,
    c.event_dt,
    u.upsell_event_id,
    u.upsell_event_name
FROM concerts c
LEFT JOIN upsells u
    ON  c.venue_id = u.venue_id
    AND c.event_dt = u.event_dt
ORDER BY
    c.event_dt,
    c.venue_id,
    u.upsell_event_name;


/*
================================================================================
  BONUS QUERY: Surface orphaned upsells that have no matching concert
================================================================================

  These are upsell events whose (venue_id, event_dt) does not match any
  concert in the dataset. Useful for data quality checks -- they may indicate
  sub-venues, data entry mismatches, or missing concert records.
*/

SELECT
    u.upsell_event_id,
    u.upsell_event_name,
    u.venue_id,
    u.event_dt
FROM (
    SELECT
        event_id   AS upsell_event_id,
        event_name AS upsell_event_name,
        venue_id,
        event_dt
    FROM events
    WHERE LOWER(event_name) NOT LIKE '%super awesome tour%'
) u
LEFT JOIN (
    SELECT DISTINCT venue_id, event_dt
    FROM events
    WHERE LOWER(event_name) LIKE '%super awesome tour%'
) c
    ON  u.venue_id = c.venue_id
    AND u.event_dt = c.event_dt
WHERE c.venue_id IS NULL
ORDER BY u.event_dt, u.venue_id;
