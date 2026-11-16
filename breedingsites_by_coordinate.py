
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('breeding_sites.csv')

df['latitude'] = pd.to_numeric(
    df['location.point.latitude'],
    errors='coerce'
)

df['longitude'] = pd.to_numeric(
    df['location.point.longitude'],
    errors='coerce'
)

df_coords = df.dropna(
    subset=['latitude', 'longitude']
).copy()

print(f'Total de registros: {len(df)}')
print(f'Registros con coordenadas: {len(df_coords)}')
print(f'Registros sin coordenadas: {len(df) - len(df_coords)}')

df_coords['latitude_3'] = df_coords['latitude'].round(3)
df_coords['longitude_3'] = df_coords['longitude'].round(3)

conteo_coordenadas = (
    df_coords
    .groupby(['latitude_3', 'longitude_3'])
    .size()
    .reset_index(name='breeding_sites')
)

conteo_coordenadas = conteo_coordenadas.sort_values(
    'breeding_sites',
    ascending=False
)

print("\nCoordenadas con más breeding sites:")
print(conteo_coordenadas.head(30))

print(
    f"\nTotal de coordenadas únicas "
    f"(precisión 3 decimales): {len(conteo_coordenadas)}"
)

top20 = conteo_coordenadas.head(30).copy()

top20['coordenada'] = (
    top20['latitude_3'].map(lambda x: f'{x:.3f}')
    + ', '
    + top20['longitude_3'].map(lambda x: f'{x:.3f}')
)

top20 = top20.sort_values(
    'breeding_sites',
    ascending=True
)

fig, ax = plt.subplots(figsize=(14, 10))

bars = ax.barh(
    top20['coordenada'],
    top20['breeding_sites'],
    color='#4C78A8',
    height=0.7
)

for bar in bars:
    valor = int(bar.get_width())

    ax.text(
        bar.get_width() + top20['breeding_sites'].max() * 0.015,
        bar.get_y() + bar.get_height() / 2,
        f'{valor}',
        ha='left',
        va='center',
        fontsize=9
    )

ax.set_title(
    'Breeding Sites by Coordinate',
    fontsize=18,
    fontweight='bold',
    loc='left',
    pad=20
)

ax.set_xlabel(
    'Number of Breeding Sites',
    fontsize=11
)

ax.set_ylabel(
    'Coordinate (Latitude, Longitude)',
    fontsize=11
)

ax.grid(
    axis='x',
    linestyle='-',
    alpha=0.25
)

ax.set_axisbelow(True)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)

ax.set_xlim(
    0,
    top20['breeding_sites'].max() * 1.12
)

plt.tight_layout()

plt.savefig(
    'breeding_sites_coordinates.png',
    dpi=200,
    bbox_inches='tight'
)

plt.show()
