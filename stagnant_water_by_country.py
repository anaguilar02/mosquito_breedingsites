import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('breeding_sites.csv')
water_df = df[df['has_water'] == True].copy()
country_counts = water_df['location.country.name_en'].value_counts()

print(f"Total records: {len(df)}")
print(f"Records with stagnant water: {len(water_df)}")
print(f"Total countries with stagnant water: {len(country_counts)}")

print("\nCountries with the most breeding sites with stagnant water:")
print(country_counts.head(20))

top20 = country_counts.head(20)

top20 = top20.sort_values(ascending=True)

fig, ax = plt.subplots(figsize=(14, 10))

bars = ax.barh(
    top20.index,
    top20.values,
    color='#4C78A8',
    height=0.7
)

for bar in bars:

    value = int(bar.get_width())

    ax.text(
        bar.get_width() + top20.max() * 0.015,
        bar.get_y() + bar.get_height() / 2,
        f'{value}',
        ha='left',
        va='center',
        fontsize=9
    )

ax.set_title(
    'Breeding Sites with Stagnant Water by Country',
    fontsize=18,
    fontweight='bold',
    loc='left',
    pad=20
)

ax.set_xlabel(
    'Number of Breeding Sites with Stagnant Water',
    fontsize=11
)

ax.set_ylabel(
    'Country',
    fontsize=11
)

ax.tick_params(
    axis='y',
    labelsize=10
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
    top20.max() * 1.12
)

plt.tight_layout()

plt.savefig(
    'breeding_sites_with_stagnant_water_by_country.png',
    dpi=200,
    bbox_inches='tight'
)
plt.show()
