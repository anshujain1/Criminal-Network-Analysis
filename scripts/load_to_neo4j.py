"""
load_to_neo4j.py

Loads the synthetic dataset (data/*.csv) into a Neo4j database.

Graph schema:
  (:Person {person_id, name, phone})
  (:Tower {tower_id, lat, lon})

  (:Person)-[:CALLED {timestamp, duration_sec}]->(:Person)
  (:Person)-[:PINGED {timestamp}]->(:Tower)

Before running:
  1. Create a free Neo4j Aura instance: https://neo4j.com/cloud/aura-free/
  2. Copy your connection URI, username, and password
  3. Set them as environment variables (recommended) or edit the constants below:
       export NEO4J_URI="neo4j+s://xxxx.databases.neo4j.io"
       export NEO4J_USER="neo4j"
       export NEO4J_PASSWORD="your-password"
  4. pip install neo4j
"""

import csv
import os
from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "neo4j+s://<your-instance>.databases.neo4j.io")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "<your-password>")


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def clear_database(tx):
    tx.run("MATCH (n) DETACH DELETE n")


def create_constraints(tx):
    tx.run("CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.person_id IS UNIQUE")
    tx.run("CREATE CONSTRAINT tower_id IF NOT EXISTS FOR (t:Tower) REQUIRE t.tower_id IS UNIQUE")


def load_people(tx, people):
    tx.run("""
        UNWIND $rows AS row
        MERGE (p:Person {person_id: row.person_id})
        SET p.name = row.name, p.phone = row.phone
    """, rows=people)


def load_towers(tx, towers):
    tx.run("""
        UNWIND $rows AS row
        MERGE (t:Tower {tower_id: row.tower_id})
        SET t.lat = toFloat(row.lat), t.lon = toFloat(row.lon)
    """, rows=towers)


def load_calls(tx, calls):
    # The burner number won't exist in people.csv, so MERGE creates a
    # minimal Person node for it automatically (this is realistic --
    # investigators often only have the number, not an identity, at first).
    tx.run("""
        UNWIND $rows AS row
        MERGE (caller:Person {person_id: row.caller_id})
        MERGE (callee:Person {person_id: row.callee_id})
        CREATE (caller)-[:CALLED {
            timestamp: datetime(row.timestamp),
            duration_sec: toInteger(row.duration_sec)
        }]->(callee)
    """, rows=calls)


def load_pings(tx, pings):
    tx.run("""
        UNWIND $rows AS row
        MATCH (p:Person {person_id: row.person_id})
        MATCH (t:Tower {tower_id: row.tower_id})
        CREATE (p)-[:PINGED {timestamp: datetime(row.timestamp)}]->(t)
    """, rows=pings)


def main():
    people = read_csv("data/people.csv")
    towers = read_csv("data/cell_towers.csv")
    calls = read_csv("data/calls.csv")
    pings = read_csv("data/tower_pings.csv")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        print("Clearing existing data...")
        session.execute_write(clear_database)

        print("Creating constraints...")
        session.execute_write(create_constraints)

        print(f"Loading {len(people)} people...")
        session.execute_write(load_people, people)

        print(f"Loading {len(towers)} towers...")
        session.execute_write(load_towers, towers)

        print(f"Loading {len(calls)} calls...")
        # batch to keep transactions reasonably sized
        batch_size = 500
        for i in range(0, len(calls), batch_size):
            session.execute_write(load_calls, calls[i:i + batch_size])

        print(f"Loading {len(pings)} tower pings...")
        for i in range(0, len(pings), batch_size):
            session.execute_write(load_pings, pings[i:i + batch_size])

    driver.close()
    print("Done. Data loaded into Neo4j.")


if __name__ == "__main__":
    main()
