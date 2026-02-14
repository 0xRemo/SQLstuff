"""
Upsell Rate by Venue - Bar Chart
=================================
Loads events.csv and ticket_sales.csv into an in-memory SQLite database,
runs the upsell-rate query, and produces a horizontal bar chart ordered
by the number of upsell options each venue offers.
"""

import sqlite3
import csv
import matplotlib.pyplot as plt


def load_csv_to_table(cursor, csv_path, table_name):
    """Read a CSV file and insert its rows into a SQLite table."""
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = next(reader)
        cols = ", ".join(headers)
        placeholders = ", ".join("?" for _ in headers)
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} ({cols})"
        )
        for row in reader:
            cursor.execute(
                f"INSERT INTO {table_name} VALUES ({placeholders})", row
            )


QUERY = """
WITH concerts AS (
    SELECT event_id, venue_id, event_dt
    FROM events
    WHERE LOWER(event_name) LIKE '%super awesome tour%'
),
upsells AS (
    SELECT event_id, event_name, venue_id, event_dt
    FROM events
    WHERE LOWER(event_name) NOT LIKE '%super awesome tour%'
),
matched_upsells AS (
    SELECT u.event_id, u.event_name, c.venue_id
    FROM upsells u
    INNER JOIN concerts c
        ON u.venue_id = c.venue_id AND u.event_dt = c.event_dt
),
concert_sales AS (
    SELECT c.venue_id, SUM(ts.tickets_sold_in_minute) AS concert_tickets
    FROM concerts c
    INNER JOIN ticket_sales ts ON c.event_id = ts.event_id
    GROUP BY c.venue_id
),
upsell_sales AS (
    SELECT
        mu.venue_id,
        COUNT(DISTINCT mu.event_name) AS upsell_options,
        SUM(ts.tickets_sold_in_minute) AS upsell_tickets
    FROM matched_upsells mu
    INNER JOIN ticket_sales ts ON mu.event_id = ts.event_id
    GROUP BY mu.venue_id
)
SELECT
    cs.venue_id,
    cs.concert_tickets,
    COALESCE(us.upsell_tickets, 0)  AS upsell_tickets,
    COALESCE(us.upsell_options, 0)  AS upsell_options,
    ROUND(COALESCE(us.upsell_tickets, 0) * 100.0 / cs.concert_tickets, 2)
        AS upsell_rate_pct
FROM concert_sales cs
LEFT JOIN upsell_sales us ON cs.venue_id = us.venue_id
WHERE cs.concert_tickets > 0
ORDER BY upsell_options DESC, upsell_rate_pct DESC;
"""


def main():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    load_csv_to_table(cur, "events.csv", "events")
    load_csv_to_table(cur, "ticket_sales.csv", "ticket_sales")
    conn.commit()

    rows = cur.execute(QUERY).fetchall()
    conn.close()

    venue_ids = [str(r[0]) for r in rows]
    upsell_rates = [r[4] for r in rows]
    upsell_options = [r[3] for r in rows]

    # Build labels: "Venue <id> (N options)"
    labels = [f"Venue {v} ({n} opts)" for v, n in zip(venue_ids, upsell_options)]

    fig, ax = plt.subplots(figsize=(10, max(6, len(labels) * 0.4)))
    bars = ax.barh(labels, upsell_rates, color="#4a90d9", edgecolor="white")

    ax.set_xlabel("Upsell Rate (%)")
    ax.set_title("Upsell Rate by Venue\n(ordered by number of upsell options offered)")
    ax.invert_yaxis()  # highest option-count venue at top

    # Annotate each bar with the percentage
    for bar, rate in zip(bars, upsell_rates):
        ax.text(
            bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
            f"{rate}%", va="center", fontsize=9
        )

    plt.tight_layout()
    plt.savefig("upsell_rate_by_venue.png", dpi=150)
    print("Chart saved to upsell_rate_by_venue.png")
    plt.show()


if __name__ == "__main__":
    main()
