import os, sys, platform, shutil, tempfile
from tkinter import messagebox

from core.constants import VERSION, GITHUB_REPO

IS_MAC     = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"


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


def _check_for_updates(app, silent=True):
    import urllib.request, json as _json, ssl
    try:
        url = "https://api.github.com/repos/{}/releases/latest".format(GITHUB_REPO)
        req = urllib.request.Request(
            url, headers={"User-Agent": "interiorcad-Stammdaten/{}".format(VERSION)})
        ctx = ssl.create_default_context()
        if getattr(sys, "frozen", False) and IS_MAC:
            for _p in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
                if os.path.exists(_p):
                    ctx = ssl.create_default_context(cafile=_p)
                    break
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            data = _json.loads(resp.read().decode())
        tag = data.get("tag_name", "")
        ver = tag.lstrip("v")
        if ver and _ver_tuple(ver) > _ver_tuple(VERSION):
            app.after(0, lambda: _offer_update(app, data))
        elif not silent:
            app.after(0, lambda: messagebox.showinfo(
                "Kein Update verfügbar",
                "Sie verwenden bereits die aktuelle Version (v{}).".format(VERSION),
                parent=app))
    except Exception as e:
        if not silent:
            app.after(0, lambda err=str(e): messagebox.showerror(
                "Update-Prüfung fehlgeschlagen",
                "Verbindung konnte nicht hergestellt werden:\n{}".format(err),
                parent=app))


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


def _run_download(app, url, tag):
    import urllib.request, threading
    from gui.dialogs.update_dialog import UpdateDialog
    dlg    = UpdateDialog(app)
    suffix = ".zip" if IS_MAC else ".exe"

    def _worker():
        tmp = tempfile.mktemp(suffix=suffix)
        try:
            def _progress(count, block, total):
                if dlg.cancelled:
                    raise Exception("Abgebrochen")
                if total > 0:
                    pct      = min(100, count * block * 100 // total)
                    done_mb  = count * block / 1_048_576
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
                messagebox.showinfo(
                    "Update bereit",
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
            messagebox.showinfo(
                "Update wird installiert",
                "Die App wird jetzt beendet und neu gestartet.",
                parent=app)
            app.destroy()
            sys.exit(0)

        elif IS_WINDOWS:
            if not app_path:
                dst = os.path.join(os.path.expanduser("~/Downloads"),
                                   os.path.basename(tmp_path))
                shutil.copy2(tmp_path, dst)
                os.remove(tmp_path)
                messagebox.showinfo(
                    "Update bereit",
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
        messagebox.showerror(
            "Installations-Fehler",
            "Automatische Installation fehlgeschlagen:\n{}\n\n"
            "Heruntergeladene Datei:\n{}".format(e, tmp_path),
            parent=app)
