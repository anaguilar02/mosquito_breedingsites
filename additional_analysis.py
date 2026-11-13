"""Additional analyses for the storm drain breeding sites preprint.

Reads breeding_sites.csv (Mosquito Alert storm drain records) and produces
  figures/temporal_patterns.png   reports per year and per calendar month
  figures/shares_with_ci.png      shares with water / with larvae, 95% Wilson intervals
and prints the numbers quoted in the text.
"""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CSV = sys.argv[1] if len(sys.argv) > 1 else "breeding_sites.csv"
BLUE, ORANGE, GREY = "#4C78A8", "#F58518", "#9A9A9A"


def wilson(x, n, z=1.96):
    p = x / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, c - h, c + h


d = pd.read_csv(CSV, low_memory=False)
d["tl"] = pd.to_datetime(d["created_at_local"], format="ISO8601")
d["country"] = d["location.country.name_en"]
d["year"], d["month"] = d.tl.dt.year, d.tl.dt.month
N = len(d)
print("records", N, "users", d.user_uuid.nunique(), "countries", d.country.nunique())
print("first/last", d.tl.min(), d.tl.max())

# ---- field completeness -------------------------------------------------
print(pd.crosstab(d.has_water, d.has_larvae.fillna("missing"), margins=True))
for a, b in [(2014, 2020), (2021, 2025), (2026, 2026)]:
    s = d[d.year.between(a, b)]
    w, dry = s[s.has_water], s[~s.has_water]
    print(a, b, "records", len(s), "water", len(w), "dry", len(dry),
          "larvae info: water", w.has_larvae.notna().sum(), "dry", dry.has_larvae.notna().sum())
print("larvae field last recorded before gap:", d[d.has_larvae.notna() & (d.year <= 2025)].tl.max())
print("larvae field first recorded in 2026:", d[d.has_larvae.notna() & (d.year == 2026)].tl.min())

# ---- temporal concentration ---------------------------------------------
print("Apr-Jun share %.3f  May share %.3f" % (d.month.isin([4, 5, 6]).mean(), (d.month == 5).mean()))
print("weekday share %.3f" % (d.tl.dt.dayofweek < 5).mean())
print("2021-2023 share %.3f" % d.year.between(2021, 2023).mean())
day = d.groupby(d.tl.dt.date).agg(n=("uuid", "size"), users=("user_uuid", "nunique")).sort_values("n", ascending=False)
print("active days", len(day), "top 50 share %.3f top 100 share %.3f" % (day.n.head(50).sum() / N, day.n.head(100).sum() / N))
print(day.head(5))
es = d[d.country == "Spain"]
camp = es.month.isin([4, 5, 6])
print("Spain water share Apr-Jun %.3f (n=%d), other months %.3f (n=%d)" %
      (es[camp].has_water.mean(), camp.sum(), es[~camp].has_water.mean(), (~camp).sum()))
parts = es["location.display_name"].str.split(", ")
print("Barcelona municipality", (parts.str[0] == "Barcelona").sum(), "Catalonia", (parts.str[-2] == "Cataluña").sum())
u = d.groupby("user_uuid").size().sort_values(ascending=False)
print("users with one report %.3f, median %.0f, top 10 users share %.3f" % ((u == 1).mean(), u.median(), u.head(10).sum() / N))

# ---- most reported coordinate -------------------------------------------
d["la"], d["lo"] = d["location.point.latitude"].round(3), d["location.point.longitude"].round(3)
(la, lo), n_top = d.groupby(["la", "lo"]).size().idxmax(), d.groupby(["la", "lo"]).size().max()
s = d[(d.la == la) & (d.lo == lo)]
print("top coordinate", la, lo, n_top, s["location.display_name"].iloc[0], "users", s.user_uuid.nunique(),
      "days", s.tl.dt.date.nunique(), "distinct exact points",
      len(s[["location.point.latitude", "location.point.longitude"]].drop_duplicates()),
      "dry", (~s.has_water).sum())
print(s.tl.dt.date.value_counts().sort_index())

# ---- shares with intervals ----------------------------------------------
g = d.groupby("country").agg(n=("uuid", "size"), water=("has_water", "sum")).sort_values("n", ascending=False)
g = g[g.n >= 20]
rows = [("All records", d.has_water.sum(), N)] + [(c, r.water, r.n) for c, r in g.iterrows()]
k = d[d.has_larvae.notna() & d.has_water].copy()
k["larv"] = k.has_larvae.astype(bool)
groups = [("All", k), ("Spain", k[k.country == "Spain"]), ("Outside Spain", k[k.country != "Spain"]),
          ("2014-2021", k[k.year <= 2021]), ("2026", k[k.year == 2026])]
for name, x, n in rows:
    print("water  %-18s %5d/%5d  %.3f [%.3f, %.3f]" % ((name, x, n) + wilson(x, n)))
for name, s_ in groups:
    print("larvae %-18s %5d/%5d  %.3f [%.3f, %.3f]" % ((name, s_.larv.sum(), len(s_)) + wilson(s_.larv.sum(), len(s_))))

plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})

# Figure: temporal patterns
fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
yr = d.groupby("year").size().reindex(range(2014, 2027), fill_value=0)
ax[0].bar(yr.index, yr.values, color=BLUE)
for x, v in yr.items():
    ax[0].text(x, v + 40, f"{v:,}", ha="center", fontsize=8.5)
ax[0].set_xticks(yr.index)
ax[0].set_xticklabels([str(y)[2:] for y in yr.index])
ax[0].set_xlabel("Year (20xx; 2026 through 16 August)")
ax[0].set_ylabel("Number of reports")
ax[0].set_title("Reports per year", loc="left", fontweight="bold")
mo = d.groupby("month").size().reindex(range(1, 13), fill_value=0)
ax[1].bar(mo.index, mo.values, color=[ORANGE if m in (4, 5, 6) else BLUE for m in mo.index])
for x, v in mo.items():
    ax[1].text(x, v + 100, f"{v:,}", ha="center", fontsize=8.5)
ax[1].set_xticks(mo.index)
ax[1].set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
ax[1].set_ylabel("Number of reports")
ax[1].set_title("Reports per calendar month, all years", loc="left", fontweight="bold")
fig.tight_layout()
fig.savefig("figures/temporal_patterns.png", dpi=200)

# Figure: shares with 95% Wilson intervals
fig, ax = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [1.25, 1]})


def dotplot(a, items, title, xlabel):
    y = np.arange(len(items))[::-1]
    for yi, (name, x, n) in zip(y, items):
        p, lo_, hi_ = wilson(x, n)
        a.plot([100 * lo_, 100 * hi_], [yi, yi], color=GREY, lw=2, zorder=1)
        a.scatter([100 * p], [yi], color=BLUE, s=45, zorder=2)
        a.text(101, yi, f"{100 * p:.1f}%  (n = {n:,})", va="center", fontsize=9)
    a.set_yticks(y)
    a.set_yticklabels([i[0] for i in items])
    a.set_xlim(0, 135)
    a.set_xticks(range(0, 101, 20))
    a.set_xlabel(xlabel)
    a.set_title(title, loc="left", fontweight="bold")
    a.grid(axis="x", color="#E6E6E6", zorder=0)


dotplot(ax[0], rows, "Storm drains reported with water", "Share of reports with water (%)")
dotplot(ax[1], [(nm, s_.larv.sum(), len(s_)) for nm, s_ in groups],
        "Larvae among drains with water", "Share with larvae (%)")
fig.tight_layout()
fig.savefig("figures/shares_with_ci.png", dpi=200)
