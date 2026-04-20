import csv
import sys
import folium


def load_towers(path="data/cell_towers.csv"):
    with open(path, newline="") as f:
        return {row["tower_id"]: (float(row["lat"]), float(row["lon"])) for row in csv.DictReader(f)}


def load_pings(path="data/tower_pings.csv"):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))
import csv
import sys
import folium


def load_towers(path="data/cell_towers.csv"):
    with open(path, newline="") as f:
        return {row["tower_id"]: (float(row["lat"]), float(row["lon"])) for row in csv.DictReader(f)}


def load_pings(path="data/tower_pings.csv"):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))

def build_overview_map(towers):
    lats = [lat for lat, lon in towers.values()]
    lons = [lon for lat, lon in towers.values()]
    center = [sum(lats) / len(lats), sum(lons) / len(lons)]

    m = folium.Map(location=center, zoom_start=12, tiles="OpenStreetMap")
    for tower_id, (lat, lon) in towers.items():
        folium.Marker(
            [lat, lon],
            tooltip=tower_id,
            icon=folium.Icon(color="gray", icon="signal", prefix="fa"),
        ).add_to(m)
    return m
