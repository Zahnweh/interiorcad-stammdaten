import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading, os, re

from core.constants import VERSION, STAMMDATEN_REL
from core.prefs import load_custom, save_custom
from core.ago_finder import find_agos
from core.derive import derive_all, extract_decor_code, extract_structure
from core.file_io import (load_existing_ids, append_lines,
                           build_board_line, build_edge_line)
from core.updater import _check_for_updates
from gui.theme import (IS_MAC, FONT_BODY, FONT_BODY_B, FONT_SM,
                        FG_GRAY, PAD_XS, PAD_S, PAD_M, PAD_L)
from gui.tabs.boards_tab import BoardsTab
from gui.tabs.edges_tab import EdgesTab
from gui.tabs.preview_tab import PreviewTab
from gui.dialogs.boards_table import BoardsTable
from gui.dialogs.edges_table import EdgesTable


class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title("interiorcad Stammdaten Tool")
        self.resizable(True, True)

        self._agos       = []
        self.boards_path = tk.StringVar()
        self.edges_path  = tk.StringVar()
        self.ago_path_var = tk.StringVar()
        self._custom     = load_custom()
        self._last_ago   = self._custom.get("last_ago", "")

        self._build_ui()

        threading.Thread(target=self._search_agos, daemon=True).start()
        threading.Thread(target=lambda: _check_for_updates(self), daemon=True).start()

        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = min(1100, sw - 40)
        h = min(int(sh * 0.9), sh - 80)
        self.geometry("{}x{}+{}+{}".format(w, h, (sw - w) // 2, (sh - h) // 2))
        self.deiconify()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_menu()
        self._build_bottom_bar()   # side=bottom first
        self._build_header()
        self._build_notebook()

    def _build_menu(self):
        menubar = tk.Menu(self)
        if IS_MAC:
            apple = tk.Menu(menubar, name="apple")
            menubar.add_cascade(label="Apple", menu=apple)
            apple.add_command(label="Über interiorcad Stammdaten…",
                              command=self._show_about)
            apple.add_separator()
            apple.add_command(label="Auf Updates prüfen…",
                              command=self._trigger_update_check)
        else:
            help_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Hilfe", menu=help_menu)
            help_menu.add_command(label="Über interiorcad Stammdaten…",
                                  command=self._show_about)
            help_menu.add_separator()
            help_menu.add_command(label="Auf Updates prüfen…",
                                  command=self._trigger_update_check)
        self.config(menu=menubar)

    def _show_about(self):
        messagebox.showinfo(
            "Über interiorcad Stammdaten",
            "interiorcad Stammdaten Tool\nVersion {}\n\n"
            "Marcel Ostendorf, extragroup GmbH".format(VERSION),
            parent=self)

    def _trigger_update_check(self):
        threading.Thread(
            target=lambda: _check_for_updates(self, silent=False),
            daemon=True).start()

    def _build_header(self):
        ago_frm = ttk.LabelFrame(self, text="Arbeitsgruppenordner (AGO)",
                                 padding=PAD_M)
        ago_frm.pack(fill="x", padx=PAD_L, pady=(PAD_M, PAD_S))
        ago_frm.columnconfigure(1, weight=1)

        ttk.Label(ago_frm, text="AGO", font=FONT_SM).grid(
            row=0, column=0, sticky="w", padx=(0, PAD_S), pady=PAD_XS)

        self.ago_var   = tk.StringVar()
        self.ago_combo = ttk.Combobox(ago_frm, textvariable=self.ago_var,
                                      values=[], state="readonly",
                                      font=FONT_BODY, width=50)
        self.ago_combo.grid(row=0, column=1, sticky="ew", pady=PAD_XS)
        self.ago_combo.set("Suche läuft…")
        self.ago_combo.bind("<<ComboboxSelected>>", self._on_ago_selected)

        ttk.Button(ago_frm, text="…", width=3,
                   command=self._choose_ago_manually).grid(
            row=0, column=2, padx=(PAD_S, 0), pady=PAD_XS)

        ttk.Label(ago_frm, textvariable=self.ago_path_var,
                  font=FONT_SM, foreground=FG_GRAY).grid(
            row=1, column=1, sticky="w", pady=(0, PAD_XS))

        dec_frm = ttk.LabelFrame(self, text="Dekor", padding=PAD_M)
        dec_frm.pack(fill="x", padx=PAD_L, pady=(0, PAD_S))
        dec_frm.columnconfigure(1, weight=1)

        ttk.Label(dec_frm, text="Wurzelname", font=FONT_SM).grid(
            row=0, column=0, sticky="w", padx=(0, PAD_S), pady=PAD_XS)
        self.root_var  = tk.StringVar()
        root_entry = ttk.Entry(dec_frm, textvariable=self.root_var,
                               width=48, font=FONT_BODY)
        root_entry.grid(row=0, column=1, sticky="ew", pady=PAD_XS)
        root_entry.bind("<Return>", lambda e: self._fill_from_root())
        ttk.Button(dec_frm, text="⚡", width=3,
                   command=self._fill_from_root).grid(
            row=0, column=2, padx=(PAD_S, 0), pady=PAD_XS)

    def _build_notebook(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=PAD_S, pady=(PAD_XS, PAD_S))

        self.boards_tab = BoardsTab(nb, self._custom, self._schedule_preview)
        nb.add(self.boards_tab, text="  Platten  ")

        self.edges_tab = EdgesTab(nb, self._custom, self._schedule_preview)
        nb.add(self.edges_tab, text="  Kanten  ")

        self.preview_tab = PreviewTab(nb)
        nb.add(self.preview_tab, text="  Vorschau  ")

    def _build_bottom_bar(self):
        bar_frame = ttk.Frame(self)
        bar_frame.pack(side="bottom", fill="x")
        ttk.Separator(bar_frame, orient="horizontal").pack(fill="x")
        bar = ttk.Frame(bar_frame, padding=(PAD_L, PAD_S))
        bar.pack(fill="x")
        ttk.Button(bar, text="Zurücksetzen",
                   command=self._reset_all).pack(side="left", padx=(0, PAD_S))
        ttk.Button(bar, text="Platten verwalten",
                   command=self._open_boards_table).pack(side="left", padx=(0, PAD_S))
        ttk.Button(bar, text="Kanten verwalten",
                   command=self._open_edges_table).pack(side="left")
        ttk.Button(bar, text="Einträge schreiben",
                   command=self._write_entries).pack(side="right")

    # ── AGO selection ─────────────────────────────────────────────────────────

    def _search_agos(self):
        agos = find_agos()
        self.after(0, lambda: self._agos_loaded(agos))

    def _agos_loaded(self, agos):
        self._agos = agos
        if not agos:
            self.ago_combo.set("Kein AGO gefunden")
            return
        seen = {}
        for label, path in agos:
            name = os.path.basename(os.path.dirname(os.path.dirname(path)))
            name = name if name else label
            if path not in seen:
                seen[path] = name
        display = list(seen.values())
        paths   = list(seen.keys())
        self._agos = list(zip(display, paths))
        self.ago_combo.config(values=display)
        if self._last_ago and self._last_ago in display:
            self.ago_combo.set(self._last_ago)
        else:
            self.ago_combo.set(display[0])
        self._on_ago_selected()

    def _on_ago_selected(self, event=None):
        label  = self.ago_combo.get()
        values = list(self.ago_combo["values"])
        try:
            idx = values.index(label)
        except ValueError:
            return
        if idx >= len(self._agos):
            return
        _, path = self._agos[idx]
        self.boards_path.set(os.path.join(path, "Boards.txt"))
        self.edges_path.set(os.path.join(path, "Edges.txt"))
        self.ago_path_var.set(os.path.dirname(os.path.dirname(path)))
        self._custom["last_ago"] = label
        save_custom(self._custom)

    def _choose_ago_manually(self):
        folder = filedialog.askdirectory(
            title="AGO-Ordner wählen (Stammordner des AGO)")
        if not folder:
            return
        sd = os.path.join(folder, STAMMDATEN_REL)
        b  = os.path.join(sd, "Boards.txt")
        e  = os.path.join(sd, "Edges.txt")
        if not os.path.isfile(b) or not os.path.isfile(e):
            messagebox.showerror(
                "Kein gültiger AGO",
                "Im gewählten Ordner wurde kein\n"
                "interiorcad/Stammdaten-Verzeichnis gefunden.")
            return
        label = os.path.basename(folder) + "  (manuell)"
        self._agos.append((label, sd))
        self.boards_path.set(b)
        self.edges_path.set(e)
        self.ago_path_var.set(sd)
        values = list(self.ago_combo["values"]) + [label]
        self.ago_combo["values"] = values
        self.ago_var.set(label)

    # ── Fill from root ────────────────────────────────────────────────────────

    def _fill_from_root(self):
        root = self.root_var.get().strip()
        if not root:
            messagebox.showwarning("Wurzelname fehlt",
                "Bitte zuerst einen Wurzelnamen eingeben.")
            return
        d = derive_all(root)
        bv = self.boards_tab.board_vars
        bv["item_no"].set(d["item_no"])
        bv["supplier_id"].set(d["supplier_id"])
        bv["description"].set(d["description"])
        bv["group"].set(d["group_label"])
        bv["cov1_tex"].set(d["decor"])
        bv["cov2_tex"].set(d["decor"])
        self.edges_tab.edge_vars["edge_texture"].set(d["decor"])
        edge_root = re.sub(r'^Dekorspanplatte\s+', 'Sicherheitskante ABS ', root)
        self.edges_tab.edge_root_var.set(edge_root)

    # ── Reset ─────────────────────────────────────────────────────────────────

    def _reset_all(self):
        self.root_var.set("")
        self.boards_tab.reset()
        self.edges_tab.reset()
        self._rebuild_preview()

    # ── Preview ───────────────────────────────────────────────────────────────

    def _schedule_preview(self):
        self.after(50, self._rebuild_preview)

    def _rebuild_preview(self):
        bv         = self.boards_tab.board_vars
        item_no    = bv.get("item_no",     tk.StringVar()).get().strip()
        description = bv.get("description", tk.StringVar()).get().strip()
        supplier   = bv.get("supplier",    tk.StringVar()).get().strip()
        supplier_id = bv.get("supplier_id", tk.StringVar()).get().strip()
        group_label = bv.get("group",       tk.StringVar()).get().strip()
        grain      = bv.get("grain",       tk.StringVar()).get().strip()
        btype      = bv.get("btype",       tk.StringVar()).get().strip()

        ev          = self.edges_tab.edge_vars
        edge_root   = self.edges_tab.edge_root_var.get().strip()
        edge_texture  = ev.get("edge_texture",  tk.StringVar()).get().strip()
        edge_supplier = ev.get("edge_supplier",  tk.StringVar()).get().strip()
        edge_item_base = ev.get("edge_item_no", tk.StringVar()).get().strip()

        _grain_map = {"length": "Längs", "width": "Quer", "none": "Keine"}
        _type_map  = {o[1]: o[0] for o in [
            ("Fertig beschichtet", "melamine"), ("Fertig furniert", "veneer"),
            ("Leimholz", "gw"), ("3-Schichtplatte", "3l"), ("Massiv", "solid"),
            ("Glas", "glass"), ("Stahl", "steel"), ("Standard", "custom"),
        ]}

        from core.derive import (replace_thickness_in_item_no,
                                  replace_thickness_in_name,
                                  make_edge_item_no, make_edge_description)

        board_rows = []
        for t in sorted(self.boards_tab.get_all_thick_vars().keys()):
            if self.boards_tab.get_all_thick_vars()[t].get():
                ni = replace_thickness_in_item_no(item_no, t) if item_no else "–"
                nd = replace_thickness_in_name(description, t) if description else "–"
                ns = replace_thickness_in_item_no(supplier_id, t) if supplier_id else "–"
                board_rows.append((
                    ni, nd, t, supplier or "–", ns,
                    _type_map.get(btype, btype) or "–",
                    _grain_map.get(grain, grain) or "–"))
        self.preview_tab.update_boards(board_rows)

        edge_rows = []
        for (ew, et), var in sorted(self.edges_tab.get_all_kante_vars().items()):
            if var.get():
                if edge_item_base:
                    ts = str(int(et)) if et == int(et) else str(et)
                    ei = "{}-{}x{}".format(edge_item_base, ew, ts)
                elif item_no:
                    ei = make_edge_item_no(item_no, ew, et)
                else:
                    ei = "–"
                if edge_root:
                    ts_str = str(int(et)) if et == int(et) else str(et)
                    ts_str = ts_str.replace(".", ",")
                    ed = re.sub(r'\d+mm\s*$', "{}x{}mm".format(ew, ts_str),
                                edge_root.rstrip())
                    if ed == edge_root.rstrip():
                        ed = "{} {}x{}mm".format(edge_root.strip(), ew, ts_str)
                else:
                    ed = make_edge_description(description, ew, et) if description else "–"
                ts = str(int(et)) if et == int(et) else str(et)
                edge_rows.append((ei, ed, ew, ts, edge_supplier or "–",
                                  edge_texture or "–"))
        self.preview_tab.update_edges(edge_rows)

    # ── Write ─────────────────────────────────────────────────────────────────

    def _write_entries(self):
        boards_file = self.boards_path.get().strip()
        edges_file  = self.edges_path.get().strip()
        if not boards_file or not os.path.isfile(boards_file):
            messagebox.showerror("Fehler",
                "Kein gültiger AGO ausgewählt (Boards.txt nicht gefunden).")
            return
        if not edges_file or not os.path.isfile(edges_file):
            messagebox.showerror("Fehler",
                "Kein gültiger AGO ausgewählt (Edges.txt nicht gefunden).")
            return

        bv = self.boards_tab.board_vars
        ev = self.edges_tab.edge_vars

        item_no     = bv["item_no"].get().strip()
        if not item_no:
            messagebox.showwarning("Fehlende Daten",
                "Bitte zuerst den Wurzelnamen eingeben und ⚡ klicken.")
            return

        description = bv["description"].get().strip()
        supplier    = bv["supplier"].get().strip()
        supplier_id = bv["supplier_id"].get().strip()
        price       = bv["price"].get().strip()
        unit        = bv["unit"].get().strip()
        amount      = bv["amount"].get().strip()
        waste       = bv["waste"].get().strip()
        markup      = bv["markup"].get().strip()
        grain       = bv["grain"].get().strip()
        btype       = bv["btype"].get().strip()
        cov1_thick  = bv["cov1_thick"].get().strip()
        cov2_thick  = bv["cov2_thick"].get().strip()
        texture     = bv["texture"].get().strip()
        cov1_tex    = bv["cov1_tex"].get().strip()
        cov2_tex    = bv["cov2_tex"].get().strip()
        group       = bv.get("group", tk.StringVar()).get().strip()

        from core.derive import (derive_group, replace_thickness_in_item_no,
                                  replace_thickness_in_name,
                                  make_edge_item_no, make_edge_description)

        if not group:
            group = derive_group(item_no)

        edge_supplier  = ev["edge_supplier"].get().strip()
        edge_waste     = ev["edge_waste"].get().strip()
        edge_texture   = ev["edge_texture"].get().strip()
        edge_item_base = ev.get("edge_item_no", tk.StringVar()).get().strip()
        edge_root      = self.edges_tab.edge_root_var.get().strip()

        existing_boards = load_existing_ids(boards_file)
        existing_edges  = load_existing_ids(edges_file)

        board_lines = []; edge_lines = []
        skipped_b   = []; skipped_e  = []

        all_thick_vars = self.boards_tab.get_all_thick_vars()
        for t in sorted(all_thick_vars.keys()):
            if all_thick_vars[t].get():
                ni = replace_thickness_in_item_no(item_no, t)
                if ni == item_no:
                    if item_no in existing_boards:
                        skipped_b.append(item_no)
                    else:
                        board_lines.append(build_board_line(
                            item_no, description, supplier, supplier_id,
                            price, unit, amount, waste, markup,
                            t, group, texture,
                            grain, btype, cov1_thick, cov2_thick,
                            cov1_tex, cov2_tex))
                    continue
                nd = replace_thickness_in_name(description, t)
                ns = replace_thickness_in_item_no(supplier_id, t)
                if ni in existing_boards:
                    skipped_b.append(ni)
                else:
                    board_lines.append(build_board_line(
                        ni, nd, supplier, ns,
                        price, unit, amount, waste, markup,
                        t, group, texture,
                        grain, btype, cov1_thick, cov2_thick,
                        cov1_tex, cov2_tex))

        all_kante_vars = self.edges_tab.get_all_kante_vars()
        for (ew, et), var in sorted(all_kante_vars.items()):
            if var.get():
                if edge_item_base:
                    ts = str(int(et)) if et == int(et) else str(et)
                    ei = "{}-{}x{}".format(edge_item_base, ew, ts)
                else:
                    ei = make_edge_item_no(item_no, ew, et)
                if edge_root:
                    ts_str = str(int(et)) if et == int(et) else str(et)
                    ts_str = ts_str.replace(".", ",")
                    ed = re.sub(r'\d+mm\s*$', "{}x{}mm".format(ew, ts_str),
                                edge_root.rstrip())
                    if ed == edge_root.rstrip():
                        ed = "{} {}x{}mm".format(edge_root.strip(), ew, ts_str)
                else:
                    ed = make_edge_description(description, ew, et)
                if ei in existing_edges:
                    skipped_e.append(ei)
                else:
                    edge_lines.append(build_edge_line(
                        ei, ed, edge_supplier, ei,
                        0, "m", 1, edge_waste, 0,
                        ew, et, edge_texture))

        if not board_lines and not edge_lines:
            messagebox.showwarning("Nichts zu tun",
                "Alle gewählten Einträge existieren bereits.")
            return

        try:
            append_lines(boards_file, board_lines)
            append_lines(edges_file,  edge_lines)
        except Exception as e:
            messagebox.showerror("Fehler beim Schreiben", str(e))
            return

        msg = "Erfolgreich gespeichert!\n\n"
        msg += "• {} Platte(n) neu\n".format(len(board_lines))
        msg += "• {} Kante(n) neu\n".format(len(edge_lines))
        if skipped_b or skipped_e:
            msg += "\nÜbersprungen (bereits vorhanden):\n"
            for s in skipped_b:
                msg += "  Platte: {}\n".format(s)
            for s in skipped_e:
                msg += "  Kante:  {}\n".format(s)
        messagebox.showinfo("Fertig", msg)

    # ── Table dialogs ─────────────────────────────────────────────────────────

    def _open_boards_table(self):
        boards_file = self.boards_path.get().strip()
        if not boards_file or not os.path.isfile(boards_file):
            messagebox.showerror("Fehler", "Bitte zuerst einen AGO auswählen.")
            return
        BoardsTable(self, boards_file)

    def _open_edges_table(self):
        edges_file = self.edges_path.get().strip()
        if not edges_file or not os.path.isfile(edges_file):
            messagebox.showerror("Fehler", "Bitte zuerst einen AGO auswählen.")
            return
        EdgesTable(self, edges_file)
