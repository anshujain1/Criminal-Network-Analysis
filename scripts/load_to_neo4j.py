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
        session.execute_write(clear_database)

        session.execute_write(create_constraints)

        session.execute_write(load_people, people)

        session.execute_write(load_towers, towers)
        batch_size = 500
        for i in range(0, len(calls), batch_size):
            session.execute_write(load_calls, calls[i:i + batch_size])
        for i in range(0, len(pings), batch_size):
            session.execute_write(load_pings, pings[i:i + batch_size])

    driver.close()
    print("Done. Data loaded into Neo4j.")


if __name__ == "__main__":
    main()
