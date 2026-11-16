
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, PowerNorm

df = pd.read_csv('breeding_sites.csv')

df['latitude'] = pd.to_numeric(
    df['location.point.latitude'], errors='coerce'
)
df['longitude'] = pd.to_numeric(
    df['location.point.longitude'], errors='coerce'
)

df = df.dropna(subset=['latitude', 'longitude']).copy()

df['lat3'] = df['latitude'].round(3)
df['lon3'] = df['longitude'].round(3)

g = (
    df.groupby(['lat3', 'lon3'])
      .size()
      .reset_index(name='n')
      .sort_values('n')
      .reset_index(drop=True)
)

print(
    f'Records: {len(df):,} | '
    f'Unique coordinates: {len(g):,}'
)

countries = (
    df.groupby('location.country.name_en')
      .agg(
          n=('lat3', 'size'),
          lat=('lat3', 'median'),
          lon=('lon3', 'median')
      )
      .sort_values('n', ascending=False)
)

_PLEN = [
    1.0000, 0.9986, 0.9954, 0.9900, 0.9822,
    0.9730, 0.9600, 0.9427, 0.9216, 0.8962,
    0.8679, 0.8350, 0.7986, 0.7597, 0.7186,
    0.6732, 0.6213, 0.5722, 0.5322
]

_PDFE = [
    0.0000, 0.0620, 0.1240, 0.1860, 0.2480,
    0.3100, 0.3720, 0.4340, 0.4958, 0.5571,
    0.6176, 0.6769, 0.7346, 0.7903, 0.8435,
    0.8936, 0.9394, 0.9761, 1.0000
]

_LATS = np.arange(0, 95, 5)


def robinson(lon, lat):
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)

    abs_lat = np.abs(lat)

    plen = np.interp(abs_lat, _LATS, _PLEN)
    pdfe = np.interp(abs_lat, _LATS, _PDFE)

    x = 0.8487 * plen * np.radians(lon)
    y = 1.3523 * pdfe * np.sign(lat)

    return x, y


BG = '#f4efe6'
OCEAN = '#dfe9ee'
INK = '#1f2a37'
MUTED = '#6b7686'
GRID = '#c3d0d8'

CMAP = LinearSegmentedColormap.from_list(
    'breeding_sites',
    ['#f2c14e', '#f78154', '#d1495b', '#8c1c4b', '#3b0f3f']
)

NORM = PowerNorm(
    gamma=0.5,
    vmin=1,
    vmax=g['n'].max()
)

plt.rcParams['font.family'] = 'DejaVu Sans'


def marker_size(n, k=1.0):
    return k * (6 + 16 * np.sqrt(n))


def load_land():
    try:
        import cartopy.io.shapereader as shpreader

        path = shpreader.natural_earth(
            resolution='50m',
            category='physical',
            name='land'
        )

        return list(shpreader.Reader(path).geometries())

    except Exception:
        return None


LAND = load_land()

print(
    'Continents:',
    'available (Cartopy)'
    if LAND
    else 'unavailable'
)


def draw_land(ax, project=True):
    if not LAND:
        return

    for geom in LAND:
        parts = geom.geoms if hasattr(geom, 'geoms') else [geom]

        for polygon in parts:
            xs, ys = polygon.exterior.xy

            xs = np.asarray(xs)
            ys = np.asarray(ys)

            if project:
                xs, ys = robinson(xs, ys)

            ax.fill(
                xs, ys,
                facecolor='#fbf8f1',
                edgecolor='#aebbc2',
                linewidth=0.4,
                zorder=0.5
            )


fig = plt.figure(figsize=(20, 12.5), facecolor=BG)

gs = fig.add_gridspec(
    1, 1,
    left=0.035,
    right=0.975,
    top=0.88,
    bottom=0.20
)

ax = fig.add_subplot(gs[0, 0])

ax.set_facecolor(BG)
ax.axis('off')
ax.set_aspect('equal')

latitudes = np.linspace(-90, 90, 200)

xl, yl = robinson(
    np.full_like(latitudes, -180),
    latitudes
)
xr, yr = robinson(
    np.full_like(latitudes, 180),
    latitudes
)

ax.fill(
    np.r_[xl, xr[::-1]],
    np.r_[yl, yr[::-1]],
    color=OCEAN,
    zorder=0
)

ax.plot(
    np.r_[xl, xr[::-1], xl[0]],
    np.r_[yl, yr[::-1], yl[0]],
    color=INK,
    linewidth=0.8,
    zorder=1
)

draw_land(ax, project=True)

for lon in range(-180, 181, 30):
    lat = np.linspace(-90, 90, 100)
    x, y = robinson(np.full_like(lat, lon), lat)

    ax.plot(
        x, y,
        color=GRID,
        linewidth=0.6,
        zorder=1
    )

for lat in range(-60, 91, 30):
    lon = np.linspace(-180, 180, 200)
    x, y = robinson(lon, np.full_like(lon, lat))

    ax.plot(
        x, y,
        color=GRID,
        linewidth=0.6,
        zorder=1
    )

    if lat != 90:
        xx, yy = robinson(-180, lat)

        ax.text(
            xx - 0.03, yy,
            f'{lat}°',
            ha='right',
            va='center',
            fontsize=8,
            color=MUTED
        )

for lon in range(-120, 181, 60):
    xx, yy = robinson(lon, -90)

    ax.text(
        xx, yy - 0.05,
        f'{lon}°',
        ha='center',
        va='top',
        fontsize=8,
        color=MUTED
    )

x, y = robinson(g['lon3'], g['lat3'])

ax.scatter(
    x, y,
    s=marker_size(g['n'], 5.0),
    c=g['n'],
    cmap=CMAP,
    norm=NORM,
    alpha=0.10,
    linewidths=0,
    zorder=3
)

ax.scatter(
    x, y,
    s=marker_size(g['n'], 1.0),
    c=g['n'],
    cmap=CMAP,
    norm=NORM,
    alpha=0.85,
    edgecolors=BG,
    linewidths=0.3,
    zorder=4
)

offsets = {
    'Spain': (-0.60, -0.28),
    'Italy': (0.80, -0.12),
    'Austria': (0.62, 0.58),
    'Netherlands': (0.02, 0.62),
    'France': (-0.55, 0.60),
    'Uruguay': (0.55, -0.15),
    'India': (0.25, -0.40),
    'United States': (0.0, 0.40),
    'Republic of Korea': (-0.25, 0.4),
    'Argentina': (-0.62, -0.35)
}

country_names = {
    'Spain': 'Spain',
    'Italy': 'Italy',
    'Austria': 'Austria',
    'Netherlands': 'Netherlands',
    'France': 'France',
    'Uruguay': 'Uruguay',
    'India': 'India',
    'United States': 'United States',
    'Republic of Korea': 'South Korea',
    'Argentina': 'Argentina'
}

for country, row in countries.head(10).iterrows():
    if country not in offsets:
        continue

    px, py = robinson(row['lon'], row['lat'])
    dx, dy = offsets[country]

    ax.annotate(
        f"{country_names[country]}  {int(row['n']):,}",
        (px, py),
        xytext=(px + dx, py + dy),
        fontsize=9.5,
        color=INK,
        fontweight='bold',
        ha='center',
        va='center',
        zorder=6,
        arrowprops=dict(
            arrowstyle='-',
            color=INK,
            linewidth=0.7,
            shrinkA=2,
            shrinkB=2
        ),
        bbox=dict(
            boxstyle='round,pad=0.25',
            facecolor=BG,
            edgecolor=INK,
            linewidth=0.6
        )
    )

ax.set_xlim(-2.75, 2.75)
ax.set_ylim(-1.45, 1.45)

ZONES = {
    'A': (
        'Iberian Peninsula',
        (-9.6, 4.6),
        (35.8, 44.0)
    ),
    'B': (
        'Barcelona',
        (2.05, 2.25),
        (41.32, 41.48)
    ),
    'C': (
        'Rome and surroundings',
        (12.30, 12.70),
        (41.75, 42.05)
    )
}

for key in ('A', 'B', 'C'):
    name, (lon_min, lon_max), (lat_min, lat_max) = ZONES[key]

    lon_corners = [
        lon_min, lon_max, lon_max, lon_min, lon_min
    ]
    lat_corners = [
        lat_min, lat_min, lat_max, lat_max, lat_min
    ]

    xs, ys = robinson(lon_corners, lat_corners)

    ax.plot(
        xs, ys,
        color=INK,
        linewidth=1.0,
        zorder=5
    )

for key, dx, dy in (
    ('A', -0.16, 0.14),
    ('B', 0.13, -0.17),
    ('C', 0.20, 0.12)
):
    _, (lon_min, lon_max), (lat_min, lat_max) = ZONES[key]

    px, py = robinson(
        (lon_min + lon_max) / 2,
        (lat_min + lat_max) / 2
    )

    ax.text(
        px + dx, py + dy,
        key,
        fontsize=11,
        fontweight='bold',
        color=BG,
        ha='center',
        va='center',
        zorder=7,
        bbox=dict(
            boxstyle='circle,pad=0.25',
            facecolor=INK,
            edgecolor='none'
        )
    )

fig.text(
    0.035, 0.165,
    'Highlighted areas',
    fontsize=11,
    fontweight='bold',
    color=INK
)

for i, key in enumerate(('A', 'B', 'C')):
    name, lon_limits, lat_limits = ZONES[key]

    subset = g[
        g['lon3'].between(*lon_limits) &
        g['lat3'].between(*lat_limits)
    ]

    total_sites = int(subset['n'].sum())
    unique_coordinates = len(subset)

    y = 0.125 - i * 0.04

    fig.text(
        0.035, y,
        key,
        fontsize=10,
        fontweight='bold',
        color=BG,
        ha='center',
        va='center',
        bbox=dict(
            boxstyle='circle,pad=0.25',
            facecolor=INK,
            edgecolor='none'
        )
    )

    fig.text(
        0.052, y,
        f'{name}: {total_sites:,} breeding sites, '
        f'{unique_coordinates:,} unique coordinates',
        fontsize=9,
        color=INK,
        va='center'
    )

fig.text(
    0.035, 0.945,
    'Breeding Sites',
    fontsize=30,
    fontweight='bold',
    color=INK,
)

cax = fig.add_axes([0.745, 0.915, 0.23, 0.012])

sm = plt.cm.ScalarMappable(
    norm=NORM,
    cmap=CMAP
)

colorbar = fig.colorbar(
    sm,
    cax=cax,
    orientation='horizontal'
)

colorbar.set_ticks([
    1, 5, 20, 50, 100, int(g['n'].max())
])

colorbar.ax.tick_params(
    labelsize=8.5,
    colors=MUTED,
    length=2
)

colorbar.outline.set_edgecolor(INK)
colorbar.outline.set_linewidth(0.6)

fig.text(
    0.745, 0.945,
    'Breeding sites per coordinate',
    fontsize=9.5,
    color=INK
)

plt.savefig(
    'world_map_breeding_sites.png',
    dpi=200,
    facecolor=BG,
    bbox_inches='tight'
)

plt.show()
