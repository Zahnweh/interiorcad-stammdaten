import codecs, os, shutil
from tkinter import messagebox
from core.constants import BOARD_COLUMNS, EDGE_COLUMNS


def tab_join(fields):
    return "\t".join([str(f) for f in fields])


def build_board_line(item_no, desc, supplier, supplier_id, price, unit,
                     amount, waste, markup, thickness, group, texture,
                     grain, btype, cov1_thick, cov2_thick, cov1_tex, cov2_tex):
    return tab_join([
        item_no, desc, supplier, supplier_id,
        price, unit, amount, waste, markup,
        0, 0, thickness,
        group, texture, thickness, grain, btype,
        cov1_thick, cov2_thick, cov1_tex, cov2_tex,
    ])


def build_edge_line(item_no, desc, supplier, supplier_id, price,
                    unit, amount, waste, markup, width, thickness, texture):
    return tab_join([
        item_no, desc, supplier, supplier_id,
        price, unit, amount, waste, markup,
        0, width, thickness,
        "IGNORE", texture, 0,
        "IGNORE", "IGNORE", 0, 0, "IGNORE", "IGNORE",
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


def parse_boards(filepath):
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
    header = (
        "#Item-No\tDescription\tSupplier\tSupplier ID\tPrice\tUnit\t"
        "Amount per unit\tWaste\tMark - Up\tLength\tWidth\tThickness\t"
        "Group\tTexture\tDefault Thickness\tGrain\tType\t"
        "Included Covering1 Thickness\tIncluded Covering2 Thickness\t"
        "Included Covering1 Texture\tIncluded Covering2 Texture"
    )
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
        messagebox.showerror("Fehler", "Edges.txt konnte nicht gelesen werden:\n" + str(e))
    return rows


def write_edges(filepath, rows):
    header = (
        "#Item-No\tDescription\tSupplier\tSupplier ID\tPrice\tUnit\t"
        "Amount per unit\tWaste\tMark - Up\tLength\tWidth\tThickness\t"
        "Group\tTexture\tDefault Thickness\tGrain\tType\t"
        "Included Covering1 Thickness\tIncluded Covering2 Thickness\t"
        "Included Covering1 Texture\tIncluded Covering2 Texture"
    )
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
