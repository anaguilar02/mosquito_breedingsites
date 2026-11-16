
import argparse

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize, PowerNorm
from matplotlib.widgets import Button

CSV = 'breeding_sites.csv'


def to_bool(s):
    if s.dtype == bool:
        return s
    return s.astype(str).str.strip().str.lower().isin(
        ['true', '1', '1.0', 'yes']
    )


def load_data(path):
    raw = pd.read_csv(path)

    raw['latitude'] = pd.to_numeric(
        raw['location.point.latitude'], errors='coerce'
    )
    raw['longitude'] = pd.to_numeric(
        raw['location.point.longitude'], errors='coerce'
    )

    df1 = raw.dropna(subset=['latitude', 'longitude']).copy()
    df1['lat3'] = df1['latitude'].round(3)
    df1['lon3'] = df1['longitude'].round(3)

    g1 = (
        df1.groupby(['lat3', 'lon3'])
           .size()
           .reset_index(name='n')
           .sort_values('n')
           .reset_index(drop=True)
    )
    countries1 = (
        df1.groupby('location.country.name_en')
           .agg(n=('lat3', 'size'),
                lat=('lat3', 'median'),
                lon=('lon3', 'median'))
           .sort_values('n', ascending=False)
    )
    print(f'[Paises]  Records: {len(df1):,} | Unique coordinates: {len(g1):,}')

    df2 = raw.dropna(
        subset=['latitude', 'longitude', 'has_water', 'has_larvae']
    ).copy()
    df2['has_water'] = to_bool(df2['has_water'])
    df2['has_larvae'] = to_bool(df2['has_larvae'])
    df2['lat3'] = df2['latitude'].round(3)
    df2['lon3'] = df2['longitude'].round(3)

    g2 = (
        df2.groupby(['lat3', 'lon3'])
           .agg(n=('has_larvae', 'size'),
                n_larvae=('has_larvae', 'sum'),
                n_water=('has_water', 'sum'))
           .reset_index()
    )
    g2['pct_larvae'] = 100 * g2['n_larvae'] / g2['n']
    g2 = g2.sort_values('n').reset_index(drop=True)

    countries2 = (
        df2.groupby('location.country.name_en')
           .agg(n=('lat3', 'size'),
                n_larvae=('has_larvae', 'sum'),
                lat=('lat3', 'median'),
                lon=('lon3', 'median'))
           .sort_values('n', ascending=False)
    )
    countries2['pct_larvae'] = 100 * countries2['n_larvae'] / countries2['n']
    print(f'[Agua]    Records: {len(df2):,} | Unique coordinates: {len(g2):,}')
    print(f"          With stagnant water: {int(df2['has_water'].sum()):,} | "
          f"With larvae: {int(df2['has_larvae'].sum()):,}")

    return dict(df1=df1, g1=g1, countries1=countries1,
                df2=df2, g2=g2, countries2=countries2)


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

plt.rcParams['font.family'] = 'DejaVu Sans'

OFFSETS = {
    'Spain': (-0.60, -0.28),
    'Italy': (0.80, -0.12),
    'Austria': (0.62, 0.58),
    'Netherlands': (0.02, 0.62),
    'France': (-0.55, 0.60),
    'Uruguay': (0.55, -0.15),
    'India': (0.25, -0.40),
    'United States': (0.0, 0.40),
    'Republic of Korea': (-0.25, 0.4),
    'Argentina': (-0.62, -0.35),
    'Libya': (0.25, -0.62),
}
DEFAULT_OFFSET = (0.0, 0.45)
COUNTRY_NAMES = {'Republic of Korea': 'South Korea'}

ZONES = {
    'A': ('Iberian Peninsula', (-9.6, 4.6), (35.8, 44.0)),
    'B': ('Barcelona', (2.05, 2.25), (41.32, 41.48)),
    'C': ('Rome and surroundings', (12.30, 12.70), (41.75, 42.05)),
}
LETTER_OFFSETS = {'A': (-0.16, 0.14), 'B': (0.13, -0.17), 'C': (0.20, 0.12)}


def marker_size(n, k=1.0):
    return k * (6 + 16 * np.sqrt(n))


def load_land():
    try:
        import cartopy.io.shapereader as shpreader

        path = shpreader.natural_earth(
            resolution='50m', category='physical', name='land'
        )
        return list(shpreader.Reader(path).geometries())
    except Exception:
        return None


def _flat(items):
    out = []
    for it in items:
        if isinstance(it, (list, tuple)):
            out.extend(it)
        else:
            out.append(it)
    return out


class Viewer:
    TITLES = {
        'countries': 'Breeding Sites',
        'water': 'Stagnant Water and Larvae',
    }
    BUTTON_TEXT = {
        'countries': 'View water and larvae',
        'water': 'View breeding sites',
    }
    FILES = {
        'countries': 'world_map_breeding_sites.png',
        'water': 'world_map_stagnant_water_larvae.png',
    }

    def __init__(self, data):
        self.d = data
        self.land = load_land()
        print('Continents:',
              'available (Cartopy)' if self.land else 'unavailable')

        self.norm_countries = PowerNorm(
            gamma=0.5, vmin=1, vmax=self.d['g1']['n'].max()
        )
        self.norm_water = Normalize(vmin=0, vmax=100)

        self.fig = plt.figure(figsize=(20, 12.5), facecolor=BG)
        try:
            self.fig.canvas.manager.set_window_title('Breeding sites map')
        except Exception:
            pass

        gs = self.fig.add_gridspec(
            1, 1, left=0.035, right=0.975, top=0.88, bottom=0.20
        )
        self.ax = self.fig.add_subplot(gs[0, 0])
        self.ax.set_facecolor(BG)
        self.ax.axis('off')
        self.ax.set_aspect('equal')
        self.ax.set_xlim(-2.75, 2.75)
        self.ax.set_ylim(-1.45, 1.45)

        self.cax = self.fig.add_axes([0.745, 0.915, 0.23, 0.012])
        self.artists = []
        self.draw_base()

        self.btn_ax = self.fig.add_axes([0.775, 0.045, 0.20, 0.06])
        self.btn = Button(self.btn_ax, '', color=INK, hovercolor='#34445a')
        self.btn.label.set_color(BG)
        self.btn.label.set_fontsize(12)
        self.btn.label.set_fontweight('bold')
        self.btn.on_clicked(self.toggle)

        self.view = None
        self.show('countries')

    def draw_base(self):
        ax = self.ax

        latitudes = np.linspace(-90, 90, 200)
        xl, yl = robinson(np.full_like(latitudes, -180), latitudes)
        xr, yr = robinson(np.full_like(latitudes, 180), latitudes)

        ax.fill(np.r_[xl, xr[::-1]], np.r_[yl, yr[::-1]],
                color=OCEAN, zorder=0)
        ax.plot(np.r_[xl, xr[::-1], xl[0]], np.r_[yl, yr[::-1], yl[0]],
                color=INK, linewidth=0.8, zorder=1)

        if self.land:
            for geom in self.land:
                parts = geom.geoms if hasattr(geom, 'geoms') else [geom]
                for polygon in parts:
                    xs, ys = polygon.exterior.xy
                    xs, ys = robinson(np.asarray(xs), np.asarray(ys))
                    ax.fill(xs, ys, facecolor='#fbf8f1',
                            edgecolor='#aebbc2', linewidth=0.4, zorder=0.5)

        for lon in range(-180, 181, 30):
            lat = np.linspace(-90, 90, 100)
            x, y = robinson(np.full_like(lat, lon), lat)
            ax.plot(x, y, color=GRID, linewidth=0.6, zorder=1)

        for lat in range(-60, 91, 30):
            lon = np.linspace(-180, 180, 200)
            x, y = robinson(lon, np.full_like(lon, lat))
            ax.plot(x, y, color=GRID, linewidth=0.6, zorder=1)

            if lat != 90:
                xx, yy = robinson(-180, lat)
                ax.text(xx - 0.03, yy, f'{lat}°', ha='right', va='center',
                        fontsize=8, color=MUTED)

        for lon in range(-120, 181, 60):
            xx, yy = robinson(lon, -90)
            ax.text(xx, yy - 0.05, f'{lon}°', ha='center', va='top',
                    fontsize=8, color=MUTED)

    def points(self, g, values, norm):
        x, y = robinson(g['lon3'], g['lat3'])
        halo = self.ax.scatter(
            x, y, s=marker_size(g['n'], 5.0), c=values, cmap=CMAP,
            norm=norm, alpha=0.10, linewidths=0, zorder=3)
        dots = self.ax.scatter(
            x, y, s=marker_size(g['n'], 1.0), c=values, cmap=CMAP,
            norm=norm, alpha=0.85, edgecolors=BG, linewidths=0.3, zorder=4)
        return [halo, dots]

    def country_labels(self, countries, text_fn, skip_unknown):
        out = []
        for country, row in countries.head(10).iterrows():
            if skip_unknown and country not in OFFSETS:
                continue
            px, py = robinson(row['lon'], row['lat'])
            dx, dy = OFFSETS.get(country, DEFAULT_OFFSET)
            label = COUNTRY_NAMES.get(country, country)

            out.append(self.ax.annotate(
                text_fn(label, row), (px, py), xytext=(px + dx, py + dy),
                fontsize=9.5, color=INK, fontweight='bold',
                ha='center', va='center', zorder=6,
                arrowprops=dict(arrowstyle='-', color=INK, linewidth=0.7,
                                shrinkA=2, shrinkB=2),
                bbox=dict(boxstyle='round,pad=0.25', facecolor=BG,
                          edgecolor=INK, linewidth=0.6)))
        return out

    def zone_boxes(self):
        out = []
        for key in ('A', 'B', 'C'):
            _, (lon_min, lon_max), (lat_min, lat_max) = ZONES[key]
            xs, ys = robinson(
                [lon_min, lon_max, lon_max, lon_min, lon_min],
                [lat_min, lat_min, lat_max, lat_max, lat_min])
            out += self.ax.plot(xs, ys, color=INK, linewidth=1.0, zorder=5)

            dx, dy = LETTER_OFFSETS[key]
            px, py = robinson((lon_min + lon_max) / 2,
                              (lat_min + lat_max) / 2)
            out.append(self.ax.text(
                px + dx, py + dy, key, fontsize=11, fontweight='bold',
                color=BG, ha='center', va='center', zorder=7,
                bbox=dict(boxstyle='circle,pad=0.25', facecolor=INK,
                          edgecolor='none')))
        return out

    def zone_summary(self, lines):
        out = [self.fig.text(0.035, 0.165, 'Highlighted areas',
                             fontsize=11, fontweight='bold', color=INK)]
        for i, (key, text) in enumerate(zip(('A', 'B', 'C'), lines)):
            y = 0.125 - i * 0.04
            out.append(self.fig.text(
                0.035, y, key, fontsize=10, fontweight='bold', color=BG,
                ha='center', va='center',
                bbox=dict(boxstyle='circle,pad=0.25', facecolor=INK,
                          edgecolor='none')))
            out.append(self.fig.text(0.052, y, text, fontsize=9,
                                     color=INK, va='center'))
        return out

    def colorbar(self, norm, ticks, ticklabels, caption):
        self.cax.clear()
        sm = plt.cm.ScalarMappable(norm=norm, cmap=CMAP)
        cb = self.fig.colorbar(sm, cax=self.cax, orientation='horizontal')
        cb.set_ticks(ticks)
        if ticklabels:
            cb.set_ticklabels(ticklabels)
        cb.ax.tick_params(labelsize=8.5, colors=MUTED, length=2)
        cb.outline.set_edgecolor(INK)
        cb.outline.set_linewidth(0.6)
        return [self.fig.text(0.745, 0.945, caption, fontsize=9.5,
                              color=INK)]

    def build_countries(self):
        g, countries, df = self.d['g1'], self.d['countries1'], self.d['df1']
        out = self.points(g, g['n'], self.norm_countries)
        out += self.country_labels(
            countries,
            lambda name, r: f"{name}  {int(r['n']):,}",
            skip_unknown=True)
        out += self.zone_boxes()

        lines = []
        for key in ('A', 'B', 'C'):
            name, lon_lim, lat_lim = ZONES[key]
            sub = g[g['lon3'].between(*lon_lim) & g['lat3'].between(*lat_lim)]
            lines.append(f'{name}: {int(sub["n"].sum()):,} breeding sites, '
                         f'{len(sub):,} unique coordinates')
        out += self.zone_summary(lines)

        out += self.colorbar(
            self.norm_countries,
            [1, 5, 20, 50, 100, int(g['n'].max())], None,
            'Breeding sites per coordinate')
        return out

    def build_water(self):
        g, countries, df = self.d['g2'], self.d['countries2'], self.d['df2']
        out = self.points(g, g['pct_larvae'], self.norm_water)
        out += self.country_labels(
            countries,
            lambda name, r: (f"{name}  {int(r['n']):,}  "
                             f"({r['pct_larvae']:.0f}% larvae)"),
            skip_unknown=False)
        out += self.zone_boxes()

        lines = []
        for key in ('A', 'B', 'C'):
            name, lon_lim, lat_lim = ZONES[key]
            sub = df[df['lon3'].between(*lon_lim) & df['lat3'].between(*lat_lim)]
            if len(sub) == 0:
                lines.append(f'{name}: no records')
            else:
                lines.append(
                    f'{name}: {len(sub):,} breeding sites, '
                    f'{100 * sub["has_water"].mean():.0f}% with stagnant '
                    f'water, {100 * sub["has_larvae"].mean():.0f}% with larvae')
        out += self.zone_summary(lines)

        out += self.colorbar(
            self.norm_water, [0, 20, 40, 60, 80, 100],
            ['0%', '20%', '40%', '60%', '80%', '100%'],
            'Share of breeding sites with larvae')
        return out

    def show(self, view):
        for a in self.artists:
            try:
                a.remove()
            except Exception:
                pass

        build = self.build_countries if view == 'countries' else self.build_water
        self.artists = _flat(build())
        self.artists.append(self.fig.text(
            0.035, 0.945, self.TITLES[view], fontsize=30,
            fontweight='bold', color=INK))

        self.view = view
        self.btn.label.set_text(self.BUTTON_TEXT[view])
        self.fig.canvas.draw_idle()

    def toggle(self, _event=None):
        self.show('water' if self.view == 'countries' else 'countries')

    def save_all(self):
        original = self.view
        self.btn_ax.set_visible(False)
        for view, filename in self.FILES.items():
            self.show(view)
            self.fig.savefig(filename, dpi=200, facecolor=BG,
                             bbox_inches='tight')
            print('Saved', filename)
        self.btn_ax.set_visible(True)
        self.show(original)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', default=CSV)
    parser.add_argument('--save', action='store_true',
                        help='guarda los dos PNG y termina')
    args = parser.parse_args()

    viewer = Viewer(load_data(args.csv))
    if args.save:
        viewer.save_all()
    else:
        plt.show()
