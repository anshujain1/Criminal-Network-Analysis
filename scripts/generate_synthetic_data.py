"""
generate_synthetic_data.py

Generates a fully SYNTHETIC dataset for the Criminal Network Analysis project:
  - people.csv        : the individuals in the network
  - calls.csv         : call detail records (CDRs) between people
  - cell_towers.csv    : cell tower locations (lat/long)
  - tower_pings.csv    : which tower each person's phone connected to, and when

IMPORTANT: All data here is randomly generated for demonstration purposes only.
No real personal, telecom, or location data is used anywhere in this project.

Design notes (read this before you run it):
  - We build a "core network" of people who call each other somewhat regularly
    (this is your normal social graph).
  - We inject ONE burner-phone pattern: a short-lived phone number that calls
    a small cluster of core people a handful of times over a short window,
    then never appears again. This is the pattern real investigators look for.
  - We inject co-location: a few people ping the same cell tower within the
    same time window multiple times, even if they never call each other --
    this simulates the "these two people's phones were near each other"
    signal that's used in real link analysis.
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)  # reproducible output

NUM_PEOPLE = 40
NUM_TOWERS = 12
SIM_DAYS = 30
START_DATE = datetime(2026, 6, 1)

FIRST_NAMES = ["Aman", "Rohit", "Priya", "Sana", "Vikram", "Neha", "Karan",
               "Divya", "Arjun", "Meera", "Sameer", "Anjali", "Rahul", "Pooja",
               "Vivek", "Isha", "Manish", "Ritu", "Aditya", "Kavya"]
LAST_NAMES = ["Sharma", "Verma", "Gupta", "Khan", "Reddy", "Nair", "Chauhan",
              "Malhotra", "Bose", "Iyer"]

# roughly centered around a fictional metro area, purely synthetic coordinates
BASE_LAT, BASE_LON = 28.6, 77.2


def make_people(n):
    people = []
    for i in range(1, n + 1):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        phone = f"9{random.randint(100000000, 999999999)}"
        people.append({"person_id": f"P{i:03d}", "name": name, "phone": phone})
    return people


def make_towers(n):
    towers = []
    for i in range(1, n + 1):
        lat = BASE_LAT + random.uniform(-0.15, 0.15)
        lon = BASE_LON + random.uniform(-0.15, 0.15)
        towers.append({"tower_id": f"T{i:03d}", "lat": round(lat, 5), "lon": round(lon, 5)})
    return towers


def random_timestamp(day_offset_range=(0, SIM_DAYS)):
    day = random.randint(*day_offset_range)
    seconds = random.randint(0, 86399)
    return START_DATE + timedelta(days=day, seconds=seconds)


def make_calls(people):
    """Core social-graph calls: most people call a handful of regular contacts."""
    calls = []
    call_id = 1
    for person in people:
        num_contacts = random.randint(2, 6)
        contacts = random.sample([p for p in people if p != person], num_contacts)
        for contact in contacts:
            num_calls = random.randint(1, 8)
            for _ in range(num_calls):
                ts = random_timestamp()
                calls.append({
                    "call_id": f"C{call_id:05d}",
                    "caller_id": person["person_id"],
                    "callee_id": contact["person_id"],
                    "timestamp": ts.isoformat(),
                    "duration_sec": random.randint(15, 900),
                })
                call_id += 1
    return calls, call_id


def inject_burner_phone(people, calls, start_call_id):
    """
    Injects one classic burner-phone pattern:
      - A new, short-lived number
      - Calls a small cluster of EXISTING people (the 'suspect cluster')
      - Only over a tight 4-day window
      - Never appears before or after that window
    """
    call_id = start_call_id
    burner = {"person_id": "P_BURNER_01", "name": "UNKNOWN (Burner)",
              "phone": f"7{random.randint(10000000, 99999999)}"}
    suspect_cluster = random.sample(people, 4)

    burst_start = random.randint(10, SIM_DAYS - 5)
    for target in suspect_cluster:
        num_calls = random.randint(2, 4)
        for _ in range(num_calls):
            ts = random_timestamp(day_offset_range=(burst_start, burst_start + 4))
            calls.append({
                "call_id": f"C{call_id:05d}",
                "caller_id": burner["person_id"],
                "callee_id": target["person_id"],
                "timestamp": ts.isoformat(),
                "duration_sec": random.randint(10, 180),  # burner calls tend to be short
            })
            call_id += 1

    return burner, suspect_cluster, calls


def make_tower_pings(people, towers, burner, suspect_cluster):
    """
    Each person pings towers throughout the sim as their phone moves around.
    We deliberately make the suspect cluster + burner ping the SAME tower
    within the SAME tight time window at least once, to simulate co-location
    (e.g. a physical meeting) even though this isn't captured by call records.
    """
    pings = []
    ping_id = 1
    all_people = people + [burner]

    for person in all_people:
        num_pings = random.randint(20, 60)
        for _ in range(num_pings):
            tower = random.choice(towers)
            ts = random_timestamp()
            pings.append({
                "ping_id": f"PG{ping_id:05d}",
                "person_id": person["person_id"],
                "tower_id": tower["tower_id"],
                "timestamp": ts.isoformat(),
            })
            ping_id += 1

    # Inject a deliberate co-location event: suspect cluster + burner
    # all ping the same tower within a 30-minute window on the same day.
    meeting_tower = random.choice(towers)
    meeting_day = random.randint(10, SIM_DAYS - 5)
    base_time = START_DATE + timedelta(days=meeting_day, hours=14)
    for person in suspect_cluster + [burner]:
        ts = base_time + timedelta(minutes=random.randint(0, 30))
        pings.append({
            "ping_id": f"PG{ping_id:05d}",
            "person_id": person["person_id"],
            "tower_id": meeting_tower["tower_id"],
            "timestamp": ts.isoformat(),
        })
        ping_id += 1

    return pings


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    people = make_people(NUM_PEOPLE)
    towers = make_towers(NUM_TOWERS)
    calls, next_call_id = make_calls(people)
    burner, suspect_cluster, calls = inject_burner_phone(people, calls, next_call_id)
    pings = make_tower_pings(people, towers, burner, suspect_cluster)

    write_csv("data/people.csv", people, ["person_id", "name", "phone"])
    write_csv("data/cell_towers.csv", towers, ["tower_id", "lat", "lon"])
    write_csv("data/calls.csv", calls, ["call_id", "caller_id", "callee_id", "timestamp", "duration_sec"])
    write_csv("data/tower_pings.csv", pings, ["ping_id", "person_id", "tower_id", "timestamp"])

    print(f"Generated {len(people)} people, {len(towers)} towers, "
          f"{len(calls)} calls, {len(pings)} tower pings.")
    print(f"Burner phone: {burner['person_id']} ({burner['phone']})")
    print(f"Suspect cluster it contacted: {[p['person_id'] for p in suspect_cluster]}")
    print("All data is synthetic and generated for demonstration purposes only.")
