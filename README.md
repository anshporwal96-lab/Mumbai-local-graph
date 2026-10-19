# Mumbai Local Graph Lab

A Python + Flask web app that treats the Mumbai suburban railway (Western, Central, Harbour and
Trans-Harbour lines) as a graph and uses Discrete Mathematics (mainly Module 6, plus Modules 3 and 5) to
answer questions about it.

## Run

    pip install -r requirements.txt
    python app.py
    # open http://127.0.0.1:5000

Run the tests (standard library only): `python tests/test_network.py`
(`networkx` is optional; if installed, the tests cross-check results against it.)

## What it does

| Tab | Idea | Syllabus link |
|---|---|---|
| Plan a trip | Fewest stops (BFS) or fewest interchanges (Dijkstra with tuple costs on (station, service) states) | Module 6: paths, shortest path |
| Network facts | 116 vertices, 119 edges, degree table, handshake lemma, diameter/radius/centre, cut vertices and bridges, cycle rank, Euler's formula, planarity (Kuratowski) | Module 6 |
| Ride every track | Euler path/circuit test, Chinese postman route (min-weight matching of odd stations), Hamiltonian impossibility from dead ends | Module 6 |
| What if | Close stations, see connected components and your re-routed trip | Module 6: connectivity |
| Services | "Two services share a station" as a relation: Boolean matrix, powers, Warshall closure | Module 3 (and Module 5, functions on states) |

## Files

- `data.py`: station sequences per service, line colours, schematic anchor points
- `network.py`: all graph algorithms (no web code)
- `app.py`: Flask routes and a JSON API (`/api/network`, `/api/route`, `/api/analysis`, `/api/euler`, `/api/disrupt`, `/api/relation`)
- `templates/`, `static/`: the page, SVG map and styling (works offline, no CDN)
- `tests/test_network.py`: 19 tests

## Limits to mention in the viva

- Station lists come from the Wikipedia pages for each line; about 116 suburban stations, no metro or monorail.
- Timetables and fast/slow trains are ignored, so distances are in stops, not minutes.
- The map is a schematic: stations between fixed anchor points are spaced evenly, and a few lines appear to cross
  without a station (the real tracks go over or under each other).
- Verify station data against the official Western/Central Railway maps before presenting it as exact.
