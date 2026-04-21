import csv
import streamlit as st
import networkx as nx
import pandas as pd

from scripts.geospatial_map import load_towers, load_pings

st.set_page_config(
    page_title="Network Link Analysis",
    layout="wide"
)

st.title("Criminal Network Link Analysis")

DATA_DISCLAIMER = (
    "All data shown is synthetically generated for demonstration purposes only. "
    "No real personal, telecom, or location data is used anywhere in this project."
)

st.caption(DATA_DISCLAIMER)


@st.cache_data
def load_data():
    with open("data/calls.csv", newline="") as f:
        calls = list(csv.DictReader(f))

    with open("data/people.csv", newline="") as f:
        people = {row["person_id"]: row for row in csv.DictReader(f)}

    towers = load_towers()
    pings = load_pings()

    return calls, people, towers, pings


calls, people, towers, pings = load_data()

st.write(f"Loaded {len(people)} people and {len(calls)} calls.")

@st.cache_data
def build_call_graph(calls):
    G = nx.Graph()

    for c in calls:
        G.add_edge(
            c["caller_id"],
            c["callee_id"]
        )

    return G

G = build_call_graph(calls)

st.write(
    f"Network contains {G.number_of_nodes()} people "
    f"and {G.number_of_edges()} connections."
)

G = build_call_graph(calls)

st.write(
    f"Network contains {G.number_of_nodes()} people "
    f"and {G.number_of_edges()} connections."
)