"""Flask server for the Mumbai local train graph project.

Run:  python app.py      then open http://127.0.0.1:5000
"""
from flask import Flask, jsonify, render_template, request

from data import FULL_NAMES, GROUPS, SERVICES
from network import Network, layout

app = Flask(__name__)
NET = Network()
POS = layout(NET)

# The network never changes, so compute the whole-network answers once at start-up.
COUNTS = NET.counts()
ODD = NET.odd_stations()
CRITICAL = NET.critical_stations()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/network")
def api_network():
    stations = [{
        "name": v, "full": FULL_NAMES.get(v, v), "x": POS[v][0], "y": POS[v][1],
        "services": sorted(NET.station_services[v]), "degree": NET.degree(v),
        "groups": sorted({SERVICES[s]["group"] for s in NET.station_services[v]}),
    } for v in NET.stations]
    edges = [{"a": a, "b": b, "services": sorted(NET.edge_services[frozenset((a, b))]),
              "groups": sorted({SERVICES[s]["group"] for s in NET.edge_services[frozenset((a, b))]})} for a, b in NET.edges]
    return jsonify({"groups": GROUPS, "services": {k: {"name": v["name"], "group": v["group"]} for k, v in SERVICES.items()},
                    "stations": stations, "edges": edges})


@app.route("/api/route")
def api_route():
    src, dst = request.args.get("src", ""), request.args.get("dst", "")
    mode = request.args.get("mode", "stops")
    if mode not in ("stops", "changes"):
        return jsonify({"error": "mode must be stops or changes"}), 400
    for s in (src, dst):
        if s not in NET.adj:
            return jsonify({"error": f"'{s}' is not a station on this map."}), 400
    return jsonify({"route": NET.route(src, dst, mode)})


@app.route("/api/analysis")
def api_analysis():
    """Numbers for the strip at the top and the critical-stations table."""
    return jsonify({"counts": COUNTS, "odd_count": len(ODD),
                    "cut_vertices": len(CRITICAL),
                    "critical": [{"station": v, "stranded": n} for v, n in CRITICAL[:10]]})


@app.route("/api/euler")
def api_euler():
    return jsonify({"odd": ODD, "status": NET.euler_status(), "hamilton": NET.hamilton_status()})


@app.route("/api/disrupt", methods=["POST"])
def api_disrupt():
    body = request.get_json(silent=True) or {}
    closed = [c for c in body.get("closed", []) if c in NET.adj]
    out = NET.disruption(closed)
    src, dst = body.get("src"), body.get("dst")
    if src in NET.adj and dst in NET.adj:
        out["route"] = NET.route(src, dst, body.get("mode", "stops"), frozenset(closed))
        out["route_checked"] = True
    return jsonify(out)


@app.route("/api/relation")
def api_relation():
    r = NET.service_relation()
    r["names"] = {k: SERVICES[k]["name"] for k in r["ids"]}
    r["groups"] = {k: SERVICES[k]["group"] for k in r["ids"]}
    return jsonify(r)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
