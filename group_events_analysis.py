"""Group events, participants, and larvae in the storm drain reports.

Reads breeding_sites.csv and writes figures/group_events_and_larvae.png.
A group event is a municipality and local calendar day with reports from at
least MIN_USERS different users. Prints the numbers quoted in the text.
"""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CSV = sys.argv[1] if len(sys.argv) > 1 else "breeding_sites.csv"
MIN_USERS = 5
BLUE, ORANGE, GREY = "#4C78A8", "#F58518", "#9A9A9A"
SEASONS = [("Dec-Mar", [12, 1, 2, 3]), ("Apr-Jun", [4, 5, 6]), ("Jul-Sep", [7, 8, 9]), ("Oct-Nov", [10, 11])]


def wilson(x, n, z=1.96):
    p = x / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, c - h, c + h


def show(label, x, n):
    if n == 0:
        print("%-42s no records" % label)
        return
    p, lo, hi = wilson(x, n)
    print("%-42s %5d/%5d  %5.1f%% [%.1f, %.1f]" % (label, x, n, 100 * p, 100 * lo, 100 * hi))


d = pd.read_csv(CSV, low_memory=False)
d["tl"] = pd.to_datetime(d["created_at_local"], format="ISO8601")
d["date"], d["month"], d["year"] = d.tl.dt.date, d.tl.dt.month, d.tl.dt.year
d["place"] = d["location.display_name"]
d["spain"] = d["location.country.name_en"] == "Spain"
N = len(d)

# ---- group events --------------------------------------------------------
ev = d.groupby(["date", "place"]).agg(n=("uuid", "size"), users=("user_uuid", "nunique"))
d = d.join(ev.users.rename("ev_users"), on=["date", "place"])
for k in (3, 5, 10):
    m = d.ev_users >= k
    print("threshold %2d users: events %d, records %d (%.1f%%), water share %.1f%% vs %.1f%%" %
          (k, (ev.users >= k).sum(), m.sum(), 100 * m.mean(), 100 * d[m].has_water.mean(), 100 * d[~m].has_water.mean()))
d["group"] = d.ev_users >= MIN_USERS
g_ev = ev[ev.users >= MIN_USERS]
print("group events:", len(g_ev), "median users", g_ev.users.median(), "median reports", g_ev.n.median(),
      "municipalities", g_ev.reset_index().place.nunique())
for name, s in [("group", d[d.group]), ("other", d[~d.group])]:
    print("%-6s records %5d | weekdays %.1f%% | Apr-Jun %.1f%% | 08:00-14:59 %.1f%% | Spain %.1f%%" %
          (name, len(s), 100 * (s.tl.dt.dayofweek < 5).mean(), 100 * s.month.isin([4, 5, 6]).mean(),
           100 * s.tl.dt.hour.between(8, 14).mean(), 100 * s.spain.mean()))
print("group share of records by year:", d.groupby("year").group.mean().round(2).to_dict())
show("water | group events", d[d.group].has_water.sum(), d.group.sum())
show("water | other reports", d[~d.group].has_water.sum(), (~d.group).sum())
es = d[d.spain]
show("water | Spain, other reports", es[~es.group].has_water.sum(), (~es.group).sum())
show("water | outside Spain", d[~d.spain].has_water.sum(), (~d.spain).sum())

# ---- participants --------------------------------------------------------
u = d.groupby("user_uuid").agg(n=("uuid", "size"), days=("date", "nunique"), years=("year", "nunique"),
                               group=("group", "max"))
top = u.n.sort_values(ascending=False)
print("users %d | one day only %.1f%% | more than one year %.1f%% | one report %.1f%% | median %d | "
      "top 10%% of users hold %.1f%% of reports | users in a group event %.1f%%" %
      (len(u), 100 * (u.days == 1).mean(), 100 * (u.years > 1).mean(), 100 * (u.n == 1).mean(), u.n.median(),
       100 * top.head(int(round(len(u) / 10))).sum() / N, 100 * u.group.mean()))

# ---- larvae among drains with water --------------------------------------
k = d[d.has_larvae.notna() & d.has_water].copy()
k["larv"] = k.has_larvae.astype(bool)
show("larvae | group events", k[k.group].larv.sum(), k.group.sum())
show("larvae | other reports", k[~k.group].larv.sum(), (~k.group).sum())
ks = k[k.spain]
show("larvae | Spain, other reports", ks[~ks.group].larv.sum(), (~ks.group).sum())
show("larvae | outside Spain", k[~k.spain].larv.sum(), (~k.spain).sum())
season_rows = {}
for name, months in SEASONS:
    s = k[k.month.isin(months)]
    show("larvae | " + name, s.larv.sum(), len(s))
    for lab, ss in [("group", s[s.group]), ("other", s[~s.group])]:
        show("larvae | %s, %s" % (name, lab), ss.larv.sum(), len(ss))
        season_rows[(name, lab)] = (ss.larv.sum(), len(ss))

# ---- adult mosquitoes nearby ---------------------------------------------
q = d[d.has_near_mosquitoes.notna()].copy()
q["near"] = q.has_near_mosquitoes.astype(bool)
print("mosquitoes-nearby field: records", len(q), "years", q.year.min(), q.year.max(), q.groupby("year").size().to_dict())
show("water | mosquitoes nearby", q[q.near].has_water.sum(), q.near.sum())
show("water | no mosquitoes nearby", q[~q.near].has_water.sum(), (~q.near).sum())
kq = k[k.has_near_mosquitoes.notna()].copy()
kq["near"] = kq.has_near_mosquitoes.astype(bool)
near_rows = {}
for lab, s in [("all", kq), ("group", kq[kq.group]), ("other", kq[~kq.group])]:
    for nm, ss in [("yes", s[s.near]), ("no", s[~s.near])]:
        show("larvae | nearby %s, %s" % (nm, lab), ss.larv.sum(), len(ss))
        near_rows[(lab, nm)] = (ss.larv.sum(), len(ss))

# ---- figure ---------------------------------------------------------------
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 3, figsize=(15, 4.6), gridspec_kw={"width_ratios": [1, 1.25, 1]})


def point(a, y, x, n, color, label=True):
    p, lo, hi = wilson(x, n)
    a.plot([100 * lo, 100 * hi], [y, y], color=GREY, lw=2, zorder=1)
    a.scatter([100 * p], [y], color=color, s=48, zorder=2)
    if label:
        a.text(100 * hi + 2, y, f"{100 * p:.0f}%  (n = {n:,})", va="center", fontsize=8.5)


def finish(a, yticks, labels, title, xlabel, xmax=100):
    a.set_yticks(yticks)
    a.set_yticklabels(labels)
    a.set_xlim(0, xmax)
    a.set_xlabel(xlabel)
    a.set_title(title, loc="left", fontweight="bold")
    a.grid(axis="x", color="#E6E6E6", zorder=0)


point(ax[0], 1, d[d.group].has_water.sum(), d.group.sum(), ORANGE)
point(ax[0], 0, d[~d.group].has_water.sum(), (~d.group).sum(), BLUE)
ax[0].set_ylim(-0.7, 1.7)
finish(ax[0], [1, 0], ["Group events", "Other reports"], "Drains reported with water", "Share with water (%)")

for i, (name, _) in enumerate(SEASONS):
    y = len(SEASONS) - 1 - i
    xg, ng = season_rows[(name, "group")]
    xo, no = season_rows[(name, "other")]
    if ng >= 20:
        point(ax[1], y + 0.17, xg, ng, ORANGE)
    point(ax[1], y - 0.17, xo, no, BLUE)
ax[1].scatter([], [], color=ORANGE, s=48, label="Group events")
ax[1].scatter([], [], color=BLUE, s=48, label="Other reports")
ax[1].legend(frameon=False, fontsize=9, loc="lower right")
ax[1].set_ylim(-0.7, len(SEASONS) - 0.3)
finish(ax[1], range(len(SEASONS) - 1, -1, -1), [s[0].replace("-", "\u2013") for s in SEASONS],
       "Larvae among drains with water, by season", "Share with larvae (%)")

point(ax[2], 1, *near_rows[("all", "yes")], BLUE)
point(ax[2], 0, *near_rows[("all", "no")], BLUE)
ax[2].set_ylim(-0.7, 1.7)
finish(ax[2], [1, 0], ["Adult mosquitoes\nnearby", "No adult\nmosquitoes nearby"],
       "Larvae among drains with water", "Share with larvae (%)")

fig.tight_layout()
fig.savefig("figures/group_events_and_larvae.png", dpi=200, bbox_inches="tight", pad_inches=0.1)
