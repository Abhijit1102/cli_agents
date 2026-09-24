# ── directories to never descend into ─────────────────────────────────────
IGNORE_DIRS: set[str] = {
    ".git", ".hg", ".svn", "__pycache__", ".venv", "venv", "env", 
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", "htmlcov", 
    ".eggs", "node_modules", ".next", ".nuxt", ".output", ".svelte-kit", 
    ".turbo", ".parcel-cache", "dist", "build", "out", "target", "bin", 
    "obj", ".cache", ".idea", ".vscode", ".fleet", ".DS_Store", 
    "coverage", ".nyc_output", ".terraform", ".vagrant", ".sandbox",
}

IGNORE_FILES: set[str] = {
    "uv.lock", "poetry.lock", "Pipfile.lock", "package-lock.json", 
    "yarn.lock", "pnpm-lock.yaml", "Gemfile.lock", "Cargo.lock", 
    "composer.lock", ".DS_Store", "Thumbs.db", "desktop.ini", 
    "bash.exe.stackdump", "*.pyc", "*.pyo", "*.pyd",
}

IGNORE_PREFIXES: tuple[str, ...] = (".env", "~")
IGNORE_SUFFIXES: tuple[str, ...] = (
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".exe", ".o", ".a", 
    ".lib", ".class", ".jar", ".war", ".wasm", ".png", ".jpg", ".jpeg", 
    ".gif", ".ico", ".svg", ".webp", ".avif", ".mp4", ".mp3", ".wav", 
    ".ogg", ".ttf", ".otf", ".woff", ".woff2", ".eot", ".zip", ".tar", 
    ".gz", ".bz2", ".xz", ".7z", ".rar", ".db", ".sqlite", ".sqlite3", 
    ".pkl", ".h5", ".parquet", ".pdf", ".docx", ".xlsx", ".pptx", 
    ".swp", ".swo", ".bak", ".orig", ".stackdump", ".wsb",
)
