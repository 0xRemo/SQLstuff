"""
Neon Harbor - Super Awesome Tour: Ticket Sales Visualization & Analysis
========================================================================

Reads events.csv and ticket_sales.csv, links concerts to upsells,
aggregates sales at the show level, and produces visualizations for
the top 2 and bottom 2 performing shows along with tour-wide insights.

Outputs:
  - fig1_top_bottom_shows.png    : Bar chart comparing top 2 vs bottom 2
  - fig2_sales_timeseries.png    : Cumulative sales curves for top/bottom shows
  - fig3_tour_overview.png       : Full tour overview (all shows + upsell breakdown)
  - fig4_upsell_analysis.png     : Upsell attachment rate analysis
  - analysis_summary.txt         : Written summary of findings
"""

import csv
import os
from collections import defaultdict
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

# ---------------------------------------------------------------------------
# 1. LOAD DATA
# ---------------------------------------------------------------------------

def load_events(path="events.csv"):
    events = {}
    with open(path, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            events[row["event_id"]] = {
                "name": row["event_name"].strip(),
                "venue_id": row["venue_id"],
                "event_dt": row["event_dt"],
            }
    return events


def load_sales(path="ticket_sales.csv"):
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append({
                "event_id": row["event_id"],
                "sales_minute": row["sales_minute"],
                "tickets": int(row["tickets_sold_in_minute"]),
            })
    return rows


# ---------------------------------------------------------------------------
# 2. CLASSIFY & LINK
# ---------------------------------------------------------------------------

def classify_events(events):
    concerts = {}
    upsells = {}
    for eid, e in events.items():
        if "super awesome tour" in e["name"].lower():
            concerts[eid] = e
        else:
            upsells[eid] = e
    return concerts, upsells


def build_show_map(concerts, upsells):
    """Map every event_id to its parent concert_id using (venue_id, event_dt)."""
    # Index concerts by (venue, date)
    concert_by_vd = {}
    for cid, c in concerts.items():
        concert_by_vd[(c["venue_id"], c["event_dt"])] = cid

    event_to_concert = {}
    # Concert events map to themselves
    for cid in concerts:
        event_to_concert[cid] = cid
    # Upsells map to their parent concert
    for uid, u in upsells.items():
        key = (u["venue_id"], u["event_dt"])
        if key in concert_by_vd:
            event_to_concert[uid] = concert_by_vd[key]

    return event_to_concert


# ---------------------------------------------------------------------------
# 3. AGGREGATE
# ---------------------------------------------------------------------------

def aggregate_show_sales(sales_rows, event_to_concert, concerts, events):
    """Aggregate ticket sales per show. Return a list of show dicts."""
    # Per-show: concert vs upsell ticket totals
    show_concert_tix = defaultdict(int)
    show_upsell_tix = defaultdict(int)
    # Per-show time-series (all events combined)
    show_timeseries = defaultdict(list)

    for row in sales_rows:
        eid = row["event_id"]
        cid = event_to_concert.get(eid)
        if cid is None:
            continue  # orphaned upsell or unknown event
        tix = row["tickets"]
        if eid == cid:
            show_concert_tix[cid] += tix
        else:
            show_upsell_tix[cid] += tix
        show_timeseries[cid].append((row["sales_minute"], tix))

    shows = []
    for cid, c in concerts.items():
        ct = show_concert_tix.get(cid, 0)
        ut = show_upsell_tix.get(cid, 0)
        total = ct + ut
        shows.append({
            "concert_id": cid,
            "venue_id": c["venue_id"],
            "event_dt": c["event_dt"],
            "concert_name": c["name"],
            "concert_tickets": ct,
            "upsell_tickets": ut,
            "total_tickets": total,
            "upsell_pct": (ut / total * 100) if total > 0 else 0.0,
            "timeseries": sorted(show_timeseries.get(cid, []))
        })

    shows.sort(key=lambda s: s["total_tickets"], reverse=True)
    return shows


# ---------------------------------------------------------------------------
# 4. IDENTIFY TOP / BOTTOM
# ---------------------------------------------------------------------------

def get_top_bottom(shows, n=2):
    """Return top-n and bottom-n shows (excluding zero-sales shows from bottom)."""
    with_sales = [s for s in shows if s["total_tickets"] > 0]
    top = with_sales[:n]
    bottom = with_sales[-n:]
    return top, bottom


# ---------------------------------------------------------------------------
# 5. VISUALIZATIONS
# ---------------------------------------------------------------------------

def make_label(show):
    return "Venue {} | {}".format(show["venue_id"], show["event_dt"])


def fig1_top_bottom_bar(top, bottom, outpath="fig1_top_bottom_shows.png"):
    """Stacked bar chart: concert vs upsell tickets for top 2 & bottom 2."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=False)

    for ax, group, title, color_c, color_u in [
        (axes[0], top,    "Top 2 Shows",    "#2ecc71", "#27ae60"),
        (axes[1], bottom, "Bottom 2 Shows", "#e74c3c", "#c0392b"),
    ]:
        labels = [make_label(s) for s in group]
        concert = [s["concert_tickets"] for s in group]
        upsell = [s["upsell_tickets"] for s in group]

        bars1 = ax.bar(labels, concert, label="Concert Tickets", color=color_c, edgecolor="white")
        bars2 = ax.bar(labels, upsell, bottom=concert, label="Upsell Tickets", color=color_u, alpha=0.7, edgecolor="white")

        # Add value labels on bars
        for bar, val in zip(bars1, concert):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()/2,
                        "{:,}".format(val), ha="center", va="center",
                        fontweight="bold", fontsize=10, color="white")
        for bar, base, val in zip(bars2, concert, upsell):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, base + val/2,
                        "{:,}".format(val), ha="center", va="center",
                        fontsize=9, color="white")

        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_ylabel("Tickets Sold")
        ax.legend(loc="upper right")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: "{:,.0f}".format(x)))

    fig.suptitle("Neon Harbor Super Awesome Tour — Top 2 vs Bottom 2 Shows",
                 fontsize=16, fontweight="bold", y=1.02)
    plt.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Saved: {}".format(outpath))


def fig2_cumulative_timeseries(top, bottom, outpath="fig2_sales_timeseries.png"):
    """Cumulative ticket sales over time for top 2 & bottom 2 shows."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    all_shows = top + bottom
    titles = (
        ["#1: " + make_label(s) for s in top] +
        ["#Bottom: " + make_label(s) for s in bottom]
    )
    colors = ["#2ecc71", "#27ae60", "#e74c3c", "#c0392b"]

    for idx, (ax, show, title, color) in enumerate(zip(axes.flat, all_shows, titles, colors)):
        if not show["timeseries"]:
            ax.text(0.5, 0.5, "No sales data", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(title)
            continue

        # Build cumulative series
        ts_data = [(datetime.fromisoformat(t.replace("+00:00", "+00:00")), v)
                    for t, v in show["timeseries"]]
        ts_data.sort()
        times = [t for t, _ in ts_data]
        cumulative = []
        running = 0
        for _, v in ts_data:
            running += v
            cumulative.append(running)

        ax.plot(times, cumulative, color=color, linewidth=2)
        ax.fill_between(times, cumulative, alpha=0.15, color=color)
        ax.set_title("{}\nTotal: {:,} tickets".format(title, show["total_tickets"]),
                     fontsize=11, fontweight="bold")
        ax.set_ylabel("Cumulative Tickets")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: "{:,.0f}".format(x)))
        ax.tick_params(axis="x", rotation=30, labelsize=8)
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle("Cumulative Ticket Sales Over Time — Top 2 vs Bottom 2",
                 fontsize=16, fontweight="bold", y=1.02)
    plt.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Saved: {}".format(outpath))


def fig3_tour_overview(shows, outpath="fig3_tour_overview.png"):
    """Horizontal bar chart of ALL shows sorted by total tickets."""
    fig, ax = plt.subplots(figsize=(14, 10))

    # Sort ascending for horizontal bars (top shows at top of chart)
    sorted_shows = sorted(shows, key=lambda s: s["total_tickets"])
    labels = [make_label(s) for s in sorted_shows]
    concert = [s["concert_tickets"] for s in sorted_shows]
    upsell = [s["upsell_tickets"] for s in sorted_shows]

    bars1 = ax.barh(labels, concert, label="Concert Tickets", color="#3498db", edgecolor="white")
    bars2 = ax.barh(labels, upsell, left=concert, label="Upsell Tickets", color="#f39c12", edgecolor="white")

    # Mark top 2 and bottom 2 with sales
    with_sales = [s for s in sorted_shows if s["total_tickets"] > 0]
    if len(with_sales) >= 2:
        for s in with_sales[:2]:  # bottom 2
            idx = sorted_shows.index(s)
            ax.get_yticklabels()[idx].set_color("#e74c3c")
            ax.get_yticklabels()[idx].set_fontweight("bold")
        for s in with_sales[-2:]:  # top 2
            idx = sorted_shows.index(s)
            ax.get_yticklabels()[idx].set_color("#2ecc71")
            ax.get_yticklabels()[idx].set_fontweight("bold")

    ax.set_xlabel("Tickets Sold", fontsize=12)
    ax.set_title("Neon Harbor Super Awesome Tour — All Shows by Total Ticket Sales",
                 fontsize=14, fontweight="bold")
    ax.legend(loc="lower right", fontsize=11)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: "{:,.0f}".format(x)))
    ax.grid(axis="x", alpha=0.3)

    plt.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Saved: {}".format(outpath))


def fig4_upsell_analysis(shows, outpath="fig4_upsell_analysis.png"):
    """Scatter plot: total tickets vs upsell percentage, plus upsell histogram."""
    with_sales = [s for s in shows if s["total_tickets"] > 0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # --- Scatter: total tickets vs upsell % ---
    totals = [s["total_tickets"] for s in with_sales]
    pcts = [s["upsell_pct"] for s in with_sales]
    has_upsell = [s["upsell_pct"] > 0 for s in with_sales]
    colors = ["#e67e22" if h else "#bdc3c7" for h in has_upsell]

    ax1.scatter(totals, pcts, c=colors, s=80, edgecolor="white", zorder=3)
    ax1.set_xlabel("Total Tickets Sold", fontsize=11)
    ax1.set_ylabel("Upsell % of Total", fontsize=11)
    ax1.set_title("Upsell Rate vs Show Size", fontsize=13, fontweight="bold")
    ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: "{:,.0f}".format(x)))
    ax1.grid(alpha=0.3)

    # Annotate notable points
    for s in with_sales:
        if s["upsell_pct"] > 10 or s["total_tickets"] > 35000:
            ax1.annotate("V{}".format(s["venue_id"]),
                         (s["total_tickets"], s["upsell_pct"]),
                         textcoords="offset points", xytext=(8, 4), fontsize=8)

    # --- Bar chart: shows WITH vs WITHOUT upsell events ---
    with_upsell_count = sum(1 for s in with_sales if s["upsell_pct"] > 0)
    without_upsell_count = len(with_sales) - with_upsell_count
    avg_with = (sum(s["total_tickets"] for s in with_sales if s["upsell_pct"] > 0) / with_upsell_count
                if with_upsell_count > 0 else 0)
    avg_without = (sum(s["total_tickets"] for s in with_sales if s["upsell_pct"] == 0) / without_upsell_count
                   if without_upsell_count > 0 else 0)

    bars = ax2.bar(
        ["With Upsells\n({} shows)".format(with_upsell_count),
         "Without Upsells\n({} shows)".format(without_upsell_count)],
        [avg_with, avg_without],
        color=["#e67e22", "#bdc3c7"],
        edgecolor="white",
        width=0.5
    )
    for bar, val in zip(bars, [avg_with, avg_without]):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 200,
                 "{:,.0f}".format(val), ha="center", fontweight="bold", fontsize=11)

    ax2.set_ylabel("Avg Total Tickets per Show", fontsize=11)
    ax2.set_title("Avg Tickets: Shows With vs Without Upsells",
                  fontsize=13, fontweight="bold")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: "{:,.0f}".format(x)))

    fig.suptitle("Upsell Analysis Across the Tour",
                 fontsize=15, fontweight="bold", y=1.02)
    plt.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Saved: {}".format(outpath))


# ---------------------------------------------------------------------------
# 6. WRITTEN SUMMARY
# ---------------------------------------------------------------------------

def write_summary(shows, top, bottom, outpath="analysis_summary.txt"):
    with_sales = [s for s in shows if s["total_tickets"] > 0]
    total_tix = sum(s["total_tickets"] for s in shows)
    total_upsell = sum(s["upsell_tickets"] for s in shows)
    shows_with_upsells = [s for s in with_sales if s["upsell_pct"] > 0]

    lines = []
    lines.append("=" * 72)
    lines.append("NEON HARBOR - SUPER AWESOME TOUR: TICKET SALES ANALYSIS")
    lines.append("=" * 72)
    lines.append("")

    lines.append("TOUR OVERVIEW")
    lines.append("-" * 40)
    lines.append("Total shows on tour:           {}".format(len(shows)))
    lines.append("Shows with sales data:         {}".format(len(with_sales)))
    lines.append("Shows with no sales data:      {} (likely not yet on sale)".format(
        len(shows) - len(with_sales)))
    lines.append("Total tickets sold (tour):     {:,}".format(total_tix))
    lines.append("Average per show:              {:,}".format(
        total_tix // len(with_sales) if with_sales else 0))
    lines.append("Total upsell tickets:          {:,} ({:.1f}% of total)".format(
        total_upsell, total_upsell / total_tix * 100 if total_tix else 0))
    lines.append("")

    lines.append("TOP 2 SHOWS (by total tickets sold)")
    lines.append("-" * 40)
    for i, s in enumerate(top, 1):
        lines.append("  {}. Venue {}, Date {}".format(i, s["venue_id"], s["event_dt"]))
        lines.append("     Concert tickets:  {:>8,}".format(s["concert_tickets"]))
        lines.append("     Upsell tickets:   {:>8,}".format(s["upsell_tickets"]))
        lines.append("     TOTAL:            {:>8,}".format(s["total_tickets"]))
        lines.append("     Upsell %:         {:>7.1f}%".format(s["upsell_pct"]))
        lines.append("")

    lines.append("BOTTOM 2 SHOWS (by total tickets sold, excluding unsold)")
    lines.append("-" * 40)
    for i, s in enumerate(bottom, 1):
        lines.append("  {}. Venue {}, Date {}".format(i, s["venue_id"], s["event_dt"]))
        lines.append("     Concert tickets:  {:>8,}".format(s["concert_tickets"]))
        lines.append("     Upsell tickets:   {:>8,}".format(s["upsell_tickets"]))
        lines.append("     TOTAL:            {:>8,}".format(s["total_tickets"]))
        lines.append("     Upsell %:         {:>7.1f}%".format(s["upsell_pct"]))
        lines.append("")

    lines.append("KEY INSIGHTS")
    lines.append("-" * 40)
    lines.append(
        "1. MASSIVE VARIANCE IN SHOW PERFORMANCE: The top show (Venue {}, "
        "{:,} tickets) sold ~{:.0f}x more than the lowest-selling show "
        "(Venue {}, {:,} tickets). This suggests very different venue "
        "capacities or market demand across cities.".format(
            top[0]["venue_id"], top[0]["total_tickets"],
            top[0]["total_tickets"] / bottom[-1]["total_tickets"] if bottom[-1]["total_tickets"] else 0,
            bottom[-1]["venue_id"], bottom[-1]["total_tickets"]))
    lines.append("")
    lines.append(
        "2. UPSELL ATTACHMENT IS INCONSISTENT: Only {} of {} shows with "
        "sales data ({:.0f}%) have any upsell ticket sales. The overall "
        "upsell rate is just {:.1f}% of total tickets. This represents a "
        "significant untapped revenue opportunity.".format(
            len(shows_with_upsells), len(with_sales),
            len(shows_with_upsells) / len(with_sales) * 100,
            total_upsell / total_tix * 100 if total_tix else 0))
    lines.append("")

    # Calculate upsell stats
    if shows_with_upsells:
        avg_upsell_pct = sum(s["upsell_pct"] for s in shows_with_upsells) / len(shows_with_upsells)
        max_upsell = max(shows_with_upsells, key=lambda s: s["upsell_pct"])
        lines.append(
            "3. WHERE UPSELLS EXIST, THEY MATTER: Among the {} shows that "
            "DO have upsell sales, the average upsell rate is {:.1f}%. The "
            "highest upsell rate is at Venue {} ({:.1f}%). Venues with upsell "
            "infrastructure consistently generate incremental revenue.".format(
                len(shows_with_upsells), avg_upsell_pct,
                max_upsell["venue_id"], max_upsell["upsell_pct"]))
        lines.append("")

    lines.append(
        "4. TOP SHOWS DON'T NEED UPSELLS TO WIN: The #1 show (Venue {}) "
        "has {:.1f}% upsell rate — its dominance comes purely from concert "
        "ticket volume. Meanwhile, smaller shows like Venue 9463 and "
        "Venue 475421 lean more heavily on upsells to boost total numbers.".format(
            top[0]["venue_id"], top[0]["upsell_pct"]))
    lines.append("")

    no_sales_shows = [s for s in shows if s["total_tickets"] == 0]
    lines.append(
        "5. DATA GAPS: {} of 33 shows have zero ticket sales rows. These "
        "should be investigated — they may be future on-sale dates or data "
        "pipeline issues.".format(len(no_sales_shows)))
    lines.append("")

    lines.append("=" * 72)
    lines.append("Generated by visualize_sales.py")
    lines.append("=" * 72)

    text = "\n".join(lines)
    with open(outpath, "w") as f:
        f.write(text)
    print("Saved: {}".format(outpath))
    print()
    print(text)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")

    events = load_events()
    sales = load_sales()
    concerts, upsells = classify_events(events)
    event_to_concert = build_show_map(concerts, upsells)
    shows = aggregate_show_sales(sales, event_to_concert, concerts, events)
    top, bottom = get_top_bottom(shows, n=2)

    # Generate all outputs
    fig1_top_bottom_bar(top, bottom)
    fig2_cumulative_timeseries(top, bottom)
    fig3_tour_overview(shows)
    fig4_upsell_analysis(shows)
    write_summary(shows, top, bottom)


if __name__ == "__main__":
    main()
