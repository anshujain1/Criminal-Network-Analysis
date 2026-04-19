
import os
from collections import defaultdict
from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "neo4j+s://<your-instance>.databases.neo4j.io")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "<your-password>")


def degree_centrality(session):
    query = """
        MATCH (p:Person)-[r:CALLED]-()
        RETURN p.person_id AS person_id, p.name AS name, count(r) AS degree
        ORDER BY degree DESC LIMIT 10
    """
    return list(session.run(query))


def betweenness_centrality_gds(session):
    #Requires GDS. Projects an in-memory graph then runs betweenness.
    session.run("""
        CALL gds.graph.project(
          'callGraph', 'Person',
          {CALLED: {orientation: 'UNDIRECTED'}}
        )
    """)
    result = list(session.run("""
        CALL gds.betweenness.stream('callGraph')
        YIELD nodeId, score
        RETURN gds.util.asNode(nodeId).person_id AS person_id,
               gds.util.asNode(nodeId).name AS name,
               score
        ORDER BY score DESC LIMIT 10
    """))
    session.run("CALL gds.graph.drop('callGraph')")
    return result


def community_detection_gds(session):
    #Requires GDS. Louvain community detection
    session.run("""
        CALL gds.graph.project(
          'callGraph2', 'Person',
          {CALLED: {orientation: 'UNDIRECTED'}}
        )
    """)
    result = list(session.run("""
        CALL gds.louvain.stream('callGraph2')
        YIELD nodeId, communityId
        RETURN communityId, collect(gds.util.asNode(nodeId).person_id) AS members
        ORDER BY size(members) DESC
    """))
    session.run("CALL gds.graph.drop('callGraph2')")
    return result


def detect_burner_candidates(session, window_days=5, max_calls=15):
    '''
    Heuristic (no ML needed, fully explainable):
    Flags any person whose FIRST and LAST call in the whole dataset are
    within `window_days` of each other, and who made fewer than `max_calls`
    total calls. This mirrors the real-world burner-phone signature:
    short-lived usage window + low call volume, aimed at existing contacts.'''

    query = """
        MATCH (p:Person)-[r:CALLED]-()
        WITH p, min(r.timestamp) AS first_seen, max(r.timestamp) AS last_seen, count(r) AS total_calls
        WHERE duration.between(first_seen, last_seen).days <= $window_days
          AND total_calls <= $max_calls
        RETURN p.person_id AS person_id, p.name AS name,
               first_seen, last_seen, total_calls
        ORDER BY total_calls ASC
    """
    return list(session.run(query, window_days=window_days, max_calls=max_calls))


def detect_colocation(session, window_minutes=30):
    """
    Finds pairs of people whose phones pinged the SAME tower within
    `window_minutes` of each other -- a possible in-person meeting,
    even if they never called each other directly.
    """
    query = """
        MATCH (p1:Person)-[r1:PINGED]->(t:Tower)<-[r2:PINGED]-(p2:Person)
        WHERE p1.person_id < p2.person_id
          AND abs(duration.between(r1.timestamp, r2.timestamp).minutes) <= $window_minutes
        RETURN p1.person_id AS person1, p2.person_id AS person2,
               t.tower_id AS tower, r1.timestamp AS time1, r2.timestamp AS time2
        LIMIT 25
    """
    return list(session.run(query, window_minutes=window_minutes))


def print_table(title, rows, columns):
    print(f"\n=== {title} ===")
    if not rows:
        print("  (no results)")
        return
    for row in rows:
        print("  " + " | ".join(f"{col}={row[col]}" for col in columns))


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        print_table("Top 10 by Degree Centrality (most contacts)",
                     degree_centrality(session), ["person_id", "name", "degree"])

        try:
            print_table("Top 10 by Betweenness Centrality (network brokers)",
                         betweenness_centrality_gds(session), ["person_id", "name", "score"])
            print_table("Community Detection (Louvain clusters)",
                         community_detection_gds(session), ["communityId", "members"])
        except Exception as e:
            print("\nNOTE: GDS-based analyses (betweenness, Louvain) failed or "
                  f"are unavailable on this Neo4j instance: {e}")
            print("Degree centrality and the heuristic detectors below still work "
                  "without GDS.")

        print_table("Burner Phone Candidates (short window, low volume)",
                     detect_burner_candidates(session),
                     ["person_id", "name", "first_seen", "last_seen", "total_calls"])

        print_table("Co-location Events (same tower, tight time window)",
                     detect_colocation(session),
                     ["person1", "person2", "tower", "time1", "time2"])

    driver.close()


if __name__ == "__main__":
    main()
