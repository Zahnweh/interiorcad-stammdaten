import os, glob, platform
import xml.etree.ElementTree as ET
from core.constants import STAMMDATEN_REL


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
        nemetschek = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Nemetschek")
        i = 0
        while True:
            try:
                vw_name = winreg.EnumKey(nemetschek, i)
                try:
                    general = winreg.OpenKey(nemetschek, vw_name + "\\General")
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

    for base in [os.path.expanduser("~/Desktop"), os.path.expanduser("~/Documents")]:
        if os.path.isdir(base):
            try:
                for entry in os.scandir(base):
                    if entry.is_dir():
                        add(entry.path)
            except PermissionError:
                pass

    return sorted([(v[0], v[1]) for v in found.values()], key=lambda x: x[0])


def find_agos_mac():
    found = {}

    def add(folder_path, label=None, overwrite=False):
        sd = os.path.join(folder_path, STAMMDATEN_REL)
        b  = os.path.join(sd, "Boards.txt")
        e  = os.path.join(sd, "Edges.txt")
        try:
            open(b, "rb").close()
            open(e, "rb").close()
        except Exception:
            return
        sd_real = os.path.realpath(sd)
        if sd_real not in found or overwrite:
            found[sd_real] = label or os.path.basename(folder_path)

    vw_base = os.path.expanduser("~/Library/Application Support/Vectorworks")
    for settings_file in glob.glob(
            os.path.join(vw_base, "*", "Einstellungen", "SavedSettingsUser.xml")):
        try:
            tree = ET.parse(settings_file)
            root = tree.getroot()
            for tag in ["WorkgroupFolderSelection", "workgroupFolderSelection", "WorkgroupFolder"]:
                el = root.find(".//" + tag)
                if el is not None and el.text:
                    _p = el.text.strip().rstrip("/")
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

    for base in [os.path.expanduser("~/Desktop"), os.path.expanduser("~/Documents")]:
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
    if platform.system() == "Windows":
        return find_agos_windows()
    else:
        return find_agos_mac()
