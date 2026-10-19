import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from network import Network, layout  # noqa: E402

N = Network()


class Facts(unittest.TestCase):
    def test_sizes(self):
        c = N.counts()
        self.assertEqual(c["V"], len(N.stations))
        self.assertEqual(c["degree_sum"], 2 * c["E"])          # handshake lemma
        self.assertEqual(c["C"], 1)                            # whole network is connected
        print("V, E:", c["V"], c["E"])

    def test_layout_places_everyone(self):
        self.assertEqual(set(layout(N)), set(N.stations))


class Routing(unittest.TestCase):
    def test_churchgate_to_csmt(self):
        r = N.route("Churchgate", "CSMT", "stops")
        self.assertEqual(r["stops"], 15)           # 8 stops to Dadar + 7 stops back down the Central line
        self.assertEqual(r["interchanges"], 1)
        self.assertIn("Dadar", r["path"])

    def test_one_change_to_thane(self):
        self.assertEqual(N.route("Churchgate", "Thane", "changes")["interchanges"], 1)

    def test_no_change_needed(self):
        r = N.route("Borivali", "Churchgate", "changes")
        self.assertEqual((r["interchanges"], r["legs"][0]["service"]), (0, "W"))

    def test_kasara_to_khopoli_needs_change_at_kalyan(self):
        r = N.route("Kasara", "Khopoli", "changes")
        self.assertEqual(r["interchanges"], 1)
        self.assertEqual(r["legs"][0]["stations"][-1], "Kalyan Junction")

    def test_route_is_never_shorter_than_bfs(self):
        dist, _ = N.bfs("Virar")
        for dst in ["Panvel", "Kasara", "Vashi", "Khopoli"]:
            self.assertGreaterEqual(N.route("Virar", dst, "stops")["stops"], dist[dst])

    def test_closed_station_reroute_or_none(self):
        self.assertIsNone(N.route("Churchgate", "Kasara", "stops", closed=frozenset(["Thane"])))
        self.assertIsNone(N.route("Churchgate", "CSMT", "stops", closed=frozenset(["Dadar"])))
        r = N.route("Dadar", "CSMT", "stops", closed=frozenset(["Parel"]))
        self.assertIsNotNone(r)                    # goes round by the Harbour branch instead
        self.assertNotIn("Parel", r["path"])
        self.assertGreater(r["stops"], N.route("Dadar", "CSMT", "stops")["stops"])

    def test_same_station(self):
        r = N.route("Dadar", "Dadar")
        self.assertEqual((r["stops"], r["interchanges"]), (0, 0))


class Connectivity(unittest.TestCase):
    def test_critical_stations(self):
        crit = dict(N.critical_stations())
        self.assertGreater(crit["Thane"], 30)
        self.assertEqual(crit["Dadar"], 8)         # Churchgate..Prabhadevi hang off Dadar
        self.assertNotIn("Parel", crit)            # Parel lies on a loop
        self.assertNotIn("Churchgate", crit)       # a dead end is never a cut vertex

    def test_critical_matches_networkx(self):
        try:
            import networkx as nx
        except ImportError:
            self.skipTest("networkx not installed")
        self.assertEqual(sorted(nx.articulation_points(nx.Graph(N.edges))), sorted(v for v, _ in N.critical_stations()))

    def test_close_thane(self):
        d = N.disruption(["Thane"])
        self.assertFalse(d["connected"])
        self.assertIn("Kasara", d["stranded"])
        self.assertIn("Khopoli", d["stranded"])


class EulerHamilton(unittest.TestCase):
    def test_no_euler_path(self):
        self.assertEqual(len(N.odd_stations()) % 2, 0)   # handshake lemma
        self.assertEqual(N.euler_status(), "none")

    def test_hamilton_pendants(self):
        h = N.hamilton_status()
        self.assertGreater(len(h["pendants"]), 2)
        self.assertFalse(h["path_possible"])

    def test_euler_theorem_on_small_graphs(self):
        square = {"A": {"name": "loop", "group": "W", "seq": ["a", "b", "c", "d", "a"]}}
        self.assertEqual(Network(square).euler_status(), "circuit")      # every degree is 2
        line = {"A": {"name": "line", "group": "W", "seq": ["a", "b", "c"]}}
        self.assertEqual(Network(line).euler_status(), "path")           # exactly two odd ends


class Relations(unittest.TestCase):
    def test_service_relation(self):
        r = N.service_relation()
        ids = r["ids"]
        self.assertEqual(r["M"][ids.index("CK")][ids.index("CR")], 1)    # share the Central trunk
        self.assertEqual(r["M"][ids.index("W")][ids.index("HP")], 0)     # no common station
        self.assertTrue(all(all(row) for row in r["closure"]))           # Warshall: everything reachable


if __name__ == "__main__":
    unittest.main(verbosity=2)
