"""Graph theory engine for the Mumbai local train network (Discrete Mathematics, Module 6 and Module 3).

The idea: a station is a vertex, a track between two neighbouring stations is an edge.
Everything below is written by hand (no graph library), using only the standard library:

    BFS ............ shortest route, connected pieces
    Dijkstra ....... route with the fewest interchanges (states are (station, service))
    Degrees ........ handshake lemma, Euler's theorem, Hamiltonian dead-end argument
    Warshall ....... transitive closure of the "services share a station" relation
"""
import heapq
from collections import defaultdict, deque

from data import ANCHORS, SERVICES


class Network:
    def __init__(self, services=SERVICES):
        self.services = services
        self.adj = defaultdict(set)          # adjacency list: station -> set of neighbouring stations
        self.edge_services = {}              # frozenset({a, b}) -> set of service ids that run on that track
        self.station_services = defaultdict(set)
        for sid, s in services.items():
            seq = s["seq"]
            for st in seq:
                self.station_services[st].add(sid)
            for a, b in zip(seq, seq[1:]):   # consecutive stations on a service = one edge
                self.adj[a].add(b)
                self.adj[b].add(a)
                self.edge_services.setdefault(frozenset((a, b)), set()).add(sid)
        self.stations = sorted(self.adj)                                   # the vertex set V
        self.edges = sorted(tuple(sorted(e)) for e in self.edge_services)  # the edge set E

    # ---------- basic facts ----------
    def degree(self, v):
        return len(self.adj[v])

    def counts(self):
        return {"V": len(self.stations), "E": len(self.edges), "C": len(self.components()),
                "degree_sum": sum(self.degree(x) for x in self.stations)}

    # ---------- BFS: shortest path by number of stops ----------
    def bfs(self, src, closed=frozenset()):
        """Visit stations layer by layer. dist[v] = fewest stops from src, parent[v] = previous station."""
        dist, parent = {src: 0}, {src: None}
        q = deque([src])
        while q:
            u = q.popleft()
            for w in sorted(self.adj[u]):
                if w not in dist and w not in closed:
                    dist[w] = dist[u] + 1
                    parent[w] = u
                    q.append(w)
        return dist, parent

    @staticmethod
    def path_from(parent, dst):
        out = []
        while dst is not None:
            out.append(dst)
            dst = parent[dst]
        return out[::-1]

    # ---------- trip planner: Dijkstra over (station, service) states ----------
    def route(self, src, dst, mode="stops", closed=frozenset()):
        """mode 'stops' minimises (stops, interchanges); mode 'changes' minimises (interchanges, stops)."""
        for s in (src, dst):
            if s not in self.adj:
                raise ValueError(f"Unknown station: {s}")
            if s in closed:
                return None
        weight = (lambda stop, chg: (stop, chg)) if mode == "stops" else (lambda stop, chg: (chg, stop))
        start = [(src, sv) for sv in sorted(self.station_services[src])]
        best = {st: weight(0, 0) for st in start}
        parent = {st: None for st in start}
        heap = [(best[st], st) for st in start]
        heapq.heapify(heap)
        goal = None
        while heap:
            cost, state = heapq.heappop(heap)
            if cost > best.get(state, (1 << 30, 1 << 30)):
                continue
            st, sv = state
            if st == dst:
                goal = state
                break
            stop_c = cost if mode == "stops" else (cost[1], cost[0])
            nxt = []
            for w in self.adj[st]:                     # ride one stop on the same service
                if w in closed:
                    continue
                if sv in self.edge_services[frozenset((st, w))]:
                    nxt.append(((w, sv), weight(stop_c[0] + 1, stop_c[1])))
            for sv2 in self.station_services[st]:      # or change service at this station
                if sv2 != sv:
                    nxt.append(((st, sv2), weight(stop_c[0], stop_c[1] + 1)))
            for state2, c2 in nxt:
                if c2 < best.get(state2, (1 << 30, 1 << 30)):
                    best[state2] = c2
                    parent[state2] = state
                    heapq.heappush(heap, (c2, state2))
        if goal is None:
            return None
        states = []
        s = goal
        while s is not None:
            states.append(s)
            s = parent[s]
        states.reverse()
        legs = []
        for (st, sv) in states:
            if legs and legs[-1]["stations"][-1] != st:
                legs[-1]["stations"].append(st)
            else:
                legs.append({"service": sv, "stations": [st]})
        legs = [l for l in legs if len(l["stations"]) > 1] or legs[:1]
        for l in legs:
            l["stops"] = len(l["stations"]) - 1
            l["name"] = self.services[l["service"]]["name"]
            l["group"] = self.services[l["service"]]["group"]
        path = list(legs[0]["stations"])
        for l in legs[1:]:
            path.extend(l["stations"][1:])
        return {"legs": legs, "stops": sum(l["stops"] for l in legs), "interchanges": len(legs) - 1, "path": path}

    # ---------- connectivity: what if a station closes? ----------
    def components(self, closed=frozenset()):
        """Connected components (largest first), found by running BFS from every unvisited station."""
        seen, comps = set(), []
        for v in self.stations:
            if v in seen or v in closed:
                continue
            dist, _ = self.bfs(v, closed)
            comps.append(sorted(dist))
            seen.update(dist)
        comps.sort(key=len, reverse=True)
        return comps

    def disruption(self, closed):
        closed = frozenset(c for c in closed if c in self.adj)
        comps = self.components(closed)
        main = set(comps[0]) if comps else set()
        stranded = sorted(v for v in self.stations if v not in closed and v not in main)
        return {"closed": sorted(closed), "pieces": [{"size": len(c), "sample": c[:4]} for c in comps],
                "stranded": stranded, "connected": len(comps) <= 1}

    def critical_stations(self):
        """Cut vertices: close each station in turn; if the network falls apart it is critical.
        Returns [(station, stations cut off)] with the biggest impact first."""
        out = []
        for v in self.stations:
            comps = self.components(frozenset([v]))
            if len(comps) > 1:
                out.append((v, len(self.stations) - 1 - len(comps[0])))
        out.sort(key=lambda x: (-x[1], x[0]))
        return out

    # ---------- Euler and Hamilton ----------
    def odd_stations(self):
        return sorted(v for v in self.stations if self.degree(v) % 2)

    def euler_status(self):
        """Euler's theorem: circuit needs 0 odd-degree vertices, path needs exactly 2."""
        odd = len(self.odd_stations())
        return "circuit" if odd == 0 else "path" if odd == 2 else "none"

    def hamilton_status(self):
        """A dead end (degree 1) must be the start or end of any path through every station."""
        pendants = sorted(v for v in self.stations if self.degree(v) == 1)
        return {"pendants": pendants, "path_possible": len(pendants) <= 2, "cycle_possible": len(pendants) == 0}

    # ---------- relation on services (Module 3) ----------
    def service_relation(self):
        """a R b when services a and b share a station. Returns the 0/1 matrix and its Warshall closure."""
        ids = list(self.services)
        n = len(ids)
        M = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                if set(self.services[ids[i]]["seq"]) & set(self.services[ids[j]]["seq"]):
                    M[i][j] = M[j][i] = 1
        W = [r[:] for r in M]                  # Warshall's algorithm
        for k in range(n):
            for i in range(n):
                for j in range(n):
                    W[i][j] = W[i][j] or (W[i][k] and W[k][j])
        return {"ids": ids, "M": M, "closure": W}


def layout(net=None):
    """Schematic coordinates: anchored stations are fixed, the rest are spread evenly between anchors."""
    net = net or Network()
    pos = {}
    for sid, s in net.services.items():
        seq = s["seq"]
        for st in seq:
            if st in ANCHORS and st not in pos:
                pos[st] = ANCHORS[st]
    for sid, s in net.services.items():
        seq = s["seq"]
        i = 0
        while i < len(seq):
            if seq[i] in pos:
                i += 1
                continue
            j = i
            while j < len(seq) and seq[j] not in pos:
                j += 1
            if i == 0 or j == len(seq):
                raise ValueError(f"Add an anchor for the end of service {sid} near {seq[i]}")
            (x0, y0), (x1, y1) = pos[seq[i - 1]], pos[seq[j]]
            n = j - i + 1
            for k in range(i, j):
                t = (k - i + 1) / n
                pos[seq[k]] = (round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t))
            i = j
    return pos
