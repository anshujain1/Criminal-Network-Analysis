"""
Builds an interactive map showing:
  - All cell towers as markers
  - A specific person's movement trail: which towers they pinged, in
    chronological order, connected by lines (their approximate movement
    path over the simulation period)
This directly implements the "trace where this person passed by" feature.
Run standalone: python scripts/geospatial_map.py P001
  -> writes screenshots/movement_P001.html (open in any browser)
Or import build_person_map() / build_overview_map() from the Streamlit app.
"""
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


def build_person_map(person_id, towers, pings):
    person_pings = sorted(
        [p for p in pings if p["person_id"] == person_id],
        key=lambda p: p["timestamp"]
    )
    if not person_pings:
        raise ValueError(f"No tower pings found for {person_id}")

    m = build_overview_map(towers)

    path_coords = []
    for i, ping in enumerate(person_pings):
        tower_id = ping["tower_id"]
        if tower_id not in towers:
            continue
        lat, lon = towers[tower_id]
        path_coords.append((lat, lon))
        folium.CircleMarker(
            [lat, lon],
            radius=5,
            color="crimson",
            fill=True,
            fill_opacity=0.7,
            tooltip=f"{person_id} @ {tower_id} — {ping['timestamp']}",
        ).add_to(m)

    folium.PolyLine(path_coords, color="crimson", weight=2, opacity=0.5,
                     tooltip=f"{person_id} movement path").add_to(m)

    return m


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/geospatial_map.py <person_id>")
        print("Example: python scripts/geospatial_map.py P001")
        sys.exit(1)

    person_id = sys.argv[1]
    towers = load_towers()
    pings = load_pings()

    m = build_person_map(person_id, towers, pings)
    out_path = f"screenshots/movement_{person_id}.html"
    m.save(out_path)
    print(f"Saved map to {out_path} -- open it in a browser to view.")
