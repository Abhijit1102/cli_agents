import threading


class ThemeManager:
    THEMES = {
        "cyan":   {"primary": "#00f5ff", "dim": "#007a80", "accent": "#bf5fff", "success": "#39ff14", "warn": "#ffe600"},
        "green":  {"primary": "#39ff14", "dim": "#145c14", "accent": "#00f5ff", "success": "#ffe600", "warn": "#ff6b35"},
        "purple": {"primary": "#bf5fff", "dim": "#4b1f73", "accent": "#ff2079", "success": "#39ff14", "warn": "#ffe600"},
        "yellow": {"primary": "#ffe600", "dim": "#7a6f00", "accent": "#ff6b35", "success": "#39ff14", "warn": "#ff2079"},
        "orange": {"primary": "#ff6b35", "dim": "#7a2f14", "accent": "#ffe600", "success": "#39ff14", "warn": "#ff2079"},
        "pink":   {"primary": "#ff2079", "dim": "#7a0033", "accent": "#bf5fff", "success": "#39ff14", "warn": "#ffe600"},
        "white":  {"primary": "#ffffff", "dim": "#aaaaaa", "accent": "#00f5ff", "success": "#39ff14", "warn": "#ffe600"},
    }

    SHIFT_FRAMES = {
        "cyan":   ["#00f5ff", "#bf5fff", "#39ff14", "#ffe600", "#ff2079", "#ff6b35"],
        "green":  ["#39ff14", "#00f5ff", "#ffe600", "#bf5fff", "#ff6b35", "#39ff14"],
        "purple": ["#bf5fff", "#ff2079", "#00f5ff", "#ffe600", "#39ff14", "#bf5fff"],
        "yellow": ["#ffe600", "#ff6b35", "#ff2079", "#00f5ff", "#bf5fff", "#39ff14"],
        "orange": ["#ff6b35", "#ffe600", "#ff2079", "#bf5fff", "#00f5ff", "#39ff14"],
        "pink":   ["#ff2079", "#bf5fff", "#ffe600", "#ff6b35", "#00f5ff", "#39ff14"],
        "white":  ["#ffffff", "#aaaaaa", "#00f5ff", "#bf5fff", "#ffe600", "#39ff14"],
    }

    def __init__(self):
        self._frame = 0
        self._lock  = threading.Lock()
        self.set_theme("cyan")

    def set_theme(self, name: str) -> bool:
        t = self.THEMES.get(name.lower())
        if not t:
            return False
        self.name    = name.lower()
        self.primary = t["primary"]
        self.dim     = t["dim"]
        self.accent  = t["accent"]
        self.success = t["success"]
        self.warn    = t["warn"]
        with self._lock:
            self._frame = 0
        return True

    def next_shift(self) -> str:
        frames = self.SHIFT_FRAMES[self.name]
        with self._lock:
            c = frames[self._frame % len(frames)]
            self._frame += 1
        return c

    def list_themes(self) -> list:
        return list(self.THEMES.keys())


# Singleton — imported everywhere
THEME = ThemeManager()


# ── Color shorthand helpers (resolved at call time so /theme is instant) ──
def P()  -> str: return THEME.primary
def D()  -> str: return THEME.dim
def A()  -> str: return THEME.accent
def S()  -> str: return THEME.success
def W()  -> str: return THEME.warn
def SH() -> str: return THEME.next_shift()