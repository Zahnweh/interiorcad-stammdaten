import tkinter as tk
from tkinter import ttk, messagebox

from core.constants import EDGE_WIDTHS, EDGE_THICKNESSES
from core.prefs import save_custom
from gui.theme import FONT_BODY, FONT_BODY_B, FONT_SM, PAD_XS, PAD_S, PAD_M, PAD_L


class EdgesTab(ttk.Frame):
    def __init__(self, parent, custom, on_change):
        super().__init__(parent, padding=(PAD_S, PAD_S))
        self._custom    = custom
        self._on_change = on_change
        self.edge_vars       = {}
        self.edge_entries    = {}
        self.edge_root_var   = tk.StringVar()
        self.kante_vars      = {}
        self._custom_edge_vars = {}
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)
        self._build()

    # ── Public interface ──────────────────────────────────────────────────────

    def get_all_kante_vars(self):
        merged = dict(self.kante_vars)
        merged.update(self._custom_edge_vars)
        return merged

    def reset(self):
        for key, var in self.edge_vars.items():
            if key == "edge_supplier":
                var.set("Holz Hahn GmbH - Krefeld")
            elif key == "edge_waste":
                var.set("10")
            else:
                var.set("")
        self.edge_root_var.set("")
        self._reset_edges()

    def _reset_edges(self):
        for v in self.kante_vars.values():
            v.set(False)
        for v in self._custom_edge_vars.values():
            v.set(False)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        left  = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_S))
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")

        self._build_params(left)
        self._build_grid(right)

    def _build_params(self, parent):
        ef = ttk.LabelFrame(parent, text="Kantenparameter", padding=PAD_M)
        ef.pack(fill="both", expand=True)
        ef.columnconfigure(1, weight=1)

        ttk.Label(ef, text="Wurzelname", font=FONT_SM).grid(
            row=0, column=0, sticky="w", padx=(0, PAD_S), pady=2)
        root_entry = ttk.Entry(ef, textvariable=self.edge_root_var,
                               width=32, font=FONT_BODY)
        root_entry.grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Button(ef, text="⚡", width=3,
                   command=self._fill_from_root).grid(
            row=0, column=2, padx=(PAD_S, 0), pady=2)
        self.edge_root_var.trace_add("write", lambda *a: self._on_change())

        edge_fields = [
            ("ID (Stamm)",      "edge_item_no",  "",                         True),
            ("Textur (Kante)", "edge_texture",  "",                         True),
            ("Lieferant",      "edge_supplier", "Holz Hahn GmbH - Krefeld", False),
            ("Verschnitt (%)", "edge_waste",    "10",                       False),
        ]
        for i, (label, key, default, locked) in enumerate(edge_fields):
            ttk.Label(ef, text=label, font=FONT_SM).grid(
                row=i + 1, column=0, sticky="w", padx=(0, PAD_S), pady=2)
            var   = tk.StringVar(value=default)
            state = "readonly" if locked else "normal"
            entry = ttk.Entry(ef, textvariable=var, width=32,
                              font=FONT_BODY, state=state)
            entry.grid(row=i + 1, column=1, sticky="ew", pady=2)
            self.edge_vars[key]    = var
            self.edge_entries[key] = entry
            var.trace_add("write", lambda *a: self._on_change())

    def _build_grid(self, parent):
        kf = ttk.LabelFrame(parent, text="Kanten  (Breite × Dicke)", padding=PAD_M)
        kf.pack(fill="x")

        ttk.Label(kf, text="", width=5).grid(row=0, column=0)
        for j, et in enumerate(EDGE_THICKNESSES):
            ts = "{}mm".format(int(et) if et == int(et) else et)
            ttk.Label(kf, text=ts, font=FONT_BODY_B,
                      width=5).grid(row=0, column=j + 1, padx=PAD_XS)

        self.kante_vars = {}
        for i, ew in enumerate(EDGE_WIDTHS):
            ttk.Label(kf, text="{} mm".format(ew),
                      font=FONT_SM).grid(
                row=i + 1, column=0, sticky="w", padx=(0, PAD_S), pady=2)
            for j, et in enumerate(EDGE_THICKNESSES):
                var = tk.BooleanVar(value=False)
                self.kante_vars[(ew, et)] = var
                var.trace_add("write", lambda *a: self._on_change())
                ttk.Checkbutton(kf, variable=var).grid(
                    row=i + 1, column=j + 1, padx=PAD_XS, pady=2)

        edge_btn_row = len(EDGE_WIDTHS) + 1
        ttk.Button(kf, text="Alle auswählen",
                   command=self._select_all_edges).grid(
            row=edge_btn_row, column=0, columnspan=2,
            sticky="w", padx=0, pady=(PAD_S, 2))
        ttk.Button(kf, text="Zurücksetzen",
                   command=self._reset_edges).grid(
            row=edge_btn_row, column=2, columnspan=2,
            sticky="w", padx=0, pady=(PAD_S, 2))

        ttk.Separator(kf, orient="horizontal").grid(
            row=edge_btn_row + 1, column=0, columnspan=4,
            sticky="ew", padx=PAD_XS, pady=(PAD_S, PAD_XS))

        add_row = edge_btn_row + 2
        ttk.Label(kf, text="B:", font=FONT_SM).grid(
            row=add_row, column=0, sticky="e")
        self._custom_edge_w_var = tk.StringVar()
        ttk.Entry(kf, textvariable=self._custom_edge_w_var,
                  width=4, font=FONT_BODY).grid(
            row=add_row, column=1, sticky="w", padx=2)
        ttk.Label(kf, text="D:", font=FONT_SM).grid(
            row=add_row, column=2, sticky="e")
        self._custom_edge_t_var = tk.StringVar()
        ttk.Entry(kf, textvariable=self._custom_edge_t_var,
                  width=4, font=FONT_BODY).grid(
            row=add_row, column=3, sticky="w", padx=2)
        ttk.Button(kf, text="+", width=2,
                   command=self._add_custom_edge).grid(
            row=add_row, column=4, sticky="w", padx=PAD_XS)

        self._custom_edge_frame = ttk.Frame(kf)
        self._custom_edge_frame.grid(
            row=add_row + 1, column=0, columnspan=5, sticky="ew", pady=2)
        self._rebuild_custom_edges()

    # ── Custom edges ──────────────────────────────────────────────────────────

    def _rebuild_custom_edges(self):
        for w in self._custom_edge_frame.winfo_children():
            w.destroy()
        self._custom_edge_vars = {}
        for i, (ew, et) in enumerate(self._custom.get("edges", [])):
            var = tk.BooleanVar(value=False)
            var.trace_add("write", lambda *a: self._on_change())
            self._custom_edge_vars[(ew, et)] = var
            ts    = str(int(et)) if et == int(et) else str(et)
            label = "{}×{} mm".format(ew, ts)
            f = ttk.Frame(self._custom_edge_frame)
            f.grid(row=i // 2, column=i % 2, sticky="w", padx=PAD_XS, pady=1)
            ttk.Checkbutton(f, text=label, variable=var).pack(side="left")
            ttk.Button(f, text="×", width=2,
                       command=lambda e=(ew, et): self._del_custom_edge(e)
                       ).pack(side="left", padx=(2, 0))

    def _add_custom_edge(self):
        try:
            ew = float(self._custom_edge_w_var.get().strip().replace(",", "."))
            et = float(self._custom_edge_t_var.get().strip().replace(",", "."))
            if ew <= 0 or et <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Ungültig",
                "Bitte Breite und Dicke als positive Zahlen eingeben.")
            return
        ew = int(ew) if ew == int(ew) else ew
        et = int(et) if et == int(et) else et
        if (ew, et) in [(w, t) for w in EDGE_WIDTHS for t in EDGE_THICKNESSES]:
            messagebox.showwarning("Bereits vorhanden",
                "{}×{} mm ist bereits in der Liste.".format(ew, et))
            return
        if [ew, et] in self._custom.get("edges", []) or \
                (ew, et) in [tuple(e) for e in self._custom.get("edges", [])]:
            messagebox.showwarning("Bereits vorhanden",
                "{}×{} mm ist bereits in der Liste.".format(ew, et))
            return
        self._custom.setdefault("edges", []).append([ew, et])
        save_custom(self._custom)
        self._custom_edge_w_var.set("")
        self._custom_edge_t_var.set("")
        self._rebuild_custom_edges()

    def _del_custom_edge(self, edge):
        ew, et = edge
        self._custom["edges"] = [
            e for e in self._custom["edges"]
            if not (e[0] == ew and e[1] == et)]
        save_custom(self._custom)
        self._rebuild_custom_edges()

    def _select_all_edges(self):
        for v in self.kante_vars.values():
            v.set(True)

    # ── Fill from root ────────────────────────────────────────────────────────

    def _fill_from_root(self):
        from core.derive import extract_decor_code, extract_structure
        root = self.edge_root_var.get().strip()
        if not root:
            messagebox.showwarning("Wurzelname fehlt",
                "Bitte zuerst einen Kanten-Wurzelnamen eingeben.")
            return
        decor  = extract_decor_code(root)
        struct = extract_structure(root)
        self.edge_vars["edge_texture"].set(decor)
        edge_id = "Ka-{}-{}".format(decor, struct) if struct else "Ka-{}".format(decor)
        self.edge_vars["edge_item_no"].set(edge_id)
