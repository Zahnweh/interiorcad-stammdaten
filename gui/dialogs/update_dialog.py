import tkinter as tk
from tkinter import ttk
from gui.theme import FONT_SM


class UpdateDialog(tk.Toplevel):
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
        self.geometry("+{}+{}".format(
            (sw - self.winfo_width()) // 2,
            (sh - self.winfo_height()) // 2))

    def _cancel(self):
        self.cancelled = True
        self.destroy()

    def set_progress(self, pct, text):
        if self.winfo_exists():
            self._bar["value"] = pct
            self._lbl.config(text=text)
            self.update_idletasks()
