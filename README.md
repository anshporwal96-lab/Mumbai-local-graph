# Mumbai Local Graph Lab

A Python + Flask web app that treats the Mumbai suburban railway (Western, Central, Harbour and
Trans-Harbour lines) as a graph and uses Discrete Mathematics (Module 6 Graphs, Module 3 Relations) to
answer questions about it.

## Run

    pip install -r requirements.txt
    python app.py
    # open http://127.0.0.1:5000

Run the tests (standard library only): `python tests/test_network.py`

## The idea

Station = vertex, track between neighbouring stations = edge. 116 vertices, 119 edges.
Each service's station list is turned into edges by pairing consecutive stations.

## The four tabs

| Tab | What it shows | Concept |
|---|---|---|
| Plan a trip | Shortest route; also fewest interchanges | BFS, shortest path |
| Critical stations | Which stations split the network if closed, plus a close-a-station simulator | Connectivity, cut vertices, components |
| Euler and Hamilton | Why you can't ride every track once (14 odd stations) or visit every station once (6 dead ends) | Euler's theorem, handshake lemma, Hamiltonian path |
| Services (relation) | "Two services share a station" as a 0/1 matrix and its Warshall closure | Module 3: relations, Warshall |

Each result has a "How this works" box with the plain-English explanation.

## Files

- `data.py`: station sequences per service, line colours, schematic anchor points
- `network.py`: all the graph algorithms (about 200 lines, no web code)
- `app.py`: Flask routes and a small JSON API
- `templates/`, `static/`: the page, SVG map and styling (works offline, no CDN)
- `tests/test_network.py`: 16 tests

## Limits to mention in the viva

- Station lists come from the Wikipedia pages for each line; about 116 suburban stations, no metro or monorail.
- Timetables and fast/slow trains are ignored, so distances are in stops, not minutes.
- The map is a schematic: a few lines appear to cross without a station (the real tracks go over or under each other).
- Verify station data against the official Western/Central Railway maps before presenting it as exact.
