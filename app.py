import csv
import streamlit as st
import networkx as nx
import pandas as pd

from scripts.link_prediction import predict_links
from scripts.geospatial_map import load_towers, load_pings
from streamlit_folium import st_folium

from scripts.geospatial_map import (
    load_towers,
    load_pings,
    build_person_map
)
from scripts.geospatial_map import (
    load_towers,
    load_pings,
    build_person_map,
    build_overview_map
)
st.set_page_config(
    page_title="Network Link Analysis",
    layout="wide"
)

st.title("Criminal Network Link Analysis")

CUSTOM_CSS = """
<style>

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

div[data-testid="stMetric"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 1rem 1.2rem;
}

button[data-baseweb="tab"] {
    font-size: 14px;
    font-weight: 500;
}

</style>
"""

st.markdown(
    CUSTOM_CSS,
    unsafe_allow_html=True
)
DATA_DISCLAIMER = (
    "All data shown is synthetically generated for demonstration purposes only. "
    "No real personal, telecom, or location data is used anywhere in this project."
)

st.caption(DATA_DISCLAIMER)
tab1, tab2, tab3 = st.tabs(
    [
        "Person Lookup",
        "Risk Flags",
        "Predicted Links"
    ]
)

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Person Lookup",
        "Risk Flags",
        "Predicted Links",
        "Network Overview"
    ]
)

with tab4:
    st.subheader("Full network overview")

    degree = sorted(
        G.degree,
        key=lambda x: -x[1]
    )[:10]

    st.markdown(
        "**Top 10 by degree centrality:**"
    )

    st.dataframe(
        pd.DataFrame(
            degree,
            columns=["Person ID", "Connections"]
        ),
        use_container_width=True
    )

    communities = nx.community.louvain_communities(
        G,
        seed=42
    )

    st.markdown(
        f"**Detected {len(communities)} communities:**"
    )

    for i, community in enumerate(communities):
        st.write(
            f"Community {i} "
            f"({len(community)} members): "
            f"{', '.join(sorted(community))}"
        )

    st.markdown("**Cell tower coverage:**")

    st_folium(
        build_overview_map(towers),
        width=1100,
        height=420
    )
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

@st.cache_data
def compute_burner_candidates(
    calls,
    window_days=5,
    max_calls=15
):
    from datetime import datetime

    by_person = {}

    for c in calls:
        for role in ("caller_id", "callee_id"):
            pid = c[role]

            by_person.setdefault(pid, []).append(
                datetime.fromisoformat(c["timestamp"])
            )

    flagged = []

    for pid, times in by_person.items():
        times.sort()

        span = (times[-1] - times[0]).days

        if span <= window_days and len(times) <= max_calls:
            flagged.append({
                "person_id": pid,
                "total_calls": len(times),
                "active_window_days": span
            })

    return pd.DataFrame(flagged).sort_values("total_calls") 

burner_df = compute_burner_candidates(calls)

tab1, tab2 = st.tabs(
    ["Risk Flags", "Network"]
)

with tab1:
    st.subheader("Burner-phone heuristic")
    st.dataframe(
        burner_df,
        use_container_width=True
    )

tab1, tab2 = st.tabs(
    ["Person Lookup", "Risk Flags"]
)

with tab1:
    st.subheader("Look up a person")

    all_ids = sorted(
        set(
            list(people.keys())
            + [c["caller_id"] for c in calls]
            + [c["callee_id"] for c in calls]
        )
    )

    selected = st.selectbox(
        "Select a person ID",
        all_ids
    )

    if selected in G:
        neighbors = list(G.neighbors(selected))

        st.write(
            f"{len(neighbors)} direct contact(s)"
        )

        if neighbors:
            st.write(", ".join(neighbors))
    else:
        st.write("No call records for this person.")
col1, col2 = st.columns([1, 1.2])

with col1:
    st.markdown("#### Direct contacts")

    if selected in G:
        neighbors = list(G.neighbors(selected))
        st.write(f"{len(neighbors)} direct contact(s)")

        if neighbors:
            st.code(
                ", ".join(neighbors),
                language=None
            )
    else:
        st.write("No call records for this person.")

with col2:
    st.markdown("#### Movement path")

    person_has_pings = any(
        p["person_id"] == selected
        for p in pings
    )

    if person_has_pings:
        m = build_person_map(
            selected,
            towers,
            pings
        )

        st_folium(
            m,
            width=550,
            height=420
        )
    else:
        st.write(
            "No tower ping data for this person."
        )
    with tab3:
        st.subheader("Predicted (unrecorded) links")

        st.caption(
        "Pairs who share several common contacts but have "
        "never called each other directly."
    )

    jaccard_ranked, aa_ranked = predict_links(
        G,
        top_n=15
    )

    pred_df = pd.DataFrame(
        [
            {
                "Person 1": u,
                "Person 2": v,
                "Jaccard Score": round(s, 3)
            }
            for u, v, s in jaccard_ranked
            if s > 0
        ]
    )

    st.dataframe(
        pred_df,
        use_container_width=True
    )