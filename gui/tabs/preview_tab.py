import tkinter as tk
from tkinter import ttk

from gui.theme import PAD_S


class PreviewTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=(PAD_S, PAD_S))
        self._build()

    def _build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        tab_b = ttk.Frame(nb)
        nb.add(tab_b, text="Platten")
        b_cols   = ("id", "desc", "thick", "supplier", "supplier_id", "btype", "grain")
        b_heads  = ("ID", "Beschreibung", "Stärke", "Lieferant", "Bestellnr.", "Typ", "Maserrichtung")
        b_widths = (140, 240, 60, 140, 120, 100, 100)
        self._board_tree = self._make_tree(tab_b, b_cols, b_heads, b_widths)

        tab_e = ttk.Frame(nb)
        nb.add(tab_e, text="Kanten")
        e_cols   = ("id", "desc", "width", "thick", "supplier", "texture")
        e_heads  = ("ID", "Beschreibung", "Breite", "Dicke", "Lieferant", "Textur")
        e_widths = (160, 280, 60, 60, 140, 100)
        self._edge_tree = self._make_tree(tab_e, e_cols, e_heads, e_widths)

    def _make_tree(self, parent, cols, heads, widths):
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=6)
        for col, head, w in zip(cols, heads, widths):
            tree.heading(col, text=head)
            tree.column(col, width=w, minwidth=40)
        vsb = ttk.Scrollbar(parent, orient="vertical",   command=tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        tree.pack(fill="both", expand=True)
        return tree

    def update_boards(self, rows):
        self._board_tree.delete(*self._board_tree.get_children())
        for values in rows:
            self._board_tree.insert("", "end", values=values)

    def update_edges(self, rows):
        self._edge_tree.delete(*self._edge_tree.get_children())
        for values in rows:
            self._edge_tree.insert("", "end", values=values)
