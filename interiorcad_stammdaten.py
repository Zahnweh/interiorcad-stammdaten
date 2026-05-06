#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interiorcad Stammdaten Tool
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os, re, codecs, glob, json, shutil, sys, tempfile, xml.etree.ElementTree as ET
import platform

IS_MAC     = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"

VERSION     = "1.0.0"
GITHUB_REPO = "Zahnweh/interiorcad-stammdaten"

# ── Konstanten ────────────────────────────────────────────────────────────────

BOARD_THICKNESSES = [5, 8, 13, 16, 19, 22, 25, 28, 32, 38]
EDGE_WIDTHS       = [16, 19, 23, 25, 26, 28, 29, 33, 43]
EDGE_THICKNESSES  = [1.0, 2.0, 3.0]
STAMMDATEN_REL    = os.path.join("interiorcad", "Stammdaten")

if platform.system() == "Darwin":
    FONT      = ("System", 13)
    FONT_SM   = ("System", 13)
    FONT_BOLD = ("System", 13, "bold")
else:
    FONT      = ("Segoe UI", 11)
    FONT_SM   = ("Segoe UI", 11)
    FONT_BOLD = ("Segoe UI", 11, "bold")

def _get_custom_file():
    app_name = "interiorcad Stammdaten"
    if IS_WINDOWS:
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.expanduser("~/Library/Application Support")
    folder = os.path.join(base, app_name)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "custom_values.json")

CUSTOM_FILE = _get_custom_file()

def load_custom():
    try:
        with open(CUSTOM_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"thicknesses": [], "edges": []}

def save_custom(data):
    try:
        with open(CUSTOM_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

# ── AGO-Erkennung ─────────────────────────────────────────────────────────────

def find_agos_windows():
    found = {}

    def add(folder_path, label=None):
        sd = os.path.join(folder_path, STAMMDATEN_REL)
        if os.path.isfile(os.path.join(sd, "Boards.txt")) and \
           os.path.isfile(os.path.join(sd, "Edges.txt")):
            sd_key = sd.lower()
            if sd_key not in found:
                found[sd_key] = (label or os.path.basename(
                    folder_path.rstrip("\\")), sd)

    try:
        import winreg
        nemetschek = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                    r"Software\Nemetschek")
        i = 0
        while True:
            try:
                vw_name = winreg.EnumKey(nemetschek, i)
                try:
                    general = winreg.OpenKey(nemetschek,
                                             vw_name + "\\General")
                    j = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(general, j)
                            if name.startswith("Workgroup Folder"):
                                folder = value.strip().rstrip("\\")
                                if os.path.isdir(folder):
                                    add(folder)
                            j += 1
                        except OSError:
                            break
                except OSError:
                    pass
                i += 1
            except OSError:
                break
    except Exception:
        pass

    # Fallback: Desktop und Dokumente
    for base in [os.path.expanduser("~/Desktop"),
                 os.path.expanduser("~/Documents")]:
        if os.path.isdir(base):
            try:
                for entry in os.scandir(base):
                    if entry.is_dir():
                        add(entry.path)
            except PermissionError:
                pass

    return sorted([(v[0], v[1]) for v in found.values()],
                  key=lambda x: x[0])


def find_agos_mac():
    found = {}
    def add(folder_path, label=None, overwrite=False):
        sd = os.path.join(folder_path, STAMMDATEN_REL)
        if os.path.isfile(os.path.join(sd, "Boards.txt")) and            os.path.isfile(os.path.join(sd, "Edges.txt")):
            sd_real = os.path.realpath(sd)
            if sd_real not in found or overwrite:
                found[sd_real] = label or os.path.basename(folder_path)
    vw_base = os.path.expanduser(
        "~/Library/Application Support/Vectorworks")
    for settings_file in glob.glob(
            os.path.join(vw_base, "*", "Einstellungen",
                         "SavedSettingsUser.xml")):
        try:
            tree = ET.parse(settings_file)
            root = tree.getroot()
            for tag in ["WorkgroupFolderSelection",
                        "workgroupFolderSelection",
                        "WorkgroupFolder"]:
                el = root.find(".//" + tag)
                if el is not None and el.text:
                    _p = el.text.strip().rstrip("/")
                    if os.path.isdir(_p):
                        _n = os.path.basename(_p)
                        if _n:
                            add(_p, _n, overwrite=True)
        except Exception:
            pass
    cloud = os.path.expanduser("~/Library/CloudStorage")
    if os.path.isdir(cloud):
        for pattern in [
            os.path.join(cloud, "*"),
            os.path.join(cloud, "*", "*"),
            os.path.join(cloud, "*", "*", "*"),
        ]:
            for p in glob.glob(pattern):
                if os.path.isdir(p):
                    add(p)
    for base in [os.path.expanduser("~/Desktop"),
                 os.path.expanduser("~/Documents")]:
        if os.path.isdir(base):
            try:
                for entry in os.scandir(base):
                    if entry.is_dir():
                        add(entry.path)
            except PermissionError:
                pass
    seen_paths = set()
    unique = []
    for path, label in found.items():
        if path not in seen_paths:
            seen_paths.add(path)
            unique.append((label, path))
    return sorted(unique, key=lambda x: x[0])


def find_agos():
    if IS_WINDOWS:
        return find_agos_windows()
    else:
        return find_agos_mac()


# ── Ableitungs-Logik ──────────────────────────────────────────────────────────

def extract_decor_code(name):
    for token in name.split():
        if re.match(r'^[A-Za-z].*\d', token):
            return token
    return ""

def extract_structure(name):
    tokens = name.split()
    for i, token in enumerate(tokens):
        if re.match(r'^[A-Za-z].*\d', token):
            if i + 1 < len(tokens) and \
               re.match(r'^ST\d', tokens[i+1], re.IGNORECASE):
                return tokens[i+1]
    return ""

def derive_all(root_name):
    decor  = extract_decor_code(root_name)
    struct = extract_structure(root_name)
    group  = "KF-{}-{}".format(decor, struct) if struct else \
             "KF-{}".format(decor)
    group_label = "{} {}".format(decor, struct).strip() if struct else decor
    return {
        "item_no":     group,
        "supplier_id": group,
        "group":       group,
        "group_label": group_label,
        "description": root_name.strip(),
        "decor":       decor,
    }

# ── Datei-Hilfsfunktionen ─────────────────────────────────────────────────────

def derive_group(item_no):
    p = item_no.rsplit("-", 1)
    return p[0] if len(p) == 2 else item_no

def replace_thickness_in_name(name, t):
    result = re.sub(r'\d+mm\s*$', '{}mm'.format(t), name.rstrip())
    if result == name.rstrip():
        result = "{} {}mm".format(name.strip(), t)
    return result

def replace_thickness_in_item_no(item_no, t):
    if re.search(r'-[0-9]{1,2}$', item_no):
        p = item_no.rsplit('-', 1)
        return p[0] + '-' + str(t).zfill(2)
    return item_no + '-' + str(t).zfill(2)

def make_edge_item_no(base_item_no, width, thickness):
    group = derive_group(base_item_no)
    parts = group.split("-", 1)
    core  = parts[1] if len(parts) == 2 else group
    ts    = str(int(thickness)) if thickness == int(thickness) \
            else str(thickness)
    return "Ka-{}-{}x{}".format(core, width, ts)

def make_edge_description(board_desc, width, thickness):
    name = re.sub(r'^Dekorspanplatte\s+', 'Sicherheitskante ABS ',
                  board_desc)
    ts   = str(int(thickness)) if thickness == int(thickness) \
           else str(thickness)
    ts   = ts.replace(".", ",")
    return re.sub(r'\d+mm\s*$', "{}x{}mm".format(width, ts),
                  name.rstrip())

def tab_join(fields):
    return "\t".join([str(f) for f in fields])

def build_board_line(item_no, desc, supplier, supplier_id, price, unit,
                     amount, waste, markup, thickness, group, texture,
                     grain, btype, cov1_thick, cov2_thick,
                     cov1_tex, cov2_tex):
    return tab_join([
        item_no, desc, supplier, supplier_id,
        price, unit, amount, waste, markup,
        0, 0, thickness,
        group, texture, thickness, grain, btype,
        cov1_thick, cov2_thick, cov1_tex, cov2_tex
    ])

def build_edge_line(item_no, desc, supplier, supplier_id, price,
                    unit, amount, waste, markup, width, thickness,
                    texture):
    return tab_join([
        item_no, desc, supplier, supplier_id,
        price, unit, amount, waste, markup,
        0, width, thickness,
        "IGNORE", texture, 0,
        "IGNORE", "IGNORE", 0, 0, "IGNORE", "IGNORE"
    ])

def load_existing_ids(filepath):
    ids = set()
    try:
        with codecs.open(filepath, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                ids.add(line.split("\t")[0].strip())
    except Exception:
        pass
    return ids

def append_lines(filepath, lines):
    with codecs.open(filepath, "a", encoding="utf-8") as f:
        for line in lines:
            f.write("\n" + line)

# ── Auto-Update ───────────────────────────────────────────────────────────────

def _ver_tuple(v):
    try:
        return tuple(int(x) for x in v.strip().lstrip("v").split("."))
    except Exception:
        return (0,)

def _shell_quote(s):
    return "'" + s.replace("'", "'\\''") + "'"

def _get_app_path():
    if not getattr(sys, "frozen", False):
        return None
    if IS_MAC:
        path = sys.executable
        for _ in range(5):
            path = os.path.dirname(path)
            if path.endswith(".app"):
                return path
        return None
    return sys.executable

def _check_for_updates(app):
    import urllib.request, json as _json
    try:
        url = "https://api.github.com/repos/{}/releases/latest".format(GITHUB_REPO)
        req = urllib.request.Request(
            url, headers={"User-Agent": "interiorcad-Stammdaten/{}".format(VERSION)})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = _json.loads(resp.read().decode())
        tag = data.get("tag_name", "")
        ver = tag.lstrip("v")
        if ver and _ver_tuple(ver) > _ver_tuple(VERSION):
            app.after(0, lambda: _offer_update(app, data))
    except Exception:
        pass

def _offer_update(app, release_data):
    tag = release_data.get("tag_name", "?")
    if not messagebox.askyesno(
            "Update verfügbar",
            "Version {} ist verfügbar (aktuell: v{}).\n\n"
            "Jetzt herunterladen und installieren?".format(tag, VERSION),
            parent=app):
        return
    assets = release_data.get("assets", [])
    if IS_MAC:
        arch_str = "arm64" if platform.machine() == "arm64" else "intel"
        asset = next(
            (a for a in assets if "mac-{}".format(arch_str) in a["name"].lower()), None)
        if not asset:
            asset = next(
                (a for a in assets
                 if "mac" in a["name"].lower() and a["name"].endswith(".zip")), None)
    elif IS_WINDOWS:
        asset = next(
            (a for a in assets if a["name"].lower().endswith(".exe")), None)
    else:
        asset = None
    if not asset:
        import webbrowser
        webbrowser.open(release_data.get("html_url", ""))
        return
    _run_download(app, asset["browser_download_url"], tag)


class _UpdateDlg(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Update wird heruntergeladen…")
        self.resizable(False, False)
        self.grab_set()
        self.cancelled = False
        frm = ttk.Frame(self, padding=20)
        frm.pack()
        self._lbl = ttk.Label(frm, text="Verbinde…", font=FONT_SM, width=40)
        self._lbl.pack(pady=(0, 8))
        self._bar = ttk.Progressbar(frm, length=320, mode="determinate")
        self._bar.pack()
        ttk.Button(frm, text="Abbrechen",
                   command=self._cancel).pack(pady=(12, 0))
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("+{}+{}".format((sw - self.winfo_width()) // 2,
                                      (sh - self.winfo_height()) // 2))

    def _cancel(self):
        self.cancelled = True
        self.destroy()

    def set_progress(self, pct, text):
        if self.winfo_exists():
            self._bar["value"] = pct
            self._lbl.config(text=text)
            self.update_idletasks()


def _run_download(app, url, tag):
    import urllib.request, threading
    dlg = _UpdateDlg(app)
    suffix = ".zip" if IS_MAC else ".exe"

    def _worker():
        tmp = tempfile.mktemp(suffix=suffix)
        try:
            def _progress(count, block, total):
                if dlg.cancelled:
                    raise Exception("Abgebrochen")
                if total > 0:
                    pct = min(100, count * block * 100 // total)
                    done_mb = count * block / 1_048_576
                    total_mb = total / 1_048_576
                    app.after(0, lambda p=pct, d=done_mb, t=total_mb:
                        dlg.set_progress(p, "{:.1f} / {:.1f} MB".format(d, t)))
            urllib.request.urlretrieve(url, tmp, reporthook=_progress)
            if dlg.cancelled:
                return
            app.after(0, lambda: dlg.destroy())
            app.after(100, lambda: _install(app, tmp))
        except Exception as e:
            if not dlg.cancelled:
                app.after(0, lambda err=str(e):
                    messagebox.showerror("Download-Fehler", err, parent=app))
            try:
                os.remove(tmp)
            except Exception:
                pass
            if dlg.winfo_exists():
                app.after(0, dlg.destroy)

    threading.Thread(target=_worker, daemon=True).start()


def _install(app, tmp_path):
    import subprocess
    app_path = _get_app_path()
    try:
        if IS_MAC:
            tmp_dir = tempfile.mkdtemp()
            subprocess.run(["ditto", "-xk", tmp_path, tmp_dir], check=True)
            bundles = [f for f in os.listdir(tmp_dir) if f.endswith(".app")]
            if not bundles:
                raise Exception("Kein .app Bundle im Archiv.")
            new_app = os.path.join(tmp_dir, bundles[0])
            if not app_path:
                dst = os.path.join(os.path.expanduser("~/Downloads"), bundles[0])
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(new_app, dst)
                shutil.rmtree(tmp_dir, ignore_errors=True)
                os.remove(tmp_path)
                messagebox.showinfo("Update bereit",
                    "Neue Version liegt unter:\n~/Downloads/{}\n\n"
                    "Bitte die App ersetzen und neu starten.".format(bundles[0]),
                    parent=app)
                return
            script = (
                "#!/bin/bash\n"
                "while kill -0 {pid} 2>/dev/null; do sleep 0.3; done\n"
                "rm -rf {old}\n"
                "ditto {new} {old}\n"
                "open {old}\n"
                "rm -rf {tmp_dir}\n"
                "rm -- \"$0\"\n"
            ).format(
                pid=os.getpid(),
                old=_shell_quote(app_path),
                new=_shell_quote(new_app),
                tmp_dir=_shell_quote(tmp_dir))
            sh = tempfile.mktemp(suffix=".sh")
            with open(sh, "w") as f:
                f.write(script)
            os.chmod(sh, 0o755)
            subprocess.Popen(["/bin/bash", sh])
            messagebox.showinfo("Update wird installiert",
                "Die App wird jetzt beendet und neu gestartet.", parent=app)
            app.destroy()
            sys.exit(0)

        elif IS_WINDOWS:
            if not app_path:
                dst = os.path.join(os.path.expanduser("~/Downloads"),
                                   os.path.basename(tmp_path))
                shutil.copy2(tmp_path, dst)
                os.remove(tmp_path)
                messagebox.showinfo("Update bereit",
                    "Neue Version liegt unter:\n{}\n\n"
                    "Bitte die App ersetzen und neu starten.".format(dst),
                    parent=app)
                return
            bat = tempfile.mktemp(suffix=".bat")
            pid = os.getpid()
            with open(bat, "w") as f:
                f.write("@echo off\r\n")
                f.write(":wait\r\n")
                f.write("tasklist /FI \"PID eq {p}\" 2>NUL | "
                        "find /I \"{p}\" >NUL\r\n".format(p=pid))
                f.write("if not errorlevel 1 "
                        "(timeout /t 1 /nobreak >nul & goto wait)\r\n")
                f.write("copy /y \"{src}\" \"{dst}\"\r\n".format(
                    src=tmp_path, dst=app_path))
                f.write("start \"\" \"{exe}\"\r\n".format(exe=app_path))
                f.write("del \"{}\"\r\n".format(tmp_path))
                f.write("del \"%~f0\"\r\n")
            subprocess.Popen(
                ["cmd", "/c", bat],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW)
            app.destroy()
            sys.exit(0)

    except Exception as e:
        messagebox.showerror("Installations-Fehler",
            "Automatische Installation fehlgeschlagen:\n{}\n\n"
            "Heruntergeladene Datei:\n{}".format(e, tmp_path),
            parent=app)


# ── Haupt-App ─────────────────────────────────────────────────────────────────

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title("interiorcad Stammdaten Tool")
        self.resizable(True, True)
        self._agos              = []
        self.boards_path        = tk.StringVar()
        self.edges_path         = tk.StringVar()
        self.ago_path_var       = tk.StringVar()
        self._custom            = load_custom()
        self._custom_thick_vars = {}
        self._custom_edge_vars  = {}
        self._last_ago          = self._custom.get("last_ago", "")
        self._build_ui()
        import threading
        threading.Thread(target=self._search_agos, daemon=True).start()
        threading.Thread(target=lambda: _check_for_updates(self), daemon=True).start()
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = min(1100, sw - 40)
        h = min(int(sh * 0.9), sh - 80)
        self.geometry("{}x{}+{}+{}".format(
            w, h, (sw - w) // 2, (sh - h) // 2))
        self.deiconify()

    # ── AGO-Suche im Hintergrund ──────────────────────────────────────────────

    def _search_agos(self):
        agos = find_agos()
        self.after(0, lambda: self._agos_loaded(agos))

    def _agos_loaded(self, agos):
        self._agos = agos
        if not agos:
            self.ago_combo.set("Kein AGO gefunden")
            return
        # Anzeigenamen ableiten und nach Pfad deduplizieren
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
        # Letzten AGO wiederherstellen falls vorhanden
        if self._last_ago and self._last_ago in display:
            self.ago_combo.set(self._last_ago)
        else:
            self.ago_combo.set(display[0])
        self._on_ago_selected()

    # ── Hilfsmethoden ─────────────────────────────────────────────────────────

    def _field_row(self, parent, label, key, store_vars, store_entries,
                   locked=False, row=0):
        COATING_KEYS  = {"cov1_thick", "cov2_thick", "cov1_tex", "cov2_tex"}
        READONLY_KEYS = {"thickness"} | COATING_KEYS
        lbl = ttk.Label(parent, text=label, font=FONT_SM,
                        foreground="gray" if key in COATING_KEYS else "")
        lbl.grid(row=row, column=0, sticky="w", padx=(0, 10), pady=3)
        if not hasattr(self, "_coating_labels"):
            self._coating_labels = {}
        if key in COATING_KEYS:
            self._coating_labels[key] = lbl
        var   = tk.StringVar()
        state = "readonly" if key in READONLY_KEYS else "normal"
        entry = ttk.Entry(parent, textvariable=var, width=32,
                          font=FONT, state=state)
        entry.grid(row=row, column=1, columnspan=2,
                   sticky="ew", ipady=3, pady=3)
        store_vars[key]    = var
        store_entries[key] = entry
        return var

    def _section(self, parent, text):
        f = ttk.Frame(parent)
        f.pack(fill="x", padx=16, pady=(12, 2))
        ttk.Label(f, text=text, font=FONT_BOLD).pack(side="left")
        ttk.Separator(f, orient="horizontal").pack(
            side="left", fill="x", expand=True, padx=(8, 0), pady=6)

    # ── UI aufbauen ───────────────────────────────────────────────────────────

    def _build_ui(self):
        # Bottom-Bar fest unten verankern
        self._bottom_bar = ttk.Frame(self)
        self._bottom_bar.pack(side="bottom", fill="x")
        ttk.Separator(self._bottom_bar, orient="horizontal").pack(
            fill="x", pady=(0, 0))
        _bar = ttk.Frame(self._bottom_bar, padding=(16, 8))
        _bar.pack(fill="x")
        ttk.Button(_bar, text="Zurücksetzen",
                   command=self._reset_all).pack(side="left", padx=(0, 6))
        ttk.Button(_bar, text="📋  Platten verwalten",
                   command=self._open_boards_table).pack(side="left", padx=(0, 6))
        ttk.Button(_bar, text="📋  Kanten verwalten",
                   command=self._open_edges_table).pack(side="left", padx=(0, 6))
        ttk.Button(_bar, text="✔  Einträge schreiben",
                   command=self._write_entries).pack(side="right")

        # Scrollbarer Bereich
        _canvas = tk.Canvas(self, highlightthickness=0)
        _vsb = ttk.Scrollbar(self, orient="vertical", command=_canvas.yview)
        _canvas.configure(yscrollcommand=_vsb.set)
        _vsb.pack(side="right", fill="y")
        _canvas.pack(side="left", fill="both", expand=True)
        p = ttk.Frame(_canvas)
        _win = _canvas.create_window((0, 0), window=p, anchor="nw")
        p.bind("<Configure>", lambda e: _canvas.configure(
            scrollregion=_canvas.bbox("all")))
        _canvas.bind("<Configure>", lambda e: _canvas.itemconfig(
            _win, width=e.width))
        def _scroll(e):
            top, bottom = _canvas.yview()
            if (e.delta > 0 and top <= 0.001) or (e.delta < 0 and bottom >= 0.999):
                return "break"
            _canvas.yview_scroll(int(-1 * e.delta), "units")
            return "break"

        self._scroll_handler = _scroll
        if IS_WINDOWS:
            def _scroll_win(e):
                top, bottom = _canvas.yview()
                if (e.delta > 0 and top <= 0.001) or (e.delta < 0 and bottom >= 0.999):
                    return "break"
                _canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
                return "break"
            self.bind_all("<MouseWheel>", _scroll_win)
            self._scroll_handler = _scroll_win
        else:
            self.bind_all("<MouseWheel>", _scroll)

        # ── AGO-Auswahl ───────────────────────────────────────────────────────
        self._section(p, "Arbeitsgruppenordner (AGO)")
        ago_frame = ttk.LabelFrame(p, padding=10)
        ago_frame.pack(fill="x", padx=16, pady=(0, 4))

        ttk.Label(ago_frame, text="AGO", font=FONT_SM).grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=4)

        self.ago_var = tk.StringVar()
        ago_labels = [label for label, _ in self._agos]

        self.ago_combo = ttk.Combobox(
            ago_frame, textvariable=self.ago_var,
            values=ago_labels, state="readonly",
            font=FONT, width=50)
        self.ago_combo.grid(row=0, column=1, sticky="ew",
                            ipady=3, pady=4)
        self.ago_combo.bind("<<ComboboxSelected>>",
                            self._on_ago_selected)
        if not ago_labels:
            self.ago_combo.set("Suche läuft…")

        ttk.Button(ago_frame, text="…", width=3,
                   command=self._choose_ago_manually).grid(
            row=0, column=2, padx=(8, 0), pady=4)

        # Pfad-Anzeige (readonly, klein)
        ttk.Label(ago_frame, textvariable=self.ago_path_var,
                  font=("System", 11),
                  foreground="gray").grid(
            row=1, column=1, sticky="w", pady=(0, 4))


        # ── Dekor / Wurzelname ────────────────────────────────────────────────
        self._section(p, "Dekor")
        dec = ttk.LabelFrame(p, padding=10)
        dec.pack(fill="x", padx=16, pady=(0, 4))

        ttk.Label(dec, text="Wurzelname", font=FONT_SM).grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.root_var = tk.StringVar()
        _root_entry = ttk.Entry(dec, textvariable=self.root_var, width=48, font=FONT)
        _root_entry.grid(row=0, column=1, sticky="ew", ipady=3, pady=4)
        _root_entry.bind("<Return>", lambda e: self._fill_from_root())
        ttk.Button(dec, text="⚡", width=3,
                   command=self._fill_from_root).grid(
            row=0, column=2, padx=(8, 0), pady=4)

        # ── Zwei Spalten ──────────────────────────────────────────────────────
        cols = ttk.Frame(p)
        cols.pack(fill="both", padx=16, pady=(4, 0))
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        # ── LINKS: Plattenparameter ───────────────────────────────────────────
        left = ttk.Frame(cols)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ttk.Label(left, text="Plattenparameter",
                  font=FONT_BOLD).pack(anchor="w", pady=(8, 2))
        pf = ttk.LabelFrame(left, padding=10)
        pf.pack(fill="x")

        self.board_vars    = {}
        self.board_entries = {}
        board_fields = [
            ("ID (Stamm)",             "item_no",     "",                         True,  None),
            ("Beschreibung (Stamm)",   "description", "",                         True,  None),
            ("Lieferant",             "supplier",    "Holz Hahn GmbH - Krefeld", False, None),
            ("Bestellnr. (Stamm)",     "supplier_id", "",                         True,  None),
            ("Gruppe",                "group",       "",                         True,  None),
            ("Preis",                 "price",       "0",                        False, None),
            ("Einheit",               "unit",        "m2",                       False, None),
            ("Menge/Einheit",         "amount",      "1",                        False, None),
            ("Verschnitt (%)",        "waste",       "25",                       False, None),
            ("Aufschlag",             "markup",      "0",                        False, None),
            ("Maserrichtung",         "grain",       "length",                   False,
                [("Längs","length"),("Quer","width"),("Keine","none")]),
            ("Materialtyp",           "btype",       "melamine",                 False,
                [("Fertig beschichtet","melamine"),("Fertig furniert","veneer"),
                 ("Leimholz","gw"),("3-Schichtplatte","3l"),("Massiv","solid"),
                 ("Glas","glass"),("Stahl","steel"),("Standard","custom")]),
            ("Beschichtung 1 (mm)",    "cov1_thick",  "1",                        True,  None),
            ("Beschichtung 2 (mm)",    "cov2_thick",  "1",                        True,  None),
            ("Textur (Platte)",       "texture",     "Spanplatte",               False, None),
            ("Textur Beschichtung 1",  "cov1_tex",    "",                         True,  None),
            ("Textur Beschichtung 2",  "cov2_tex",    "",                         True,  None),
        ]
        for i, (label, key, default, locked, options) in enumerate(board_fields):
            if options:
                # Dropdown
                ttk.Label(pf, text=label, font=FONT_SM).grid(
                    row=i, column=0, sticky="w", padx=(0, 10), pady=3)
                internal_var = tk.StringVar(value=default)
                display_var  = tk.StringVar()
                self.board_vars[key] = internal_var
                var = internal_var  # für idx-Lookup unten
                display_vals  = [o[0] for o in options]
                internal_vals = [o[1] for o in options]
                combo = ttk.Combobox(pf, textvariable=display_var,
                                     values=display_vals,
                                     state="readonly", width=30, font=FONT)
                # Anzeigewert setzen (deutsch), internen Wert in var
                try:
                    idx = internal_vals.index(default)
                except ValueError:
                    idx = 0
                combo.set(display_vals[idx])
                var.set(internal_vals[idx])
                # var tracen: immer internen Wert halten
                combo.grid(row=i, column=1, sticky="ew", ipady=3, pady=3)
                self.board_entries[key] = combo
                # Beim Auswählen internen Wert in var speichern
                def make_cb(iv, ivals, dvals, cb):
                    def cb_select(e, iv=iv, ivals=ivals, dvals=dvals, cb=cb):
                        try:
                            iv.set(ivals[dvals.index(cb.get())])
                        except ValueError:
                            pass
                    return cb_select
                combo.bind("<<ComboboxSelected>>",
                           make_cb(internal_var, internal_vals,
                                   display_vals, combo))
                if key == "btype":
                    def on_btype(e, cb=combo, ivals=internal_vals,
                                 dvals=display_vals):
                        try:
                            val = ivals[dvals.index(cb.get())]
                        except ValueError:
                            val = ""
                        self._update_coating_fields(val)
                    combo.bind("<<ComboboxSelected>>", on_btype, add="+")
            else:
                var = self._field_row(pf, label, key,
                                      self.board_vars, self.board_entries,
                                      locked=locked, row=i)
                var.set(default)

        # ── RECHTS ────────────────────────────────────────────────────────────
        right = ttk.Frame(cols)
        right.grid(row=0, column=1, sticky="nsew")

        # Kantenparameter
        ttk.Label(right, text="Kantenparameter",
                  font=FONT_BOLD).pack(anchor="w", pady=(8, 2))
        ef = ttk.LabelFrame(right, padding=10)
        ef.pack(fill="x")

        # Kanten-Wurzelname
        ttk.Label(ef, text="Wurzelname", font=FONT_SM).grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=3)
        self.edge_root_var = tk.StringVar()
        ttk.Entry(ef, textvariable=self.edge_root_var, width=32,
                  font=FONT).grid(row=0, column=1, sticky="ew",
                                  ipady=3, pady=3)
        ttk.Button(ef, text="⚡", width=3,
                   command=self._fill_edge_from_root).grid(
            row=0, column=2, padx=(6, 0), pady=3)
        # Kein Stift-Button mehr

        self.edge_vars    = {}
        self.edge_entries = {}
        edge_fields = [
            ("ID (Stamm)",        "edge_item_no",  "",                         True),
            ("Textur (Kante)",  "edge_texture",  "",                         True),
            ("Lieferant",       "edge_supplier", "Holz Hahn GmbH - Krefeld", False),
            ("Verschnitt (%)",  "edge_waste",    "10",                       False),
        ]
        for i, (label, key, default, locked) in enumerate(edge_fields):
            var = self._field_row(ef, label, key,
                                  self.edge_vars, self.edge_entries,
                                  locked=locked, row=i+1)
            var.set(default)

        # Plattenstärken
        ttk.Label(right, text="Plattenstärken",
                  font=FONT_BOLD).pack(anchor="w", pady=(12, 2))
        tf = ttk.LabelFrame(right, padding=10)
        tf.pack(fill="x")

        self.thick_vars = {}
        for idx, t in enumerate(BOARD_THICKNESSES):
            var = tk.BooleanVar(value=False)
            self.thick_vars[t] = var
            ttk.Checkbutton(tf, text="{} mm".format(t),
                            variable=var).grid(
                row=idx // 2, column=idx % 2,
                sticky="w", padx=8, pady=2)
        btn_row = len(BOARD_THICKNESSES)//2 + 1
        ttk.Button(tf, text="Alle auswählen",
                   command=self._select_all_thick).grid(
            row=btn_row, column=0, sticky="w", padx=8, pady=(6, 2))
        ttk.Button(tf, text="Zurücksetzen",
                   command=self._reset_thick).grid(
            row=btn_row, column=1, sticky="w", padx=8, pady=(6, 2))

        # Benutzerdefinierte Stärken
        ttk.Separator(tf, orient="horizontal").grid(
            row=btn_row+1, column=0, columnspan=2,
            sticky="ew", padx=4, pady=(8, 4))
        add_row = btn_row + 2
        self._custom_thick_var = tk.StringVar()
        ttk.Entry(tf, textvariable=self._custom_thick_var,
                  width=6, font=FONT).grid(
            row=add_row, column=0, sticky="w", padx=8, pady=2)
        ttk.Label(tf, text="mm", font=FONT_SM).grid(
            row=add_row, column=0, sticky="e", padx=(0, 4))
        ttk.Button(tf, text="+", width=2,
                   command=self._add_custom_thick).grid(
            row=add_row, column=1, sticky="w", padx=4, pady=2)

        # Frame für custom Checkboxen
        self._custom_thick_frame = ttk.Frame(tf)
        self._custom_thick_frame.grid(
            row=add_row+1, column=0, columnspan=2,
            sticky="ew", padx=4, pady=2)
        self._rebuild_custom_thick()

        # Kanten-Grid
        ttk.Label(right, text="Kanten  (Breite × Dicke)",
                  font=FONT_BOLD).pack(anchor="w", pady=(12, 2))
        kf = ttk.LabelFrame(right, padding=10)
        kf.pack(fill="x")

        ttk.Label(kf, text="", width=5).grid(row=0, column=0)
        for j, et in enumerate(EDGE_THICKNESSES):
            ts = "{}mm".format(int(et) if et == int(et) else et)
            ttk.Label(kf, text=ts, font=FONT_BOLD,
                      width=5).grid(row=0, column=j+1, padx=4)

        self.kante_vars = {}
        for i, ew in enumerate(EDGE_WIDTHS):
            ttk.Label(kf, text="{} mm".format(ew),
                      font=FONT_SM).grid(
                row=i+1, column=0, sticky="w",
                padx=(0, 8), pady=2)
            for j, et in enumerate(EDGE_THICKNESSES):
                var = tk.BooleanVar(value=False)
                self.kante_vars[(ew, et)] = var
                ttk.Checkbutton(kf, variable=var).grid(
                    row=i+1, column=j+1, padx=4, pady=2)
        edge_btn_row = len(EDGE_WIDTHS)+1
        ttk.Button(kf, text="Alle auswählen",
                   command=self._select_all_edges).grid(
            row=edge_btn_row, column=0,
            columnspan=2, sticky="w", padx=0, pady=(6, 2))
        ttk.Button(kf, text="Zurücksetzen",
                   command=self._reset_edges).grid(
            row=edge_btn_row, column=2,
            columnspan=2, sticky="w", padx=0, pady=(6, 2))

        # Benutzerdefinierte Kanten
        ttk.Separator(kf, orient="horizontal").grid(
            row=edge_btn_row+1, column=0, columnspan=4,
            sticky="ew", padx=4, pady=(8, 4))
        edge_add_row = edge_btn_row + 2
        ttk.Label(kf, text="B:", font=FONT_SM).grid(
            row=edge_add_row, column=0, sticky="e")
        self._custom_edge_w_var = tk.StringVar()
        ttk.Entry(kf, textvariable=self._custom_edge_w_var,
                  width=4, font=FONT).grid(
            row=edge_add_row, column=1, sticky="w", padx=2)
        ttk.Label(kf, text="D:", font=FONT_SM).grid(
            row=edge_add_row, column=2, sticky="e")
        self._custom_edge_t_var = tk.StringVar()
        ttk.Entry(kf, textvariable=self._custom_edge_t_var,
                  width=4, font=FONT).grid(
            row=edge_add_row, column=3, sticky="w", padx=2)
        ttk.Button(kf, text="+", width=2,
                   command=self._add_custom_edge).grid(
            row=edge_add_row, column=4, sticky="w", padx=4)

        self._custom_edge_frame = ttk.Frame(kf)
        self._custom_edge_frame.grid(
            row=edge_add_row+1, column=0, columnspan=5,
            sticky="ew", padx=0, pady=2)
        self._rebuild_custom_edges()

        # ── Vorschau ─────────────────────────────────────────────────────────
        self._section(p, "Vorschau")
        nb = ttk.Notebook(p)
        nb.pack(fill="x", padx=16, pady=(0, 8))

        # Tab Platten
        tab_b = ttk.Frame(nb)
        nb.add(tab_b, text="Platten")
        b_cols = ("id","desc","thick","supplier","supplier_id","btype","grain")
        b_heads = ("ID","Beschreibung","Stärke","Lieferant","Bestellnr.","Typ","Maserrichtung")
        b_widths = (140, 240, 60, 140, 120, 100, 100)
        self._preview_board_tree = ttk.Treeview(
            tab_b, columns=b_cols, show="headings", height=6)
        for col, head, w in zip(b_cols, b_heads, b_widths):
            self._preview_board_tree.heading(col, text=head)
            self._preview_board_tree.column(col, width=w, minwidth=40)
        b_vsb = ttk.Scrollbar(tab_b, orient="vertical",
                              command=self._preview_board_tree.yview)
        b_hsb = ttk.Scrollbar(tab_b, orient="horizontal",
                              command=self._preview_board_tree.xview)
        self._preview_board_tree.configure(
            yscrollcommand=b_vsb.set, xscrollcommand=b_hsb.set)
        b_vsb.pack(side="right", fill="y")
        b_hsb.pack(side="bottom", fill="x")
        self._preview_board_tree.pack(fill="both", expand=True)

        # Tab Kanten
        tab_e = ttk.Frame(nb)
        nb.add(tab_e, text="Kanten")
        e_cols = ("id","desc","width","thick","supplier","texture")
        e_heads = ("ID","Beschreibung","Breite","Dicke","Lieferant","Textur")
        e_widths = (160, 280, 60, 60, 140, 100)
        self._preview_edge_tree = ttk.Treeview(
            tab_e, columns=e_cols, show="headings", height=6)
        for col, head, w in zip(e_cols, e_heads, e_widths):
            self._preview_edge_tree.heading(col, text=head)
            self._preview_edge_tree.column(col, width=w, minwidth=40)
        e_vsb = ttk.Scrollbar(tab_e, orient="vertical",
                              command=self._preview_edge_tree.yview)
        e_hsb = ttk.Scrollbar(tab_e, orient="horizontal",
                              command=self._preview_edge_tree.xview)
        self._preview_edge_tree.configure(
            yscrollcommand=e_vsb.set, xscrollcommand=e_hsb.set)
        e_vsb.pack(side="right", fill="y")
        e_hsb.pack(side="bottom", fill="x")
        self._preview_edge_tree.pack(fill="both", expand=True)

        # Traces auf alle relevanten Variablen
        def _preview_trace(*a):
            self.after(50, self._rebuild_preview)
        for v in list(self.thick_vars.values()) + list(self.kante_vars.values()):
            v.trace_add("write", _preview_trace)
        for v in list(self.board_vars.values()) + list(self.edge_vars.values()):
            v.trace_add("write", _preview_trace)
        self.edge_root_var.trace_add("write", _preview_trace)
        self.root_var.trace_add("write", _preview_trace)


    # ── AGO-Auswahl ───────────────────────────────────────────────────────────

    def _on_ago_selected(self, event=None):
        label = self.ago_combo.get()
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
        ago_root = os.path.dirname(os.path.dirname(path))
        self.ago_path_var.set(ago_root)
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
        # Combobox aktualisieren
        values = list(self.ago_combo["values"]) + [label]
        self.ago_combo["values"] = values
        self.ago_var.set(label)

    # ── Blitz ─────────────────────────────────────────────────────────────────

    def _fill_from_root(self):
        root = self.root_var.get().strip()
        if not root:
            messagebox.showwarning("Wurzelname fehlt",
                "Bitte zuerst einen Wurzelnamen eingeben.")
            return
        d = derive_all(root)
        self.board_vars["item_no"].set(d["item_no"])
        self.board_vars["supplier_id"].set(d["supplier_id"])
        self.board_vars["description"].set(d["description"])
        self.board_vars["group"].set(d["group_label"])
        self.board_vars["cov1_tex"].set(d["decor"])
        self.board_vars["cov2_tex"].set(d["decor"])
        self.edge_vars["edge_texture"].set(d["decor"])
        # Kanten-Wurzelname ableiten
        edge_root = re.sub(r'^Dekorspanplatte' + r'\s+', 'Sicherheitskante ABS ', root)
        self.edge_root_var.set(edge_root)

    # ── Benutzerdefinierte Stärken ───────────────────────────────────────────

    def _rebuild_custom_thick(self):
        for w in self._custom_thick_frame.winfo_children():
            w.destroy()
        self._custom_thick_vars = {}
        for i, t in enumerate(self._custom["thicknesses"]):
            var = tk.BooleanVar(value=False)
            var.trace_add("write", lambda *a: self.after(50, self._rebuild_preview))
            self._custom_thick_vars[t] = var
            row = i // 2
            col = i % 2
            f = ttk.Frame(self._custom_thick_frame)
            f.grid(row=row, column=col, sticky="w", padx=4, pady=1)
            ttk.Checkbutton(f, text="{} mm".format(t),
                            variable=var).pack(side="left")
            ttk.Button(f, text="×", width=2,
                       command=lambda t=t: self._del_custom_thick(t)
                       ).pack(side="left", padx=(2, 0))

    def _add_custom_thick(self):
        val = self._custom_thick_var.get().strip()
        try:
            t = float(val)
            if t <= 0: raise ValueError
        except ValueError:
            messagebox.showwarning("Ungültig",
                "Bitte eine positive Zahl eingeben.")
            return
        # Normalisieren: ganze Zahlen ohne .0
        t = int(t) if t == int(t) else t
        if t in BOARD_THICKNESSES or t in self._custom["thicknesses"]:
            messagebox.showwarning("Bereits vorhanden",
                "{} mm ist bereits in der Liste.".format(t))
            return
        self._custom["thicknesses"].append(t)
        save_custom(self._custom)
        self._custom_thick_var.set("")
        self._rebuild_custom_thick()

    def _del_custom_thick(self, t):
        self._custom["thicknesses"].remove(t)
        save_custom(self._custom)
        self._rebuild_custom_thick()

    # ── Benutzerdefinierte Kanten ─────────────────────────────────────────────

    def _rebuild_custom_edges(self):
        for w in self._custom_edge_frame.winfo_children():
            w.destroy()
        self._custom_edge_vars = {}
        for i, (ew, et) in enumerate(self._custom["edges"]):
            var = tk.BooleanVar(value=False)
            var.trace_add("write", lambda *a: self.after(50, self._rebuild_preview))
            self._custom_edge_vars[(ew, et)] = var
            ts = str(int(et)) if et == int(et) else str(et)
            label = "{}×{} mm".format(ew, ts)
            f = ttk.Frame(self._custom_edge_frame)
            f.grid(row=i // 2, column=i % 2, sticky="w", padx=4, pady=1)
            ttk.Checkbutton(f, text=label, variable=var).pack(side="left")
            ttk.Button(f, text="×", width=2,
                       command=lambda e=(ew,et): self._del_custom_edge(e)
                       ).pack(side="left", padx=(2, 0))

    def _add_custom_edge(self):
        try:
            # Komma als Dezimaltrennzeichen erlauben
            ew = float(self._custom_edge_w_var.get().strip().replace(",", "."))
            et = float(self._custom_edge_t_var.get().strip().replace(",", "."))
            if ew <= 0 or et <= 0: raise ValueError
        except ValueError:
            messagebox.showwarning("Ungültig",
                "Bitte Breite und Dicke als positive Zahlen eingeben.")
            return
        ew = int(ew) if ew == int(ew) else ew
        et = int(et) if et == int(et) else et
        if (ew, et) in [(w, t) for w in EDGE_WIDTHS
                        for t in EDGE_THICKNESSES]:
            messagebox.showwarning("Bereits vorhanden",
                "{}×{} mm ist bereits in der Liste.".format(ew, et))
            return
        if [ew, et] in self._custom["edges"] or            (ew, et) in [tuple(e) for e in self._custom["edges"]]:
            messagebox.showwarning("Bereits vorhanden",
                "{}×{} mm ist bereits in der Liste.".format(ew, et))
            return
        self._custom["edges"].append([ew, et])
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

    def _update_coating_fields(self, btype_val):
        """Sperrt/entsperrt Beschichtungsfelder je nach Materialtyp."""
        editable = (btype_val == "melamine")
        for key in ["cov1_thick", "cov2_thick", "cov1_tex", "cov2_tex"]:
            entry = self.board_entries.get(key)
            if entry:
                entry.config(state="normal" if editable else "readonly")
            lbl = getattr(self, "_coating_labels", {}).get(key)
            if lbl:
                lbl.config(foreground="" if editable else "gray")

    def _fill_edge_from_root(self):
        root = self.edge_root_var.get().strip()
        if not root:
            messagebox.showwarning("Wurzelname fehlt",
                "Bitte zuerst einen Kanten-Wurzelnamen eingeben.")
            return
        decor = extract_decor_code(root)
        struct = extract_structure(root)
        self.edge_vars["edge_texture"].set(decor)
        # ID-Stamm ableiten: Ka-U570-ST9
        if struct:
            edge_id = "Ka-{}-{}".format(decor, struct)
        else:
            edge_id = "Ka-{}".format(decor)
        self.edge_vars["edge_item_no"].set(edge_id)

    # ── Checkboxen ────────────────────────────────────────────────────────────

    def _select_all_thick(self):
        for v in self.thick_vars.values(): v.set(True)
        self._rebuild_preview()

    def _select_all_edges(self):
        for v in self.kante_vars.values(): v.set(True)
        self._rebuild_preview()

    def _reset_all(self):
        defaults = {
            "supplier": "Holz Hahn GmbH - Krefeld",
            "price": "0", "unit": "m2", "amount": "1",
            "waste": "25", "markup": "0", "group": "",
            "grain": "length", "btype": "melamine",
            "cov1_thick": "1", "cov2_thick": "1",
            "texture": "Spanplatte",
        }
        for key, var in self.board_vars.items():
            var.set(defaults.get(key, ""))
        _grain_display = {"length": "Längs", "width": "Quer", "none": "Keine"}
        _btype_display = {
            "melamine": "Fertig beschichtet", "veneer": "Fertig furniert",
            "gw": "Leimholz", "3l": "3-Schichtplatte", "solid": "Massiv",
            "glass": "Glas", "steel": "Stahl", "custom": "Standard",
        }
        self.board_entries["grain"].set(_grain_display.get(defaults["grain"], ""))
        self.board_entries["btype"].set(_btype_display.get(defaults["btype"], ""))
        self._update_coating_fields(defaults["btype"])
        self.root_var.set("")
        self.edge_root_var.set("")
        for key, var in self.edge_vars.items():
            if key == "edge_supplier":
                var.set("Holz Hahn GmbH - Krefeld")
            elif key == "edge_waste":
                var.set("10")
            else:
                var.set("")
        self._reset_thick()
        self._reset_edges()


    def _reset_thick(self):
        for v in self.thick_vars.values(): v.set(False)
        self._rebuild_preview()

    def _reset_edges(self):
        for v in self.kante_vars.values(): v.set(False)
        self._rebuild_preview()

    def _rebuild_preview(self):
        """Aktualisiert die Vorschau-Tabellen."""
        if not hasattr(self, "_preview_board_tree"):
            return

        bv = self.board_vars
        item_no     = bv.get("item_no", tk.StringVar()).get().strip()
        description = bv.get("description", tk.StringVar()).get().strip()
        supplier    = bv.get("supplier", tk.StringVar()).get().strip()
        supplier_id = bv.get("supplier_id", tk.StringVar()).get().strip()
        group_label = bv.get("group", tk.StringVar()).get().strip()
        grain       = bv.get("grain", tk.StringVar()).get().strip()
        btype       = bv.get("btype", tk.StringVar()).get().strip()

        ev = self.edge_vars
        edge_root      = self.edge_root_var.get().strip()
        edge_texture   = ev.get("edge_texture", tk.StringVar()).get().strip()
        edge_supplier  = ev.get("edge_supplier", tk.StringVar()).get().strip()
        edge_item_base = ev.get("edge_item_no", tk.StringVar()).get().strip()

        # Übersetzungstabellen
        _grain_map = {"length": "Längs", "width": "Quer", "none": "Keine"}
        _type_map  = {
            "melamine": "Fertig beschichtet", "veneer": "Fertig furniert",
            "gw": "Leimholz", "3l": "3-Schichtplatte", "solid": "Massiv",
            "glass": "Glas", "steel": "Stahl", "custom": "Standard",
        }

        # Platten-Vorschau
        self._preview_board_tree.delete(*self._preview_board_tree.get_children())
        all_thick = dict(self.thick_vars)
        all_thick.update(getattr(self, "_custom_thick_vars", {}))
        for t in sorted(all_thick.keys()):
            if all_thick[t].get():
                ni = replace_thickness_in_item_no(item_no, t) if item_no else "–"
                nd = replace_thickness_in_name(description, t) if description else "–"
                ns = replace_thickness_in_item_no(supplier_id, t) if supplier_id else "–"
                self._preview_board_tree.insert("", "end", values=(
                    ni, nd, t, supplier or "–", ns,
                    _type_map.get(btype, btype) or "–",
                    _grain_map.get(grain, grain) or "–"))

        # Kanten-Vorschau
        self._preview_edge_tree.delete(*self._preview_edge_tree.get_children())
        all_kante = dict(self.kante_vars)
        all_kante.update(getattr(self, "_custom_edge_vars", {}))
        for (ew, et), var in sorted(all_kante.items()):
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
                self._preview_edge_tree.insert("", "end", values=(
                    ei, ed, ew, ts, edge_supplier or "–", edge_texture or "–"))

    # ── Schreiben ─────────────────────────────────────────────────────────────

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

        bv = self.board_vars
        ev = self.edge_vars

        item_no     = bv["item_no"].get().strip()
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

        edge_supplier    = ev["edge_supplier"].get().strip()
        edge_waste       = ev["edge_waste"].get().strip()
        edge_texture     = ev["edge_texture"].get().strip()
        edge_item_base   = ev.get("edge_item_no", tk.StringVar()).get().strip()
        edge_root        = self.edge_root_var.get().strip()
        group            = bv.get("group", tk.StringVar()).get().strip() or derive_group(item_no)

        if not item_no:
            messagebox.showwarning("Fehlende Daten",
                "Bitte zuerst den Wurzelnamen eingeben und ⚡ klicken.")
            return

        existing_boards = load_existing_ids(boards_file)
        existing_edges  = load_existing_ids(edges_file)

        board_lines = []; edge_lines = []
        skipped_b   = []; skipped_e  = []

        # Standard + benutzerdefinierte Stärken zusammenführen
        all_thick_vars = dict(self.thick_vars)
        all_thick_vars.update(getattr(self, "_custom_thick_vars", {}))

        for t in sorted(all_thick_vars.keys()):
            if all_thick_vars[t].get():
                ni = replace_thickness_in_item_no(item_no, t)
                # Basis-Platte: item_no direkt mit korrekter Dicke t verwenden
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

        all_kante_vars = dict(self.kante_vars)
        all_kante_vars.update(getattr(self, "_custom_edge_vars", {}))

        for (ew, et), var in sorted(all_kante_vars.items()):
            if var.get():
                # Eigenen ID-Stamm nutzen wenn vorhanden, sonst aus Platten-ID ableiten
                if edge_item_base:
                    ts = str(int(et)) if et == int(et) else str(et)
                    ei = "{}-{}x{}".format(edge_item_base, ew, ts)
                else:
                    ei = make_edge_item_no(item_no, ew, et)
                # Kanten-Beschreibung aus edge_root ableiten falls vorhanden
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
            for s in skipped_b: msg += "  Platte: {}\n".format(s)
            for s in skipped_e: msg += "  Kante:  {}\n".format(s)
        messagebox.showinfo("Fertig", msg)

    def _open_boards_table(self):
        boards_file = self.boards_path.get().strip()
        if not boards_file or not os.path.isfile(boards_file):
            messagebox.showerror("Fehler",
                "Bitte zuerst einen AGO auswählen.")
            return
        BoardsTable(self, boards_file)

    def _open_edges_table(self):
        edges_file = self.edges_path.get().strip()
        if not edges_file or not os.path.isfile(edges_file):
            messagebox.showerror("Fehler",
                "Bitte zuerst einen AGO auswählen.")
            return
        EdgesTable(self, edges_file)


# ── Boards Tabellenansicht ───────────────────────────────────────────────────

BOARD_COLUMNS = [
    ("item_no",     "ID",                   120),
    ("description", "Bezeichnung",          220),
    ("supplier",    "Lieferant",            140),
    ("supplier_id", "Bestellnummer",        130),
    ("price",       "Preis",                60),
    ("unit",        "Einheit",              60),
    ("amount",      "Menge",                60),
    ("waste",       "Verschnitt",           80),
    ("markup",      "Aufschlag",            80),
    ("length",      "Länge",                60),
    ("width",       "Breite",               60),
    ("thickness",   "Stärke",               60),
    ("group",       "Gruppe",               110),
    ("texture",     "Textur",               80),
    ("def_thick",   "Std. Stärke",          80),
    ("grain",       "Maserrichtung",        100),
    ("btype",       "Typ",                  120),
    ("cov1_thick",  "Besch. 1 (mm)",        90),
    ("cov2_thick",  "Besch. 2 (mm)",        90),
    ("cov1_tex",    "Textur Besch. 1",      110),
    ("cov2_tex",    "Textur Besch. 2",      110),
]

def parse_boards(filepath):
    """Liest Boards.txt und gibt Liste von Dicts zurück."""
    rows = []
    try:
        with codecs.open(filepath, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.rstrip("\r\n")
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                while len(parts) < 21:
                    parts.append("")
                rows.append({
                    "item_no":     parts[0],
                    "description": parts[1],
                    "supplier":    parts[2],
                    "supplier_id": parts[3],
                    "price":       parts[4],
                    "unit":        parts[5],
                    "amount":      parts[6],
                    "waste":       parts[7],
                    "markup":      parts[8],
                    "length":      parts[9],
                    "width":       parts[10],
                    "thickness":   parts[11],
                    "group":       parts[12],
                    "texture":     parts[13],
                    "def_thick":   parts[14],
                    "grain":       parts[15],
                    "btype":       parts[16],
                    "cov1_thick":  parts[17],
                    "cov2_thick":  parts[18],
                    "cov1_tex":    parts[19],
                    "cov2_tex":    parts[20],
                })
    except Exception as e:
        messagebox.showerror("Fehler", "Boards.txt konnte nicht gelesen werden:\n" + str(e))
    return rows

def write_boards(filepath, rows):
    """Schreibt Liste von Dicts zurück in Boards.txt."""
    header = "#Item-No\tDescription\tSupplier\tSupplier ID\tPrice\tUnit\t" \
             "Amount per unit\tWaste\tMark - Up\tLength\tWidth\tThickness\t" \
             "Group\tTexture\tDefault Thickness\tGrain\tType\t" \
             "Included Covering1 Thickness\tIncluded Covering2 Thickness\t" \
             "Included Covering1 Texture\tIncluded Covering2 Texture"
    tmp = filepath + ".tmp"
    try:
        if os.path.exists(filepath):
            shutil.copy2(filepath, filepath + ".bak")
        with codecs.open(tmp, "w", encoding="utf-8") as f:
            f.write(header)
            for r in rows:
                line = "\t".join([
                    r["item_no"], r["description"], r["supplier"], r["supplier_id"],
                    r["price"], r["unit"], r["amount"], r["waste"], r["markup"],
                    r["length"], r["width"], r["thickness"], r["group"], r["texture"],
                    r["def_thick"], r["grain"], r["btype"],
                    r["cov1_thick"], r["cov2_thick"], r["cov1_tex"], r["cov2_tex"],
                ])
                f.write("\n" + line)
        os.replace(tmp, filepath)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


class EditDialog(tk.Toplevel):
    """Dialog zum Bearbeiten eines Boards-Eintrags."""

    GRAIN_OPTIONS = [("Längs","length"),("Quer","width"),("Keine","none")]
    TYPE_OPTIONS  = [
        ("Fertig beschichtet","melamine"),("Fertig furniert","veneer"),
        ("Leimholz","gw"),("3-Schichtplatte","3l"),("Massiv","solid"),
        ("Glas","glass"),("Stahl","steel"),("Standard","custom"),
    ]

    def __init__(self, parent, row_data, on_save):
        super().__init__(parent)
        self.title("Eintrag bearbeiten")
        self.resizable(True, True)
        self.grab_set()
        self._data    = dict(row_data)
        self._on_save = on_save
        self._vars    = {}
        self._build()
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = min(1100, sw - 40)
        h = min(int(sh * 0.9), sh - 80)
        self.geometry("{}x{}+{}+{}".format(
            w, h, (sw - w) // 2, (sh - h) // 2))

    def _build(self):
        fields = [
            ("ID",                   "item_no",    False),
            ("Bezeichnung",          "description",False),
            ("Lieferant",            "supplier",   False),
            ("Bestellnummer",        "supplier_id",False),
            ("Preis",                "price",      False),
            ("Einheit",              "unit",       False),
            ("Menge/Einheit",        "amount",     False),
            ("Verschnitt (%)",       "waste",      False),
            ("Aufschlag",            "markup",     False),
            ("Stärke (mm)",          "thickness",  False),
            ("Gruppe",               "group",      False),
            ("Textur (Platte)",      "texture",    False),
            ("Std. Stärke",          "def_thick",  False),
            ("Maserrichtung",        "grain",      True),
            ("Materialtyp",          "btype",      True),
            ("Beschichtung 1 (mm)",  "cov1_thick", False),
            ("Beschichtung 2 (mm)",  "cov2_thick", False),
            ("Textur Beschichtung 1","cov1_tex",   False),
            ("Textur Beschichtung 2","cov2_tex",   False),
        ]
        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both")

        for i, (label, key, is_dropdown) in enumerate(fields):
            ttk.Label(frm, text=label, font=FONT_SM, width=20,
                      anchor="w").grid(row=i, column=0, sticky="w",
                                       padx=(0,10), pady=3)
            var = tk.StringVar(value=self._data.get(key, ""))
            self._vars[key] = var

            if key == "grain":
                dvals = [o[0] for o in self.GRAIN_OPTIONS]
                ivals = [o[1] for o in self.GRAIN_OPTIONS]
                dvar  = tk.StringVar()
                try:
                    dvar.set(dvals[ivals.index(var.get())])
                except ValueError:
                    dvar.set(dvals[0])
                cb = ttk.Combobox(frm, textvariable=dvar,
                                  values=dvals, state="readonly",
                                  width=28, font=FONT)
                cb.grid(row=i, column=1, sticky="ew", ipady=3, pady=3)
                def _g(v=var, iv=ivals, dv=dvals, c=cb):
                    def sel(e):
                        try: v.set(iv[dv.index(c.get())])
                        except: pass
                    return sel
                cb.bind("<<ComboboxSelected>>", _g())
            elif key == "btype":
                dvals = [o[0] for o in self.TYPE_OPTIONS]
                ivals = [o[1] for o in self.TYPE_OPTIONS]
                dvar  = tk.StringVar()
                try:
                    dvar.set(dvals[ivals.index(var.get())])
                except ValueError:
                    dvar.set(dvals[0])
                cb = ttk.Combobox(frm, textvariable=dvar,
                                  values=dvals, state="readonly",
                                  width=28, font=FONT)
                cb.grid(row=i, column=1, sticky="ew", ipady=3, pady=3)
                def _t(v=var, iv=ivals, dv=dvals, c=cb):
                    def sel(e):
                        try: v.set(iv[dv.index(c.get())])
                        except: pass
                    return sel
                cb.bind("<<ComboboxSelected>>", _t())
            else:
                ttk.Entry(frm, textvariable=var, width=32,
                          font=FONT).grid(row=i, column=1, sticky="ew",
                                          ipady=3, pady=3)

        # Buttons
        ttk.Separator(frm, orient="horizontal").grid(
            row=len(fields), column=0, columnspan=2,
            sticky="ew", pady=(12, 0))
        bf = ttk.Frame(frm)
        bf.grid(row=len(fields)+1, column=0, columnspan=2,
                sticky="ew", pady=(8, 0))
        ttk.Button(bf, text="Abbrechen",
                   command=self.destroy).pack(side="left")
        ttk.Button(bf, text="Übernehmen",
                   command=self._save).pack(side="right")

    def _save(self):
        for key, var in self._vars.items():
            self._data[key] = var.get().strip()
        self._on_save(self._data)
        self.destroy()


class BoardsTable(tk.Toplevel):
    """Fenster mit Tabellenansicht der Boards.txt."""

    def __init__(self, parent, filepath):
        super().__init__(parent)
        self.title("Platten verwalten – {}".format(
            os.path.basename(filepath)))
        self.filepath = filepath
        self._rows    = parse_boards(filepath)
        self._pending = []   # geänderte/gelöschte Einträge
        self._build()
        self.geometry("1200x600")
        # Haupt-Scroll deaktivieren solange dieses Fenster offen ist
        parent.unbind_all("<MouseWheel>")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._parent = parent
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry("+{}+{}".format(
            (sw - 1200) // 2,
            (sh - 600)  // 2))

    def _build(self):
        # Toolbar
        bar = ttk.Frame(self, padding=(8, 6))
        bar.pack(fill="x")
        ttk.Button(bar, text="Bearbeiten",
                   command=self._edit_selected).pack(side="left", padx=(0,4))
        ttk.Button(bar, text="Duplizieren",
                   command=self._duplicate_selected).pack(side="left", padx=(0,4))
        ttk.Button(bar, text="Entfernen",
                   command=self._delete_selected).pack(side="left", padx=(0,4))

        # Suchfeld
        ttk.Label(bar, text="Suche:", font=FONT_SM).pack(
            side="left", padx=(20, 4))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._apply_filter())
        ttk.Entry(bar, textvariable=self._search_var,
                  width=24, font=FONT).pack(side="left")

        ttk.Button(bar, text="💾  Speichern",
                   command=self._save).pack(side="right")

        # Treeview
        cols = [c[0] for c in BOARD_COLUMNS]
        self._tree = ttk.Treeview(self, columns=cols,
                                  show="headings", selectmode="extended")
        for key, label, width in BOARD_COLUMNS:
            self._tree.heading(key, text=label,
                               command=lambda k=key: self._sort(k))
            self._tree.column(key, width=width, minwidth=40)

        vsb = ttk.Scrollbar(self, orient="vertical",
                            command=self._tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal",
                            command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set,
                             xscrollcommand=hsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")

        self._tree.bind("<Double-1>", lambda e: self._edit_selected())
        self._populate()

    def _populate(self, rows=None):
        self._tree.delete(*self._tree.get_children())
        display = self._rows if rows is None else rows
        for r in display:
            vals = [r.get(c[0], "") for c in BOARD_COLUMNS]
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
                "Bitte zuerst eine Zeile auswählen.")
            return None
        iid = sel[0]
        for r in self._rows:
            if r["item_no"] == iid:
                return r
        return None

    def _selected_rows(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Keine Auswahl",
                "Bitte zuerst eine oder mehrere Zeilen auswählen.")
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
        EditDialog(self, row, on_save)

    def _duplicate_selected(self):
        row = self._selected_row()
        if not row:
            return
        copy = dict(row)
        copy["item_no"] = row["item_no"] + "_Kopie"
        def on_save(updated):
            self._rows.append(updated)
            self._apply_filter()
        EditDialog(self, copy, on_save)

    def _delete_selected(self):
        rows = self._selected_rows()
        if not rows:
            return
        if len(rows) == 1:
            msg = 'Eintrag "{}" wirklich löschen?'.format(rows[0]["item_no"])
        else:
            msg = '{} Einträge wirklich löschen?'.format(len(rows))
        if not messagebox.askyesno("Löschen bestätigen", msg):
            return
        ids = {r["item_no"] for r in rows}
        self._rows = [r for r in self._rows if r["item_no"] not in ids]
        self._apply_filter()

    def _on_close(self):
        self._parent.bind_all("<MouseWheel>",
            self._parent._scroll_handler)
        self.destroy()

    def _save(self):
        if not messagebox.askyesno(
                "Speichern bestätigen",
                "Alle Änderungen in Boards.txt schreiben?"):
            return
        try:
            write_boards(self.filepath, self._rows)
            messagebox.showinfo("Gespeichert",
                "Boards.txt wurde erfolgreich gespeichert.")
        except Exception as e:
            messagebox.showerror("Fehler", str(e))


# ── Edges Tabellenansicht ────────────────────────────────────────────────────

EDGE_COLUMNS = [
    ("item_no",      "ID",              140),
    ("description",  "Bezeichnung",     260),
    ("supplier",     "Lieferant",       150),
    ("supplier_id",  "Bestellnummer",   140),
    ("price",        "Preis",            60),
    ("unit",         "Einheit",          60),
    ("amount",       "Menge",            60),
    ("waste",        "Verschnitt",       80),
    ("markup",       "Aufschlag",        80),
    ("length",       "Länge",            60),
    ("width",        "Breite",           60),
    ("thickness",    "Dicke",            60),
    ("group",        "Gruppe",          100),
    ("texture",      "Textur",          100),
    ("def_thick",    "Std. Dicke",       80),
    ("grain",        "Maserrichtung",   100),
    ("btype",        "Typ",             100),
    ("cov1_thick",   "Besch. 1 (mm)",   90),
    ("cov2_thick",   "Besch. 2 (mm)",   90),
    ("cov1_tex",     "Textur Besch. 1", 110),
    ("cov2_tex",     "Textur Besch. 2", 110),
]

def parse_edges(filepath):
    rows = []
    try:
        with codecs.open(filepath, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.rstrip("\r\n")
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                while len(parts) < 21:
                    parts.append("")
                rows.append({
                    "item_no":     parts[0],
                    "description": parts[1],
                    "supplier":    parts[2],
                    "supplier_id": parts[3],
                    "price":       parts[4],
                    "unit":        parts[5],
                    "amount":      parts[6],
                    "waste":       parts[7],
                    "markup":      parts[8],
                    "length":      parts[9],
                    "width":       parts[10],
                    "thickness":   parts[11],
                    "group":       parts[12],
                    "texture":     parts[13],
                    "def_thick":   parts[14],
                    "grain":       parts[15],
                    "btype":       parts[16],
                    "cov1_thick":  parts[17],
                    "cov2_thick":  parts[18],
                    "cov1_tex":    parts[19],
                    "cov2_tex":    parts[20],
                })
    except Exception as e:
        messagebox.showerror("Fehler",
            "Edges.txt konnte nicht gelesen werden:\n" + str(e))
    return rows

def write_edges(filepath, rows):
    header = "#Item-No\tDescription\tSupplier\tSupplier ID\tPrice\tUnit\t" \
             "Amount per unit\tWaste\tMark - Up\tLength\tWidth\tThickness\t" \
             "Group\tTexture\tDefault Thickness\tGrain\tType\t" \
             "Included Covering1 Thickness\tIncluded Covering2 Thickness\t" \
             "Included Covering1 Texture\tIncluded Covering2 Texture"
    tmp = filepath + ".tmp"
    try:
        if os.path.exists(filepath):
            shutil.copy2(filepath, filepath + ".bak")
        with codecs.open(tmp, "w", encoding="utf-8") as f:
            f.write(header)
            for r in rows:
                line = "\t".join([
                    r["item_no"], r["description"], r["supplier"], r["supplier_id"],
                    r["price"], r["unit"], r["amount"], r["waste"], r["markup"],
                    r["length"], r["width"], r["thickness"], r["group"], r["texture"],
                    r["def_thick"], r["grain"], r["btype"],
                    r["cov1_thick"], r["cov2_thick"], r["cov1_tex"], r["cov2_tex"],
                ])
                f.write("\n" + line)
        os.replace(tmp, filepath)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


class EdgeEditDialog(tk.Toplevel):
    """Dialog zum Bearbeiten eines Edges-Eintrags."""

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
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry("+{}+{}".format(
            (sw - self.winfo_width())  // 2,
            (sh - self.winfo_height()) // 2))

    def _build(self):
        fields = [
            ("ID",               "item_no"),
            ("Bezeichnung",      "description"),
            ("Lieferant",        "supplier"),
            ("Bestellnummer",    "supplier_id"),
            ("Preis",            "price"),
            ("Einheit",          "unit"),
            ("Menge/Einheit",    "amount"),
            ("Verschnitt (%)",   "waste"),
            ("Aufschlag",        "markup"),
            ("Breite (mm)",      "width"),
            ("Dicke (mm)",       "thickness"),
            ("Textur",           "texture"),
        ]
        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both")

        for i, (label, key) in enumerate(fields):
            ttk.Label(frm, text=label, font=FONT_SM, width=18,
                      anchor="w").grid(row=i, column=0, sticky="w",
                                       padx=(0, 10), pady=3)
            var = tk.StringVar(value=self._data.get(key, ""))
            self._vars[key] = var
            ttk.Entry(frm, textvariable=var, width=32,
                      font=FONT).grid(row=i, column=1, sticky="ew",
                                      ipady=3, pady=3)

        ttk.Separator(frm, orient="horizontal").grid(
            row=len(fields), column=0, columnspan=2,
            sticky="ew", pady=(12, 0))
        bf = ttk.Frame(frm)
        bf.grid(row=len(fields)+1, column=0, columnspan=2,
                sticky="ew", pady=(8, 0))
        ttk.Button(bf, text="Abbrechen",
                   command=self.destroy).pack(side="left")
        ttk.Button(bf, text="Übernehmen",
                   command=self._save).pack(side="right")

    def _save(self):
        for key, var in self._vars.items():
            self._data[key] = var.get().strip()
        self._on_save(self._data)
        self.destroy()


class EdgesTable(tk.Toplevel):
    """Fenster mit Tabellenansicht der Edges.txt."""

    def __init__(self, parent, filepath):
        super().__init__(parent)
        self.title("Kanten verwalten – {}".format(
            os.path.basename(filepath)))
        self.filepath  = filepath
        self._rows     = parse_edges(filepath)
        self._build()
        self.geometry("1200x600")
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry("+{}+{}".format(
            (sw - 1200) // 2,
            (sh - 600)  // 2))
        # Haupt-Scroll deaktivieren
        parent.unbind_all("<MouseWheel>")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._parent = parent

    def _build(self):
        bar = ttk.Frame(self, padding=(8, 6))
        bar.pack(fill="x")
        ttk.Button(bar, text="Bearbeiten",
                   command=self._edit_selected).pack(side="left", padx=(0, 4))
        ttk.Button(bar, text="Duplizieren",
                   command=self._duplicate_selected).pack(side="left", padx=(0, 4))
        ttk.Button(bar, text="Entfernen",
                   command=self._delete_selected).pack(side="left", padx=(0, 4))

        ttk.Label(bar, text="Suche:", font=FONT_SM).pack(
            side="left", padx=(20, 4))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._apply_filter())
        ttk.Entry(bar, textvariable=self._search_var,
                  width=24, font=FONT).pack(side="left")

        ttk.Button(bar, text="💾  Speichern",
                   command=self._save).pack(side="right")

        cols = [c[0] for c in EDGE_COLUMNS]
        self._tree = ttk.Treeview(self, columns=cols,
                                  show="headings", selectmode="extended")
        for key, label, width in EDGE_COLUMNS:
            self._tree.heading(key, text=label,
                               command=lambda k=key: self._sort(k))
            self._tree.column(key, width=width, minwidth=40)

        vsb = ttk.Scrollbar(self, orient="vertical",
                            command=self._tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal",
                            command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set,
                             xscrollcommand=hsb.set)
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
                "Bitte zuerst eine Zeile auswählen.")
            return None
        iid = sel[0]
        for r in self._rows:
            if r["item_no"] == iid:
                return r
        return None

    def _selected_rows(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Keine Auswahl",
                "Bitte zuerst eine oder mehrere Zeilen auswählen.")
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
        if len(rows) == 1:
            msg = 'Eintrag "{}" wirklich löschen?'.format(rows[0]["item_no"])
        else:
            msg = '{} Einträge wirklich löschen?'.format(len(rows))
        if not messagebox.askyesno("Löschen bestätigen", msg):
            return
        ids = {r["item_no"] for r in rows}
        self._rows = [r for r in self._rows if r["item_no"] not in ids]
        self._apply_filter()

    def _on_close(self):
        self._parent.bind_all("<MouseWheel>",
            self._parent._scroll_handler)
        self.destroy()

    def _save(self):
        if not messagebox.askyesno(
                "Speichern bestätigen",
                "Alle Änderungen in Edges.txt schreiben?"):
            return
        try:
            write_edges(self.filepath, self._rows)
            messagebox.showinfo("Gespeichert",
                "Edges.txt wurde erfolgreich gespeichert.")
        except Exception as e:
            messagebox.showerror("Fehler", str(e))


if __name__ == "__main__":
    app = App()
    app.mainloop()
