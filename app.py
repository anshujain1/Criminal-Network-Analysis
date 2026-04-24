"""
The demo/presentation layer. All the real analysis logic lives in
scripts/*.py -- this file just wires it together into something
you can click through in an interview or a viva.

To Run: streamlit run app.py

NOTE: This dashboard runs entirely on the local CSV files using NetworkX,
so it works WITHOUT a Neo4j connection -- useful for demos and for anyone
cloning the repo without wanting to set up Aura first. The Neo4j + Cypher
pipeline (scripts/load_to_neo4j.py, scripts/analyze_network.py) is the
"production" analysis path and is what the README documents as the core
technical work.
"""
import csv
import streamlit as st
import networkx as nx
import pandas as pd
from streamlit_folium import st_folium

from scripts.geospatial_map import load_towers, load_pings, build_person_map, build_overview_map
from scripts.link_prediction import predict_links

st.set_page_config(page_title="Network Link Analysis", layout="wide", page_icon="🕸️")

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* metric cards */
div[data-testid="stMetric"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 1rem 1.2rem;
}
div[data-testid="stMetricLabel"] {
    font-size: 13px;
    opacity: 0.7;
}
div[data-testid="stMetricValue"] {
    font-size: 26px;
    font-weight: 600;
}

/* tabs */
button[data-baseweb="tab"] {
    font-size: 14px;
    font-weight: 500;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #e63946 !important;
}
div[data-baseweb="tab-highlight"] {
    background-color: #e63946 !important;
}

/* hero */
.hero-eyebrow {
    font-size: 13px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    opacity: 0.6;
    margin-bottom: 4px;
}
.hero-title {
    font-size: 34px;
    font-weight: 600;
    margin: 0 0 8px 0;
    line-height: 1.2;
}
.hero-subtitle {
    font-size: 15px;
    opacity: 0.75;
    max-width: 560px;
    margin-bottom: 0.5rem;
}

/* dataframes */
div[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
}

/* expander */
div[data-testid="stExpander"] {
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.08);
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

DATA_DISCLAIMER = (
    "All data shown is synthetically generated for demonstration purposes only. "
    "No real personal, telecom, or location data is used anywhere in this project."
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


@st.cache_data
def build_call_graph(calls):
    G = nx.Graph()
    for c in calls:
        G.add_edge(c["caller_id"], c["callee_id"])
    return G


@st.cache_data
def compute_burner_candidates(calls, window_days=5, max_calls=15):
    from datetime import datetime
    by_person = {}
    for c in calls:
        for role in ("caller_id", "callee_id"):
            pid = c[role]
            by_person.setdefault(pid, []).append(datetime.fromisoformat(c["timestamp"]))
    flagged = []
    for pid, times in by_person.items():
        times.sort()
        span = (times[-1] - times[0]).days
        if span <= window_days and len(times) <= max_calls:
            flagged.append({"person_id": pid, "total_calls": len(times), "active_window_days": span})
    return pd.DataFrame(flagged).sort_values("total_calls")


st.markdown(
    """
    <div style="padding: 1rem 0 0.5rem;">
        <p class="hero-eyebrow">network intelligence</p>
        <p class="hero-title">Criminal Network Link Analysis</p>
        <p class="hero-subtitle">Surfacing hidden connections, brokers, and anomalies
        across a synthetic call and location graph.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption("⚠️ " + DATA_DISCLAIMER)

calls, people, towers, pings = load_data()
G = build_call_graph(calls)
burner_df = compute_burner_candidates(calls)
communities_preview = nx.community.louvain_communities(G, seed=42)

with st.sidebar:
    st.header("About this project")
    st.markdown(
        "A graph-based link-analysis prototype inspired by techniques used "
        "in investigative intelligence work -- detecting burner-phone "
        "patterns, network brokers, hidden clusters, and probable "
        "unrecorded connections."
    )
    st.markdown("**Tech stack:** Neo4j · NetworkX · Streamlit · Folium")
    st.markdown("---")
    st.markdown(
        "⚠️ " + DATA_DISCLAIMER
    )
    st.markdown("---")
    st.caption("[View source on GitHub](https://github.com/anshujain1/Criminal-Network-Analysis)")

m1, m2, m3, m4 = st.columns(4)
m1.metric("People in network", G.number_of_nodes())
m2.metric("Recorded calls", len(calls))
m3.metric("Burner numbers flagged", len(burner_df))
m4.metric("Communities detected", len(communities_preview))

st.markdown("###")  # small vertical spacer

tab1, tab2, tab3, tab4 = st.tabs(
    [" Person Lookup", "Risk Flags", " Predicted Links", " Network Overview"]
)

with tab1:
    st.subheader("Look up a person")
    all_ids = sorted(set(list(people.keys()) + [c["caller_id"] for c in calls] + [c["callee_id"] for c in calls]))
    selected = st.selectbox("Select a person ID", all_ids, label_visibility="collapsed")

    col1, col2 = st.columns([1, 1.2], gap="large")

    with col1:
        st.markdown("#### Direct contacts")
        if selected in G:
            neighbors = list(G.neighbors(selected))
            st.write(f"**{len(neighbors)}** direct contact(s)")
            if neighbors:
                st.code(", ".join(neighbors), language=None)
        else:
            st.write("No call records for this person.")

        st.markdown("#### Risk assessment")
        is_flagged = selected in burner_df["person_id"].values
        if is_flagged:
            row = burner_df[burner_df["person_id"] == selected].iloc[0]
            st.error(
                f"**Flagged as probable burner phone**\n\n"
                f"Active for only {row['active_window_days']} day(s) with "
                f"{row['total_calls']} total calls -- matches a short-window, "
                f"low-volume pattern."
            )
        else:
            st.success("Not flagged by the burner-phone heuristic.")

        betweenness_note = "P_BURNER_01" == selected
        if betweenness_note:
            st.info(
                "This number also has the **highest betweenness centrality** "
                "in the network -- it's the sole bridge between otherwise "
                "separate community clusters."
            )

    with col2:
        st.markdown("#### 🗺️ Movement path (tower pings)")
        person_has_pings = any(p["person_id"] == selected for p in pings)
        if person_has_pings:
            m = build_person_map(selected, towers, pings)
            st_folium(m, width=550, height=420)
        else:
            st.write("No tower ping data for this person.")

with tab2:
    st.subheader("Burner-phone heuristic")
    st.caption(
        "Flags anyone whose entire calling activity falls within a short "
        "window and stays below a call-count threshold -- fully explainable, "
        "not a black-box model. Thresholds are adjustable in `scripts/evaluate.py`."
    )
    st.dataframe(
        burner_df.rename(columns={
            "person_id": "Person ID", "total_calls": "Total Calls",
            "active_window_days": "Active Window (days)"
        }),
        use_container_width=True, hide_index=True
    )
    with st.expander("📊 See measured accuracy (ground-truth evaluation)"):
        st.markdown(
            "- **Precision:** 1.0 · **Recall:** 1.0 · **F1:** 1.0 on the known "
            "injected burner, zero false positives\n"
            "- *(Single known positive in this dataset -- a method sanity "
            "check, not a statistically powered claim)*\n"
            "- Full methodology in `scripts/evaluate.py`"
        )

with tab3:
    st.subheader("Predicted (unrecorded) links")
    st.caption(
        "Pairs who share several common contacts but have never called each "
        "other directly -- computed via Jaccard coefficient. Classic, "
        "explainable link-prediction, not a black-box model."
    )
    jaccard_ranked, aa_ranked = predict_links(G, top_n=15)
    pred_df = pd.DataFrame(
        [{"Person 1": u, "Person 2": v, "Jaccard Score": round(s, 3)} for u, v, s in jaccard_ranked if s > 0]
    )
    st.dataframe(pred_df, use_container_width=True, hide_index=True)
    with st.expander("📊 See measured accuracy (ground-truth evaluation)"):
        st.markdown(
            "- Hidden-edge recovery test: **97.0%** mean percentile rank, "
            "**100%** hit-rate in top 50 predictions (50% / random-baseline "
            "would be chance level)\n"
            "- Full methodology in `scripts/evaluate.py`"
        )

with tab4:
    st.subheader("Full network overview")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Top 10 by degree centrality** (most-connected people)")
        degree = sorted(G.degree, key=lambda x: -x[1])[:10]
        st.dataframe(
            pd.DataFrame(degree, columns=["Person ID", "Connections"]),
            use_container_width=True, hide_index=True
        )

    with col2:
        st.markdown(f"**Detected communities** (Louvain, {len(communities_preview)} total)")
        for i, c in enumerate(communities_preview):
            st.write(f"**Community {i}** ({len(c)} members): {', '.join(sorted(c))}")

    st.markdown("**Cell tower coverage:**")
    st_folium(build_overview_map(towers), width=1100, height=420)
