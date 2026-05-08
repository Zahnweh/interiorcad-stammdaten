import os

VERSION     = "1.1.3"
GITHUB_REPO = "Zahnweh/interiorcad-stammdaten"

BOARD_THICKNESSES = [5, 8, 13, 16, 19, 22, 25, 28, 32, 38]
EDGE_WIDTHS       = [16, 19, 23, 25, 26, 28, 29, 33, 43]
EDGE_THICKNESSES  = [1.0, 2.0, 3.0]
STAMMDATEN_REL    = os.path.join("interiorcad", "Stammdaten")

BOARD_COLUMNS = [
    ("item_no",     "ID",                   120),
    ("description", "Bezeichnung",          220),
    ("supplier",    "Lieferant",            140),
    ("supplier_id", "Bestellnummer",        130),
    ("price",       "Preis",                 60),
    ("unit",        "Einheit",               60),
    ("amount",      "Menge",                 60),
    ("waste",       "Verschnitt",            80),
    ("markup",      "Aufschlag",             80),
    ("length",      "Länge",                 60),
    ("width",       "Breite",                60),
    ("thickness",   "Stärke",                60),
    ("group",       "Gruppe",               110),
    ("texture",     "Textur",                80),
    ("def_thick",   "Std. Stärke",           80),
    ("grain",       "Maserrichtung",        100),
    ("btype",       "Typ",                  120),
    ("cov1_thick",  "Besch. 1 (mm)",         90),
    ("cov2_thick",  "Besch. 2 (mm)",         90),
    ("cov1_tex",    "Textur Besch. 1",       110),
    ("cov2_tex",    "Textur Besch. 2",       110),
]

EDGE_COLUMNS = [
    ("item_no",     "ID",                   140),
    ("description", "Bezeichnung",          260),
    ("supplier",    "Lieferant",            150),
    ("supplier_id", "Bestellnummer",        140),
    ("price",       "Preis",                 60),
    ("unit",        "Einheit",               60),
    ("amount",      "Menge",                 60),
    ("waste",       "Verschnitt",            80),
    ("markup",      "Aufschlag",             80),
    ("length",      "Länge",                 60),
    ("width",       "Breite",                60),
    ("thickness",   "Dicke",                 60),
    ("group",       "Gruppe",               100),
    ("texture",     "Textur",               100),
    ("def_thick",   "Std. Dicke",            80),
    ("grain",       "Maserrichtung",        100),
    ("btype",       "Typ",                  100),
    ("cov1_thick",  "Besch. 1 (mm)",         90),
    ("cov2_thick",  "Besch. 2 (mm)",         90),
    ("cov1_tex",    "Textur Besch. 1",       110),
    ("cov2_tex",    "Textur Besch. 2",       110),
]

GRAIN_OPTIONS = [("Längs", "length"), ("Quer", "width"), ("Keine", "none")]
TYPE_OPTIONS  = [
    ("Fertig beschichtet", "melamine"),
    ("Fertig furniert",    "veneer"),
    ("Leimholz",           "gw"),
    ("3-Schichtplatte",    "3l"),
    ("Massiv",             "solid"),
    ("Glas",               "glass"),
    ("Stahl",              "steel"),
    ("Standard",           "custom"),
]
