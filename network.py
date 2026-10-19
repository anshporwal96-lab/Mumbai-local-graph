"""Graph theory engine for the Mumbai local train network (Discrete Mathematics, Module 6).

Every algorithm here is written by hand from the syllabus (BFS, Dijkstra with tuple costs, Tarjan,
Hierholzer, bitmask matching, Kuratowski search), so each one can be explained in a viva.
Only the standard library is used.
"""
import heapq
import itertools
from collections import defaultdict, deque

from data import ANCHORS, GROUPS, SERVICES


class Network:
    def __init__(self, services=SERVICES):
        self.services = services
        self.adj = defaultdict(set)          # simple undirected graph of stations
        self.edge_services = {}              # frozenset({a, b}) -> set of service ids
        self.station_services = defaultdict(set)
        for sid, s in services.items():
            seq = s["seq"]
            for st in seq:
                self.station_services[st].add(sid)
            for a, b in zip(seq, seq[1:]):
                self.adj[a].add(b)
                self.adj[b].add(a)
                self.edge_services.setdefault(frozenset((a, b)), set()).add(sid)
        self.stations = sorted(self.adj)
        self.edges = sorted(tuple(sorted(e)) for e in self.edge_services)

    # ---------- basic facts ----------
    def degree(self, v):
        return len(self.adj[v])

    def edge_key(self, a, b):
        return frozenset((a, b))

    # ---------- shortest paths (BFS) ----------
    def bfs(self, src, closed=frozenset()):
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
            # ride one stop on the same service
            nxt = []
            for w in self.adj[st]:
                if w in closed:
                    continue
                if sv in self.edge_services[self.edge_key(st, w)]:
                    nxt.append(((w, sv), weight(stop_c[0] + 1, stop_c[1])))
            # change service at this station
            for sv2 in self.station_services[st]:
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

    # ---------- connectivity ----------
    def components(self, closed=frozenset()):
        seen, comps = set(), []
        for v in self.stations:
            if v in seen or v in closed:
                continue
            dist, _ = self.bfs(v, closed)
            comps.append(sorted(dist))
            seen.update(dist)
        comps.sort(key=len, reverse=True)
        return comps

    def articulation_and_bridges(self):
        """Tarjan's low-link algorithm."""
        disc, low, parent = {}, {}, {}
        art, bridges, timer = set(), [], [0]

        def dfs(u):
            disc[u] = low[u] = timer[0]
            timer[0] += 1
            children = 0
            for w in sorted(self.adj[u]):
                if w not in disc:
                    parent[w] = u
                    children += 1
                    dfs(w)
                    low[u] = min(low[u], low[w])
                    if parent.get(u) is None and children > 1:
                        art.add(u)
                    if parent.get(u) is not None and low[w] >= disc[u]:
                        art.add(u)
                    if low[w] > disc[u]:
                        bridges.append(tuple(sorted((u, w))))
                elif w != parent.get(u):
                    low[u] = min(low[u], disc[w])

        for v in self.stations:
            if v not in disc:
                parent[v] = None
                dfs(v)
        return sorted(art), sorted(bridges)

    def impact_of_closing(self, v):
        """Number of other stations cut off from the largest remaining piece when v is closed."""
        comps = self.components(closed=frozenset([v]))
        return (len(self.stations) - 1) - len(comps[0]) if comps else 0

    # ---------- distances ----------
    def eccentricities(self):
        ecc, far = {}, {}
        for v in self.stations:
            dist, _ = self.bfs(v)
            m = max(dist.values())
            ecc[v] = m
            far[v] = sorted(w for w, d in dist.items() if d == m)[0]
        return ecc, far

    def distance_summary(self):
        ecc, far = self.eccentricities()
        diam = max(ecc.values())
        rad = min(ecc.values())
        a = sorted(v for v in self.stations if ecc[v] == diam)[0]
        _, parent = self.bfs(a)
        path = self.path_from(parent, far[a])
        total, pairs = 0, 0
        for v in self.stations:
            dist, _ = self.bfs(v)
            total += sum(dist.values())
            pairs += len(dist) - 1
        return {"diameter": diam, "radius": rad, "diameter_path": path,
                "centre": sorted(v for v in self.stations if ecc[v] == rad),
                "periphery": sorted(v for v in self.stations if ecc[v] == diam),
                "average_distance": total / pairs}

    # ---------- Euler and Hamilton ----------
    def odd_stations(self):
        return sorted(v for v in self.stations if self.degree(v) % 2)

    def chinese_postman(self):
        """Fewest repeated segments needed to ride every segment: Euler's theorem plus min-weight matching."""
        odd = self.odd_stations()
        k = len(odd)
        dist, par = {}, {}
        for v in odd:
            dist[v], par[v] = self.bfs(v)
        INF = 1 << 30
        memo = {}

        def best(mask):
            if mask == (1 << k) - 1:
                return 0, ()
            if mask in memo:
                return memo[mask]
            i = next(j for j in range(k) if not mask >> j & 1)
            res = (INF, ())
            for j in range(i + 1, k):
                if not mask >> j & 1:
                    c, rest = best(mask | 1 << i | 1 << j)
                    c += dist[odd[i]][odd[j]]
                    if c < res[0]:
                        res = (c, ((i, j),) + rest)
            memo[mask] = res
            return res

        cost, pairs = best(0)
        repeated = []
        extra_edges = []
        for i, j in pairs:
            path = self.path_from(par[odd[i]], odd[j])
            repeated.append(path)
            extra_edges.extend(zip(path, path[1:]))
        return {"odd": odd, "extra": cost, "pairs": [(odd[i], odd[j]) for i, j in pairs],
                "repeated_paths": repeated, "extra_edges": extra_edges,
                "total_segments": len(self.edges) + cost}

    def euler_tour(self, extra_edges, start="Churchgate"):
        """Hierholzer's algorithm on the multigraph (all segments plus the repeated ones)."""
        multi = defaultdict(list)
        eid = 0
        for a, b in self.edges + list(extra_edges):
            multi[a].append((b, eid))
            multi[b].append((a, eid))
            eid += 1
        used = set()
        ptr = defaultdict(int)
        stack, tour = [start], []
        while stack:
            u = stack[-1]
            while ptr[u] < len(multi[u]) and multi[u][ptr[u]][1] in used:
                ptr[u] += 1
            if ptr[u] == len(multi[u]):
                tour.append(stack.pop())
            else:
                w, e = multi[u][ptr[u]]
                used.add(e)
                stack.append(w)
        return tour[::-1]

    def euler_status(self):
        odd = self.odd_stations()
        if len(odd) == 0:
            return "circuit"
        if len(odd) == 2:
            return "path"
        return "none"

    def hamilton_status(self):
        pendants = sorted(v for v in self.stations if self.degree(v) == 1)
        return {"pendants": pendants, "path_possible": len(pendants) <= 2, "cycle_possible": len(pendants) == 0}

    # ---------- counting and planarity ----------
    def counts(self):
        v, e = len(self.stations), len(self.edges)
        c = len(self.components())
        return {"V": v, "E": e, "C": c, "cycle_rank": e - v + c, "faces": e - v + 1 + c,
                "degree_sum": sum(self.degree(x) for x in self.stations)}

    def kernel(self):
        """Remove dead ends, then smooth out degree-2 stations: the planar skeleton of the network."""
        adj = {v: set(n) for v, n in self.adj.items()}
        changed = True
        while changed:
            changed = False
            for v in list(adj):
                if len(adj[v]) <= 1:
                    for w in adj[v]:
                        adj[w].discard(v)
                    del adj[v]
                    changed = True
            for v in list(adj):
                if v in adj and len(adj[v]) == 2:
                    a, b = sorted(adj[v])
                    adj[a].discard(v)
                    adj[b].discard(v)
                    del adj[v]
                    adj[a].add(b)
                    adj[b].add(a)
                    changed = True
        edges = sorted({tuple(sorted((a, b))) for a in adj for b in adj[a]})
        return sorted(adj), edges

    def skeleton(self):
        """Topological skeleton: drop dead ends (2-core), keep junctions (degree >= 3) and
        replace each chain of through-stations by one link. Parallel links are kept."""
        adj = {v: set(n) for v, n in self.adj.items()}
        stack = [v for v in adj if len(adj[v]) <= 1]
        while stack:
            v = stack.pop()
            if v not in adj:
                continue
            for w in adj[v]:
                adj[w].discard(v)
                if len(adj[w]) <= 1:
                    stack.append(w)
            del adj[v]
        junctions = sorted(v for v in adj if len(adj[v]) >= 3)
        links, seen = [], set()
        for a in junctions:
            for first in sorted(adj[a]):
                if (a, first) in seen:
                    continue
                prev, cur, length = a, first, 1
                while cur not in junctions:
                    nxt = next(x for x in adj[cur] if x != prev)
                    prev, cur, length = cur, nxt, length + 1
                seen.add((a, first))
                seen.add((cur, prev))
                links.append([a, cur, length])
        return junctions, links

    def planarity(self):
        nodes, edges = self.kernel()
        found = kuratowski(nodes, edges) if len(edges) <= 20 else "unknown"
        sk_nodes, sk_links = self.skeleton()
        return {"kernel_nodes": nodes, "kernel_edges": edges, "subdivision": found,
                "skeleton_nodes": sk_nodes, "skeleton_links": sk_links,
                "planar": found is None if found != "unknown" else None}

    # ---------- what-if: closures ----------
    def disruption(self, closed):
        closed = frozenset(c for c in closed if c in self.adj)
        comps = self.components(closed)
        main = set(comps[0]) if comps else set()
        stranded = sorted(v for v in self.stations if v not in closed and v not in main)
        return {"closed": sorted(closed), "pieces": [{"size": len(c), "sample": c[:4]} for c in comps],
                "stranded": stranded, "connected": len(comps) <= 1}

    # ---------- relations on services (Module 3) ----------
    def service_relation(self):
        ids = list(self.services)
        n = len(ids)
        shared = {}
        M = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                common = sorted(set(self.services[ids[i]]["seq"]) & set(self.services[ids[j]]["seq"]))
                if common:
                    M[i][j] = M[j][i] = 1
                    shared[f"{ids[i]}-{ids[j]}"] = common
        # Warshall closure and the smallest power R^k that connects two services
        W = [r[:] for r in M]
        for k in range(n):
            for i in range(n):
                for j in range(n):
                    W[i][j] = W[i][j] or (W[i][k] and W[k][j])
        changes = [[None] * n for _ in range(n)]
        P = [r[:] for r in M]
        power = 1
        for i in range(n):
            changes[i][i] = 0
        while True:
            for i in range(n):
                for j in range(n):
                    if P[i][j] and changes[i][j] is None:
                        changes[i][j] = power
            if all(c is not None for r in changes for c in r) or power > n:
                break
            Q = [[0] * n for _ in range(n)]
            for i in range(n):
                for j in range(n):
                    Q[i][j] = 1 if any(P[i][k] and M[k][j] for k in range(n)) else 0
            P, power = Q, power + 1
        return {"ids": ids, "M": M, "closure": W, "interchanges": changes, "shared": shared}


def kuratowski(nodes, edges):
    """Return 'K5' or 'K3,3' if the graph contains a subdivision of it, otherwise None."""
    m = len(edges)
    for mask in range((1 << m) - 1, 0, -1):
        adj = defaultdict(list)
        for k in range(m):
            if mask >> k & 1:
                a, b = edges[k]
                adj[a].append(b)
                adj[b].append(a)
        vs = list(adj)
        if len(vs) < 5 or any(len(adj[x]) < 2 for x in vs):
            continue
        branch = [x for x in vs if len(adj[x]) >= 3]
        if len(branch) < 5 or any(len(adj[x]) > 4 for x in branch):
            continue
        bset, nb, ok = set(branch), {}, True
        for b in branch:
            nb[b] = set()
            for start in adj[b]:
                prev, cur = b, start
                while cur not in bset:
                    nxt = [w for w in adj[cur] if w != prev]
                    if not nxt:
                        ok = False
                        break
                    prev, cur = cur, nxt[0]
                if not ok or cur == b or cur in nb[b]:
                    ok = False
                    break
                nb[b].add(cur)
            if not ok:
                break
        if not ok or any(x not in bset and len(adj[x]) != 2 for x in vs):
            continue
        if len(branch) == 5 and all(len(nb[b]) == 4 for b in branch):
            return "K5"
        if len(branch) == 6 and all(len(nb[b]) == 3 for b in branch):
            side = {branch[0]: 0}
            q = deque([branch[0]])
            bip = True
            while q and bip:
                u = q.popleft()
                for w in nb[u]:
                    if w not in side:
                        side[w] = 1 - side[u]
                        q.append(w)
                    elif side[w] == side[u]:
                        bip = False
            if bip and len(side) == 6:
                return "K3,3"
    return None


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
