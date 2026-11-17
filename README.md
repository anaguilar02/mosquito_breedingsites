# mosquito_breedingsites

Data and code for the preprint

> Aguilar-Pineda A, Jiménez-Jiménez I, Sánchez F. *Interpreting citizen science data for larval surveillance: lessons from storm drain reports in Mosquito Alert.* 2026.

The preprint link and DOI will be added here once it is posted.

## Abstract

Mosquito-borne diseases are an increasing public health concern, and urban drainage infrastructure such as storm drains and catch basins can provide breeding habitat for *Aedes* vectors, including *Aedes albopictus*. Detecting these sites over large areas is costly with traditional surveillance alone, and citizen science offers a complementary, lower-cost source of geolocated observations. Mosquito Alert is a citizen science platform, active since 2014, through which participants report adult mosquitoes, bites, and potential breeding sites. In this work, we present a descriptive analysis of the 17,880 storm drain breeding sites reported through the platform from June 2014 to August 2026, obtained from the project's public map. We counted the reported sites by country and geographic coordinate, examined when reports are submitted and which fields are recorded, estimated how often water and larvae are reported, and mapped the records globally. We also developed an interactive map to help inspect regions where many records overlap. Spain accounts for 90% of the records, 82% of all reports were submitted between April and June, and half of them fall on only 50 days. Group events, defined as five or more users reporting in the same municipality on the same day, account for 63% of the records. Water was reported in 43% of the storm drains: 33% in group events and 61% in the remaining reports. Larvae information exists for only 1,739 records; almost all are drains with water, and 28.5% of those had larvae, with higher shares in the warmer months and where participants noticed adult mosquitoes nearby. Our aim is not to model mosquito populations but to describe the structure of the data and highlight patterns worth further investigation. Because citizen science reporting effort varies across space, time, and socioeconomic groups, we discuss how sampling bias and other limitations of volunteer-based data affect the interpretation of these patterns and what they imply for the use of such data in larval surveillance.

## Data

`breeding_sites.csv` contains the 17,880 storm drain reports (storm drains with water and dry storm drains) downloaded from the Mosquito Alert public map (https://map.mosquitoalert.com) on September 12, 2026. The map is updated continuously, so this file is the exact snapshot used in the paper. Do not open and re-save it in a spreadsheet program: depending on the regional settings, this can corrupt the decimal coordinates.

The data are provided by the Mosquito Alert project and remain under its terms of use; they are not covered by the licences of this repository.

The folder `basemap/` contains the boundaries used by `spain_barcelona_map.py`: Spanish provinces and neighbouring countries from Natural Earth (1:10m, public domain), and the districts of Barcelona from the open data portal of the Ajuntament de Barcelona.

## Scripts and figures

Run every script from the top folder of the repository. The scripts read `breeding_sites.csv` from that folder. `additional_analysis.py`, `group_events_analysis.py`, and `spain_barcelona_map.py` write their figures to `figures/`; the other scripts write to the top folder. Most scripts also print the numbers quoted in the paper.

| Paper | Output | Script |
|---|---|---|
| Figure 1a | `breeding_sites_by_country.png` | `breedingsites_by_country.py` |
| Figure 1b | `breeding_sites_coordinates.png` | `breedingsites_by_coordinate.py` |
| Figure 1c | `stagnant_water_vs_larvae.png` | `breedingsites_water_and_larvae.py` |
| Figure 2 | `world_map_breeding_sites.png` | `worldmap_not_interactive.py` |
| Figure 3 | `spain_barcelona_map.png` | `spain_barcelona_map.py` |
| Figure 4 | `temporal_patterns.png` | `additional_analysis.py` |
| Figure 5 | `shares_with_ci.png` | `additional_analysis.py` |
| Figure 6 | `group_events_and_larvae.png` | `group_events_analysis.py` |
| Figure 7 | `world_map_stagnant_water_larvae.png` | `worldmap_stagnant_and_larvae.py` |
| Table 1 and other figures in the text | printed output | `additional_analysis.py`, `group_events_analysis.py` |
| Interactive map | `breedingsites_map.html` | `breedingsites_map_html.py` |

Other files:

- `breedingsites_map.py` opens the two world maps in a desktop window with a button to switch between them; `python breedingsites_map.py --save` saves them as PNG files instead.
- `stagnant_water_by_country.py` produces `breeding_sites_with_stagnant_water_by_country.png`, which was used in an earlier version of the paper and is not part of the current one.

## Interactive map

Open `breedingsites_map.html` in any web browser; it needs no internet connection. Hover over a point to see its country, coordinates, and number of breeding sites, zoom and pan to inspect areas where many records overlap, and use the button at the bottom right to switch between the map of breeding sites and the map of stagnant water and larvae.

## Requirements

Python 3 with the packages in `requirements.txt`:

```
pip install -r requirements.txt
```

Cartopy is optional. Without it, the scripts still run but the world maps are drawn without continent outlines.

## Licence

- Code: MIT licence (see `LICENSE`).
- Figures in `figures/` and the interactive map: CC BY 4.0 (see `figures/LICENSE.md`).
- Data: Mosquito Alert's terms of use; boundaries: Natural Earth (public domain) and the Ajuntament de Barcelona's open data terms.
