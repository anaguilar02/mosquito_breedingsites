"""Map of storm drain reports in Spain with a detail of Barcelona.

Reads breeding_sites.csv and the boundary files in basemap/ and writes
figures/spain_barcelona_map.png.

Boundaries: Natural Earth 1:10m (provinces, neighbouring countries; public
domain) and the district limits of Barcelona from the Ajuntament de Barcelona
open data, via github.com/martgnz/bcn-geodata.
"""
import json
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import PowerNorm
from matplotlib.patches import Rectangle

CSV = sys.argv[1] if len(sys.argv) > 1 else "breeding_sites.csv"
SPAIN = (-9.7, 4.7, 35.7, 44.1)          # lon min, lon max, lat min, lat max
BCN = (2.045, 2.235, 41.315, 41.475)
CMAP = plt.get_cmap("plasma_r")


def rings(path):
    for f in json.load(open(path))["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            yield f["properties"]["name"], np.asarray(poly[0])


def draw(ax, path, face, edge, lw, z):
    for _, r in rings(path):
        ax.fill(r[:, 0], r[:, 1], facecolor=face, edgecolor=edge, linewidth=lw, zorder=z)


def frame(ax, ext):
    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(ext[2], ext[3])
    ax.set_aspect(1 / np.cos(np.radians((ext[2] + ext[3]) / 2)))
    ax.set_facecolor("#EAF2F8")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#888888")


def bubbles(ax, g, norm, smin, sscale):
    g = g.sort_values("n")
    return ax.scatter(g.lon, g.lat, s=smin + sscale * np.sqrt(g.n), c=g.n, cmap=CMAP, norm=norm,
                      edgecolor="white", linewidth=0.3, alpha=0.9, zorder=5)


d = pd.read_csv(CSV, low_memory=False)
d = d[d["location.country.name_en"] == "Spain"].copy()
d["lat"], d["lon"] = d["location.point.latitude"], d["location.point.longitude"]
in_frame = d.lon.between(SPAIN[0], SPAIN[1]) & d.lat.between(SPAIN[2], SPAIN[3])
print("Spain records", len(d), "outside frame (Canary Islands)", (~in_frame).sum())

# left panel: 0.1 degree cells; right panel: coordinates rounded to 3 decimals
cell = 0.1
d["clat"], d["clon"] = (np.floor(d.lat / cell) + 0.5) * cell, (np.floor(d.lon / cell) + 0.5) * cell
gs = d[in_frame].groupby(["clat", "clon"]).size().rename("n").reset_index().rename(columns={"clat": "lat", "clon": "lon"})
b = d[d.lon.between(BCN[0], BCN[1]) & d.lat.between(BCN[2], BCN[3])].copy()
b["rlat"], b["rlon"] = b.lat.round(3), b.lon.round(3)
gb = b.groupby(["rlat", "rlon"]).size().rename("n").reset_index().rename(columns={"rlat": "lat", "rlon": "lon"})
print("cells", len(gs), "max per cell", gs.n.max(), "cells holding half the records",
      (gs.n.sort_values(ascending=False).cumsum() < gs.n.sum() / 2).sum() + 1)
print("Barcelona panel: records", len(b), "coordinates", len(gb), "max", gb.n.max(),
      "share of Spain %.3f" % (len(b) / len(d)))
muni = d["location.display_name"].str.split(", ").str[0]
print("Barcelona municipality records", (muni == "Barcelona").sum(), "of which in panel",
      ((muni == "Barcelona") & d.index.isin(b.index)).sum())

fig, ax = plt.subplots(1, 2, figsize=(14, 6.6), gridspec_kw={"width_ratios": [1.45, 1]})

frame(ax[0], SPAIN)
draw(ax[0], "basemap/neighbours_ne10m.geojson", "#F4F4F4", "#BBBBBB", 0.5, 1)
draw(ax[0], "basemap/spain_provinces_ne10m.geojson", "#FFFFFF", "#C4C4C4", 0.45, 2)
n0 = PowerNorm(0.35, vmin=1, vmax=gs.n.max())
sc0 = bubbles(ax[0], gs, n0, 6, 7)
ax[0].add_patch(Rectangle((BCN[0], BCN[2]), BCN[1] - BCN[0], BCN[3] - BCN[2], fill=False,
                          edgecolor="black", linewidth=1.1, zorder=6))
ax[0].annotate("Barcelona\n(right panel)", xy=(BCN[1], BCN[2]), xytext=(3.0, 39.9), fontsize=9.5, ha="center",
               arrowprops=dict(arrowstyle="-", color="black", lw=0.8), zorder=7)
ax[0].set_title(f"Spain: {in_frame.sum():,} storm drain reports", loc="left", fontweight="bold")
cb = fig.colorbar(sc0, ax=ax[0], orientation="horizontal", fraction=0.04, pad=0.03, aspect=40,
                  ticks=[1, 10, 50, 200, 1000, 3000])
cb.set_label("Reports per 0.1° cell", fontsize=9.5)

frame(ax[1], BCN)
draw(ax[1], "basemap/spain_provinces_ne10m.geojson", "#F4F4F4", "#C4C4C4", 0.45, 1)
draw(ax[1], "basemap/barcelona_districts.geojson", "#FFFFFF", "#9A9A9A", 0.7, 2)
from matplotlib.path import Path
pts = b[["lon", "lat"]].to_numpy()
b["district"] = None
for name, r in rings("basemap/barcelona_districts.geojson"):
    b.loc[Path(r).contains_points(pts) & b.district.isna().to_numpy(), "district"] = name
print(b.district.fillna("outside the municipality").value_counts())
n1 = PowerNorm(0.5, vmin=1, vmax=gb.n.max())
sc1 = bubbles(ax[1], gb, n1, 3, 4)
km = 2 / (111.32 * np.cos(np.radians(41.4)))
x0, y0 = BCN[1] - 0.012 - km, BCN[2] + 0.008
ax[1].plot([x0, x0 + km], [y0, y0], color="black", lw=2, zorder=7)
ax[1].text(x0 + km / 2, y0 + 0.003, "2 km", ha="center", fontsize=9, zorder=7)
ax[1].set_title(f"Barcelona: {len(b):,} reports at {len(gb):,} coordinates", loc="left", fontweight="bold")
cb = fig.colorbar(sc1, ax=ax[1], orientation="horizontal", fraction=0.04, pad=0.03, aspect=30,
                  ticks=[1, 5, 10, 25, 50, 97])
cb.set_label("Reports per coordinate (rounded to 3 decimals)", fontsize=9.5)

fig.tight_layout()
fig.savefig("figures/spain_barcelona_map.png", dpi=200, bbox_inches="tight", pad_inches=0.1)
