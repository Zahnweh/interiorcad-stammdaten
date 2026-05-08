import tkinter as tk
from tkinter import ttk, messagebox

from core.constants import EDGE_COLUMNS
from core.file_io import parse_edges, write_edges
from gui.theme import FONT_BODY, FONT_SM, PAD_XS, PAD_S, PAD_M, PAD_L


class EdgeEditDialog(tk.Toplevel):
    def __init__(self, parent, row_data, on_save):
        super().__init__(parent)
        self.title("Kante bearbeiten")
        self.resizable(False, False)
        self.grab_set()
        self._data    = dict(row_data)
        self._on_save = on_save
        self._vars    = {}
        self._build()
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("+{}+{}".format(
            (sw - self.winfo_width()) // 2,
            (sh - self.winfo_height()) // 2))

    def _build(self):
        fields = [
            ("ID",             "item_no"),
            ("Bezeichnung",    "description"),
            ("Lieferant",      "supplier"),
            ("Bestellnummer",  "supplier_id"),
            ("Preis",          "price"),
            ("Einheit",        "unit"),
            ("Menge/Einheit",  "amount"),
            ("Verschnitt (%)", "waste"),
            ("Aufschlag",      "markup"),
            ("Breite (mm)",    "width"),
            ("Dicke (mm)",     "thickness"),
            ("Textur",         "texture"),
        ]
        outer = ttk.Frame(self, padding=PAD_L)
        outer.pack(fill="both")
        outer.columnconfigure(1, weight=1)

        for i, (label, key) in enumerate(fields):
            ttk.Label(outer, text=label, font=FONT_SM, width=18,
                      anchor="w").grid(row=i, column=0, sticky="w",
                                       padx=(0, PAD_S), pady=2)
            var = tk.StringVar(value=self._data.get(key, ""))
            self._vars[key] = var
            ttk.Entry(outer, textvariable=var, width=32,
                      font=FONT_BODY).grid(row=i, column=1, sticky="ew", pady=2)

        ttk.Separator(outer, orient="horizontal").grid(
            row=len(fields), column=0, columnspan=2, sticky="ew", pady=(PAD_M, 0))
        bf = ttk.Frame(outer)
        bf.grid(row=len(fields) + 1, column=0, columnspan=2,
                sticky="ew", pady=(PAD_S, 0))
        ttk.Button(bf, text="Abbrechen", command=self.destroy).pack(side="left")
        ttk.Button(bf, text="Übernehmen", command=self._save).pack(side="right")

    def _save(self):
        for key, var in self._vars.items():
            self._data[key] = var.get().strip()
        self._on_save(self._data)
        self.destroy()


class EdgesTable(tk.Toplevel):
    def __init__(self, parent, filepath):
        super().__init__(parent)
        self.title("Kanten verwalten – {}".format(filepath.split("/")[-1]))
        self.filepath = filepath
        self._rows    = parse_edges(filepath)
        self._build()
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(1200, sw - 40), min(600, sh - 80)
        self.geometry("{}x{}+{}+{}".format(w, h, (sw - w) // 2, (sh - h) // 2))
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build(self):
        bar = ttk.Frame(self, padding=(PAD_S, PAD_S - 2))
        bar.pack(fill="x")
        ttk.Button(bar, text="Bearbeiten",
                   command=self._edit_selected).pack(side="left", padx=(0, PAD_XS))
        ttk.Button(bar, text="Duplizieren",
                   command=self._duplicate_selected).pack(side="left", padx=(0, PAD_XS))
        ttk.Button(bar, text="Entfernen",
                   command=self._delete_selected).pack(side="left", padx=(0, PAD_XS))
        ttk.Label(bar, text="Suche:", font=FONT_SM).pack(
            side="left", padx=(PAD_L, PAD_XS))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._apply_filter())
        ttk.Entry(bar, textvariable=self._search_var,
                  width=24, font=FONT_BODY).pack(side="left")
        ttk.Button(bar, text="Speichern",
                   command=self._save).pack(side="right")

        cols = [c[0] for c in EDGE_COLUMNS]
        self._tree = ttk.Treeview(self, columns=cols,
                                  show="headings", selectmode="extended")
        for key, label, width in EDGE_COLUMNS:
            self._tree.heading(key, text=label,
                               command=lambda k=key: self._sort(k))
            self._tree.column(key, width=width, minwidth=40)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._tree.bind("<Double-1>", lambda e: self._edit_selected())
        self._populate()

    def _populate(self, rows=None):
        self._tree.delete(*self._tree.get_children())
        display = self._rows if rows is None else rows
        for r in display:
            vals = [r.get(c[0], "") for c in EDGE_COLUMNS]
            self._tree.insert("", "end", iid=r["item_no"], values=vals)

    def _apply_filter(self):
        q = self._search_var.get().lower()
        if not q:
            self._populate()
            return
        filtered = [r for r in self._rows
                    if any(q in str(v).lower() for v in r.values())]
        self._populate(filtered)

    def _sort(self, key):
        self._rows.sort(key=lambda r: r.get(key, "").lower()
                        if isinstance(r.get(key), str) else r.get(key, ""))
        self._apply_filter()

    def _selected_row(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Keine Auswahl",
                "Bitte zuerst eine Zeile auswählen.", parent=self)
            return None
        iid = sel[0]
        return next((r for r in self._rows if r["item_no"] == iid), None)

    def _selected_rows(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Keine Auswahl",
                "Bitte zuerst eine oder mehrere Zeilen auswählen.", parent=self)
            return []
        return [r for r in self._rows if r["item_no"] in sel]

    def _edit_selected(self):
        row = self._selected_row()
        if not row:
            return
        def on_save(updated):
            idx = next(i for i, r in enumerate(self._rows)
                       if r["item_no"] == row["item_no"])
            self._rows[idx] = updated
            self._apply_filter()
        EdgeEditDialog(self, row, on_save)

    def _duplicate_selected(self):
        row = self._selected_row()
        if not row:
            return
        copy = dict(row)
        copy["item_no"] = row["item_no"] + "_Kopie"
        def on_save(updated):
            self._rows.append(updated)
            self._apply_filter()
        EdgeEditDialog(self, copy, on_save)

    def _delete_selected(self):
        rows = self._selected_rows()
        if not rows:
            return
        msg = ('Eintrag "{}" wirklich löschen?'.format(rows[0]["item_no"])
               if len(rows) == 1
               else '{} Einträge wirklich löschen?'.format(len(rows)))
        if not messagebox.askyesno("Löschen bestätigen", msg, parent=self):
            return
        ids = {r["item_no"] for r in rows}
        self._rows = [r for r in self._rows if r["item_no"] not in ids]
        self._apply_filter()

    def _save(self):
        if not messagebox.askyesno(
                "Speichern bestätigen",
                "Alle Änderungen in Edges.txt schreiben?",
                parent=self):
            return
        try:
            write_edges(self.filepath, self._rows)
            messagebox.showinfo("Gespeichert",
                "Edges.txt wurde erfolgreich gespeichert.", parent=self)
        except Exception as e:
            messagebox.showerror("Fehler", str(e), parent=self)
