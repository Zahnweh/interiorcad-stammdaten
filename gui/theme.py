"""
gui/theme.py
Platform-aware theme constants.
macOS: native aqua — no manual widget backgrounds.
Windows: explicit dark mode, all colors set.
"""
import platform

PLATFORM   = platform.system()
IS_WINDOWS = PLATFORM == "Windows"
IS_MAC     = PLATFORM == "Darwin"

FONT_FAMILY = "System" if IS_MAC else "Segoe UI"

FONT_BODY   = (FONT_FAMILY, 13)
FONT_BODY_B = (FONT_FAMILY, 13, "bold")
FONT_SM     = (FONT_FAMILY, 12)
FONT_SM_B   = (FONT_FAMILY, 12, "bold")

PAD_XS = 4
PAD_S  = 8
PAD_M  = 12
PAD_L  = 16

if IS_WINDOWS:
    BG_MAIN    = "#202020"
    BG_SURFACE = "#2B2B2B"
    BG_INPUT   = "#333333"
    FG_PRIMARY = "#F3F3F3"
    FG_SEC     = "#A8A8A8"
    FG_GRAY    = "#707070"
    BORDER     = "#404040"
else:
    # macOS: aqua handles backgrounds — don't set them manually
    BG_MAIN = BG_SURFACE = BG_INPUT = FG_PRIMARY = FG_SEC = BORDER = None
    FG_GRAY = "#888888"
