import tkinter as tk
from tkinter import ttk, messagebox

from core.constants import BOARD_THICKNESSES, GRAIN_OPTIONS, TYPE_OPTIONS
from core.prefs import save_custom
from gui.theme import FONT_BODY, FONT_BODY_B, FONT_SM, PAD_XS, PAD_S, PAD_M, PAD_L

COATING_KEYS  = {"cov1_thick", "cov2_thick", "cov1_tex", "cov2_tex"}
READONLY_KEYS = {"thickness"} | COATING_KEYS


class BoardsTab(ttk.Frame):
    def __init__(self, parent, custom, on_change):
        super().__init__(parent, padding=(PAD_S, PAD_S))
        self._custom    = custom
        self._on_change = on_change
        self.board_vars    = {}
        self.board_entries = {}
        self.thick_vars    = {}
        self._custom_thick_vars  = {}
        self._coating_labels     = {}
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._build()

    # ── Public interface ──────────────────────────────────────────────────────

    def get_all_thick_vars(self):
        merged = dict(self.thick_vars)
        merged.update(self._custom_thick_vars)
        return merged

    def reset(self):
        defaults = {
            "supplier":   "Holz Hahn GmbH - Krefeld",
            "price":      "0",
            "unit":       "m2",
            "amount":     "1",
            "waste":      "25",
            "markup":     "0",
            "group":      "",
            "grain":      "length",
            "btype":      "melamine",
            "cov1_thick": "1",
            "cov2_thick": "1",
            "texture":    "Spanplatte",
        }
        for key, var in self.board_vars.items():
            var.set(defaults.get(key, ""))
        _grain_display = {"length": "Längs", "width": "Quer", "none": "Keine"}
        _btype_display = {o[1]: o[0] for o in TYPE_OPTIONS}
        self.board_entries["grain"].set(_grain_display.get(defaults["grain"], ""))
        self.board_entries["btype"].set(_btype_display.get(defaults["btype"], ""))
        self._update_coating_fields("melamine")
        self._reset_thick()

    def _reset_thick(self):
        for v in self.thick_vars.values():
            v.set(False)
        for v in self._custom_thick_vars.values():
            v.set(False)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_S))
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")

        self._build_params(left)
        self._build_thicknesses(right)

    def _build_params(self, parent):
        pf = ttk.LabelFrame(parent, text="Plattenparameter", padding=PAD_M)
        pf.pack(fill="both", expand=True)
        pf.columnconfigure(1, weight=1)

        board_fields = [
            ("ID (Stamm)",             "item_no",     "",                         True,  None),
            ("Beschreibung (Stamm)",   "description", "",                         True,  None),
            ("Lieferant",              "supplier",    "Holz Hahn GmbH - Krefeld", False, None),
            ("Bestellnr. (Stamm)",     "supplier_id", "",                         True,  None),
            ("Gruppe",                 "group",       "",                         True,  None),
            ("Preis",                  "price",       "0",                        False, None),
            ("Einheit",                "unit",        "m2",                       False, None),
            ("Menge/Einheit",          "amount",      "1",                        False, None),
            ("Verschnitt (%)",         "waste",       "25",                       False, None),
            ("Aufschlag",              "markup",      "0",                        False, None),
            ("Maserrichtung",          "grain",       "length",                   False,
                GRAIN_OPTIONS),
            ("Materialtyp",            "btype",       "melamine",                 False,
                TYPE_OPTIONS),
            ("Beschichtung 1 (mm)",    "cov1_thick",  "1",                        True,  None),
            ("Beschichtung 2 (mm)",    "cov2_thick",  "1",                        True,  None),
            ("Textur (Platte)",        "texture",     "Spanplatte",               False, None),
            ("Textur Beschichtung 1",  "cov1_tex",    "",                         True,  None),
            ("Textur Beschichtung 2",  "cov2_tex",    "",                         True,  None),
        ]

        for i, (label, key, default, locked, options) in enumerate(board_fields):
            if options:
                lbl = ttk.Label(pf, text=label, font=FONT_SM)
                lbl.grid(row=i, column=0, sticky="w", padx=(0, PAD_S), pady=2)
                internal_var  = tk.StringVar(value=default)
                display_var   = tk.StringVar()
                self.board_vars[key] = internal_var
                display_vals  = [o[0] for o in options]
                internal_vals = [o[1] for o in options]
                combo = ttk.Combobox(pf, textvariable=display_var,
                                     values=display_vals,
                                     state="readonly", width=30, font=FONT_BODY)
                try:
                    idx = internal_vals.index(default)
                except ValueError:
                    idx = 0
                combo.set(display_vals[idx])
                internal_var.set(internal_vals[idx])
                combo.grid(row=i, column=1, sticky="ew", pady=2)
                self.board_entries[key] = combo

                def make_cb(iv, ivals, dvals, cb):
                    def cb_select(e, iv=iv, ivals=ivals, dvals=dvals, cb=cb):
                        try:
                            iv.set(ivals[dvals.index(cb.get())])
                        except ValueError:
                            pass
                    return cb_select

                combo.bind("<<ComboboxSelected>>",
                           make_cb(internal_var, internal_vals, display_vals, combo))
                if key == "btype":
                    def on_btype(e, cb=combo, ivals=internal_vals, dvals=display_vals):
                        try:
                            val = ivals[dvals.index(cb.get())]
                        except ValueError:
                            val = ""
                        self._update_coating_fields(val)
                    combo.bind("<<ComboboxSelected>>", on_btype, add="+")
                internal_var.trace_add("write", lambda *a: self._on_change())
            else:
                is_coating = key in COATING_KEYS
                lbl = ttk.Label(pf, text=label, font=FONT_SM,
                                foreground="gray" if is_coating else "")
                lbl.grid(row=i, column=0, sticky="w", padx=(0, PAD_S), pady=2)
                if is_coating:
                    self._coating_labels[key] = lbl
                var   = tk.StringVar()
                state = "readonly" if key in READONLY_KEYS else "normal"
                entry = ttk.Entry(pf, textvariable=var, width=32,
                                  font=FONT_BODY, state=state)
                entry.grid(row=i, column=1, sticky="ew", pady=2)
                self.board_vars[key]    = var
                self.board_entries[key] = entry
                var.set(default)
                var.trace_add("write", lambda *a: self._on_change())

    def _build_thicknesses(self, parent):
        tf = ttk.LabelFrame(parent, text="Plattenstärken", padding=PAD_M)
        tf.pack(fill="x")

        for idx, t in enumerate(BOARD_THICKNESSES):
            var = tk.BooleanVar(value=False)
            self.thick_vars[t] = var
            var.trace_add("write", lambda *a: self._on_change())
            ttk.Checkbutton(tf, text="{} mm".format(t),
                            variable=var).grid(
                row=idx // 2, column=idx % 2, sticky="w", padx=PAD_S, pady=2)

        btn_row = len(BOARD_THICKNESSES) // 2 + 1
        ttk.Button(tf, text="Alle auswählen",
                   command=self._select_all_thick).grid(
            row=btn_row, column=0, sticky="w", padx=PAD_S, pady=(PAD_S, 2))
        ttk.Button(tf, text="Zurücksetzen",
                   command=self._reset_thick).grid(
            row=btn_row, column=1, sticky="w", padx=PAD_S, pady=(PAD_S, 2))

        ttk.Separator(tf, orient="horizontal").grid(
            row=btn_row + 1, column=0, columnspan=2,
            sticky="ew", padx=PAD_XS, pady=(PAD_S, PAD_XS))

        add_row = btn_row + 2
        self._custom_thick_var = tk.StringVar()
        ttk.Entry(tf, textvariable=self._custom_thick_var,
                  width=6, font=FONT_BODY).grid(
            row=add_row, column=0, sticky="w", padx=PAD_S, pady=2)
        ttk.Label(tf, text="mm", font=FONT_SM).grid(
            row=add_row, column=0, sticky="e", padx=(0, PAD_XS))
        ttk.Button(tf, text="+", width=2,
                   command=self._add_custom_thick).grid(
            row=add_row, column=1, sticky="w", padx=PAD_XS, pady=2)

        self._custom_thick_frame = ttk.Frame(tf)
        self._custom_thick_frame.grid(
            row=add_row + 1, column=0, columnspan=2,
            sticky="ew", padx=PAD_XS, pady=2)
        self._rebuild_custom_thick()

    # ── Custom thicknesses ────────────────────────────────────────────────────

    def _rebuild_custom_thick(self):
        for w in self._custom_thick_frame.winfo_children():
            w.destroy()
        self._custom_thick_vars = {}
        for i, t in enumerate(self._custom.get("thicknesses", [])):
            var = tk.BooleanVar(value=False)
            var.trace_add("write", lambda *a: self._on_change())
            self._custom_thick_vars[t] = var
            f = ttk.Frame(self._custom_thick_frame)
            f.grid(row=i // 2, column=i % 2, sticky="w", padx=PAD_XS, pady=1)
            ttk.Checkbutton(f, text="{} mm".format(t),
                            variable=var).pack(side="left")
            ttk.Button(f, text="×", width=2,
                       command=lambda t=t: self._del_custom_thick(t)
                       ).pack(side="left", padx=(2, 0))

    def _add_custom_thick(self):
        val = self._custom_thick_var.get().strip()
        try:
            t = float(val)
            if t <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Ungültig",
                "Bitte eine positive Zahl eingeben.")
            return
        t = int(t) if t == int(t) else t
        if t in BOARD_THICKNESSES or t in self._custom.get("thicknesses", []):
            messagebox.showwarning("Bereits vorhanden",
                "{} mm ist bereits in der Liste.".format(t))
            return
        self._custom.setdefault("thicknesses", []).append(t)
        save_custom(self._custom)
        self._custom_thick_var.set("")
        self._rebuild_custom_thick()

    def _del_custom_thick(self, t):
        self._custom["thicknesses"].remove(t)
        save_custom(self._custom)
        self._rebuild_custom_thick()

    def _select_all_thick(self):
        for v in self.thick_vars.values():
            v.set(True)

    # ── Coating fields ────────────────────────────────────────────────────────

    def _update_coating_fields(self, btype_val):
        editable = (btype_val == "melamine")
        for key in ["cov1_thick", "cov2_thick", "cov1_tex", "cov2_tex"]:
            entry = self.board_entries.get(key)
            if entry:
                entry.config(state="normal" if editable else "readonly")
            lbl = self._coating_labels.get(key)
            if lbl:
                lbl.config(foreground="" if editable else "gray")
