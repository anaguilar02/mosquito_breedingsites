
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('breeding_sites.csv')

df_relation = df.dropna(
    subset=['has_water', 'has_larvae']
).copy()

print(f"Total records: {len(df)}")
print(f"Records with water and larvae information: {len(df_relation)}")

print("\nRelationship between stagnant water and larvae:")
print(
    pd.crosstab(
        df_relation['has_water'],
        df_relation['has_larvae']
    )
)

conteo = pd.crosstab(
    df_relation['has_water'],
    df_relation['has_larvae']
)

conteo.index = [
    'No stagnant water',
    'Stagnant water'
]

conteo.columns = [
    'No larvae',
    'Larvae present'
]

fig, ax = plt.subplots(figsize=(12, 8))

bars = conteo.plot(
    kind='bar',
    ax=ax,
    color=['#4C78A8', '#F58518'],
    width=0.7
)

for container in ax.containers:
    ax.bar_label(
        container,
        fmt='%d',
        padding=3,
        fontsize=10
    )

ax.set_title(
    'Relationship Between Stagnant Water and Larvae',
    fontsize=18,
    fontweight='bold',
    loc='left',
    pad=20
)

ax.set_xlabel(
    'Stagnant Water',
    fontsize=11
)

ax.set_ylabel(
    'Number of Breeding Sites',
    fontsize=11
)

ax.tick_params(
    axis='x',
    rotation=0
)

ax.grid(
    axis='y',
    linestyle='-',
    alpha=0.25
)

ax.set_axisbelow(True)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)

ax.legend(
    title='Larvae',
    frameon=False
)

plt.tight_layout()

plt.savefig(
    'stagnant_water_vs_larvae.png',
    dpi=200,
    bbox_inches='tight'
)

plt.show()
