"""Mumbai suburban railway data: stations in running order for each service.

Source: Wikipedia pages for the Western, Central, Harbour and Trans-Harbour lines
(Mumbai Suburban Railway). Metro, monorail and mainline-only stations are not included.
A station that appears on several services is one vertex of the graph.
"""

W_SEQ = [
    "Churchgate", "Marine Lines", "Charni Road", "Grant Road", "Mumbai Central", "Mahalaxmi", "Lower Parel",
    "Prabhadevi", "Dadar", "Matunga Road", "Mahim Junction", "Bandra", "Khar Road", "Santacruz", "Vile Parle",
    "Andheri", "Jogeshwari", "Ram Mandir", "Goregaon", "Malad", "Kandivli", "Borivali", "Dahisar", "Mira Road",
    "Bhayandar", "Naigaon", "Vasai Road", "Nallasopara", "Virar", "Vaitarna", "Saphale", "Kelve Road", "Palghar",
    "Umroli", "Boisar", "Vangaon", "Dahanu Road",
]

C_MAIN = [
    "CSMT", "Masjid", "Sandhurst Road", "Byculla", "Chinchpokli", "Currey Road", "Parel", "Dadar", "Matunga",
    "Sion", "Kurla", "Vidyavihar", "Ghatkopar", "Vikhroli", "Kanjur Marg", "Bhandup", "Nahur", "Mulund", "Thane",
    "Kalwa", "Mumbra", "Diva Junction", "Kopar", "Dombivli", "Thakurli", "Kalyan Junction",
]
C_KASARA = ["Shahad", "Ambivli", "Titwala", "Khadavli", "Vasind", "Asangaon", "Atgaon", "Thansit", "Khardi", "Umbermali", "Kasara"]
C_KARJAT = [
    "Vithalwadi", "Ulhasnagar", "Ambarnath", "Chikhloli", "Badlapur", "Vangani", "Shelu", "Neral Junction",
    "Bhivpuri Road", "Karjat", "Palasdhari", "Kelavli", "Dolavli", "Lowjee", "Khopoli",
]

H_PANVEL = [
    "CSMT", "Masjid", "Sandhurst Road", "Dockyard Road", "Reay Road", "Cotton Green", "Sewri", "Wadala Road",
    "Guru Tegh Bahadur Nagar", "Chunabhatti", "Kurla", "Tilak Nagar", "Chembur", "Govandi", "Mankhurd", "Vashi",
    "Sanpada", "Juinagar", "Nerul", "Seawoods-Darave", "CBD Belapur", "Kharghar", "Mansarovar", "Khandeshwar", "Panvel",
]
H_GOREGAON = [
    "CSMT", "Masjid", "Sandhurst Road", "Dockyard Road", "Reay Road", "Cotton Green", "Sewri", "Wadala Road",
    "King's Circle", "Mahim Junction", "Bandra", "Khar Road", "Santacruz", "Vile Parle", "Andheri", "Jogeshwari",
    "Ram Mandir", "Goregaon",
]

T_COMMON = ["Thane", "Digha Gaon", "Airoli", "Rabale", "Ghansoli", "Koparkhairane", "Turbhe"]
T_VASHI = T_COMMON + ["Sanpada", "Vashi"]
T_PANVEL = T_COMMON + ["Juinagar", "Nerul", "Seawoods-Darave", "CBD Belapur", "Kharghar", "Mansarovar", "Khandeshwar", "Panvel"]

# Four coloured lines, split into the through-services a passenger actually boards.
# Changing from one service to another is an interchange, even when both have the same colour
# (for example Kasara <-> Karjat at Kalyan).
GROUPS = {
    "W": {"name": "Western", "color": "#d1402f"},
    "C": {"name": "Central", "color": "#1b6fb5"},
    "H": {"name": "Harbour", "color": "#0e8f73"},
    "T": {"name": "Trans-Harbour", "color": "#7a4cc0"},
}
SERVICES = {
    "W": {"name": "Western: Churchgate to Dahanu Road", "group": "W", "seq": W_SEQ},
    "CK": {"name": "Central: CSMT to Kasara", "group": "C", "seq": C_MAIN + C_KASARA},
    "CR": {"name": "Central: CSMT to Khopoli", "group": "C", "seq": C_MAIN + C_KARJAT},
    "HP": {"name": "Harbour: CSMT to Panvel", "group": "H", "seq": H_PANVEL},
    "HG": {"name": "Harbour: CSMT to Goregaon", "group": "H", "seq": H_GOREGAON},
    "TV": {"name": "Trans-Harbour: Thane to Vashi", "group": "T", "seq": T_VASHI},
    "TP": {"name": "Trans-Harbour: Thane to Panvel", "group": "T", "seq": T_PANVEL},
}

FULL_NAMES = {"CSMT": "Chhatrapati Shivaji Maharaj Terminus"}

# Schematic map anchors (x right, y down, north is up). Stations between two anchors on a service
# are spread evenly along the straight segment. This is a diagram, not a geographic map.
ANCHORS = {
    "Churchgate": (150, 1390), "Dadar": (330, 1010), "Mahim Junction": (292, 925), "Andheri": (245, 700),
    "Borivali": (215, 470), "Virar": (165, 235), "Dahanu Road": (105, 40),
    "CSMT": (480, 1390), "Kurla": (445, 800), "Ghatkopar": (505, 700), "Thane": (600, 480),
    "Kalyan Junction": (770, 300), "Kasara": (1010, 70), "Karjat": (975, 520), "Khopoli": (1070, 650),
    "Wadala Road": (505, 1115), "Mankhurd": (575, 760), "Vashi": (705, 800), "Juinagar": (785, 950),
    "Panvel": (930, 1250), "Turbhe": (835, 745),
}
