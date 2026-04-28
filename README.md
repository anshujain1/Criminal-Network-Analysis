# Criminal Network Link Analysis

A graph-based link-analysis prototype inspired by techniques used in law
enforcement and intelligence investigations (similar in spirit to tools
like IBM i2 Analyst's Notebook or Palantir Gotham, at a student-project
scale). It models a network of people, their call records, and their
approximate phone-tower locations, then applies graph algorithms to
surface investigative leads: who's a central hub, who's a hidden broker
between groups, which phone number behaves like a disposable "burner,"
and which pairs of people are probably connected even though no call
between them was ever recorded.

> **Data disclaimer:** All data in this project — people, phone numbers,
> call records, and tower locations — is **synthetically generated**
> (`scripts/generate_synthetic_data.py`). No real personal, telecom, or
> location data is used anywhere. This is a technique demonstration, not
> a tool built on or for real investigative data.

## What it does

- **Graph modeling (Neo4j):** People and cell towers as nodes; calls and
  tower pings as relationships.
- **Burner-phone detection:** A fully explainable heuristic that flags
  any number whose entire calling activity falls within a short time
  window and stays below a call-count threshold — the real-world
  signature of a disposable phone.
- **Co-location detection:** Finds pairs of people whose phones pinged
  the *same* cell tower within a tight time window, surfacing probable
  in-person meetings even when there's no call record between them.
- **Centrality analysis:** Degree centrality (most-connected people) and
  betweenness centrality (who bridges otherwise-separate groups — the
  "broker" role).
- **Community detection:** Louvain clustering to find sub-groups within
  the network.
- **Link prediction:** Jaccard coefficient and Adamic-Adar index flag
  pairs who share many contacts but have never called each other
  directly — a probable, unconfirmed connection worth manual review.
  (Deliberately uses classic, explainable graph methods rather than a
  black-box model — every score is traceable to shared contacts.)
- **Geospatial movement mapping:** Plots a person's tower pings over
  time as a path on a map, answering "where did this person pass
  through?"
- **Interactive dashboard (Streamlit):** Search a person, see their
  contacts, risk flags, and movement path in one view.

## Evaluation (ground-truth, measured)

Because the dataset is synthetic, the true burner number and the true
call graph are known — so instead of eyeballing results, `scripts/evaluate.py`
measures them properly:

- **Burner detection:** precision 1.0, recall 1.0 on the known burner,
  zero false positives. (Note: with a single true positive in the
  dataset this is a method sanity check, not a statistically powered
  claim — stated explicitly rather than glossed over.)
- **Link prediction (hidden-edge recovery):** 19 real edges were hidden
  and re-predicted using Adamic-Adar on the remaining graph. Mean
  percentile rank of recovered edges: **97.0%** (50% = random guessing).
  Hit-rate in the top 50 predictions out of 710 candidate pairs: **100%**.
- **A worthwhile failure, kept in the record:** the first version of the
  data generator assigned contacts uniformly at random, giving the
  network almost no community structure. Link prediction on that
  version scored *below* random (40.1% percentile, 4.3% hit-rate) —
  because Jaccard/Adamic-Adar rely on shared-neighbor signal that
  simply didn't exist in a random graph. Rebuilding the generator to
  produce realistic clustered communities (people mostly call within
  their own group, plus a few cross-group bridges) fixed this. This is
  documented because measuring *before* fixing is the point of having
  an evaluation harness at all.
- **Bonus finding:** the injected burner number has the **highest
  betweenness centrality in the entire network** — it's the only
  connection between otherwise-separate community clusters, which is
  exactly the kind of anomaly betweenness centrality is designed to
  surface.

Run it yourself: `python scripts/evaluate.py` (writes `evaluation_report.json`).

## Tests

Unit tests cover the burner-detection heuristic's edge cases (short
burst, long-running number, high-volume number, empty input, boundary
conditions) and the data generator's structural invariants (unique IDs,
referential integrity, valid coordinates).

```bash
pip install pytest
python -m pytest tests/ -v
```

## Tech stack

Python · Neo4j (+ Graph Data Science library) · NetworkX · Streamlit ·
Folium

## Project structure

```
data/                        synthetic CSVs (people, calls, towers, pings)
scripts/
  generate_synthetic_data.py builds the synthetic dataset from scratch
  local_sanity_check.py      validates analysis logic with NetworkX (no DB needed)
  load_to_neo4j.py           loads CSVs into a Neo4j instance
  analyze_network.py         centrality / community / burner / co-location via Cypher
  link_prediction.py         Jaccard & Adamic-Adar link prediction
  geospatial_map.py          builds movement maps with Folium
  evaluate.py                 ground-truth evaluation of burner detection & link prediction
tests/                        pytest unit tests
app.py                       Streamlit dashboard tying it all together
requirements.txt
```

## How to run

**1. Generate the synthetic data**
```bash
pip install -r requirements.txt
python scripts/generate_synthetic_data.py
```

**2. Validate locally (no database needed)**
```bash
python scripts/local_sanity_check.py
python scripts/link_prediction.py
python scripts/geospatial_map.py P001   # writes an HTML map to screenshots/
```

**3. (Optional) Run the full Neo4j pipeline**
- Create a free instance at [Neo4j Aura Free](https://neo4j.com/cloud/aura-free/)
- Set environment variables:
  ```bash
  export NEO4J_URI="neo4j+s://<your-instance>.databases.neo4j.io"
  export NEO4J_USER="neo4j"
  export NEO4J_PASSWORD="<your-password>"
  ```
- Load and analyze:
  ```bash
  python scripts/load_to_neo4j.py
  python scripts/analyze_network.py
  ```

**4. Launch the dashboard**
```bash
streamlit run app.py
```

## Honest scope notes

- Real telecom call-detail records and cell-tower data are legally
  restricted and unavailable to student projects — this project uses
  synthetic data designed to reproduce the *structural patterns*
  investigators look for, not real surveillance data.
- Link prediction here uses interpretable graph-theoretic scores
  (Jaccard / Adamic-Adar), not a trained GNN. Swapping in node2vec + a
  classifier is a natural next step if extended further.
- Betweenness centrality and Louvain community detection require
  Neo4j's Graph Data Science library; `analyze_network.py` degrades
  gracefully if GDS isn't available on a given instance, and
  `local_sanity_check.py` reproduces the same results via NetworkX
  regardless.

## Author

Built as an independent project exploring graph databases and network
analysis techniques for AI/Data Science coursework.
