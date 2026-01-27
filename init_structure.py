from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

structure = {
    "project": [
        "__init__.py",
        "settings.py",
        "urls.py",
        "asgi.py",
        "wsgi.py",
    ],
    "core": {
        "": [
            "__init__.py",
            "admin.py",
            "apps.py",
            "models.py",
            "views.py",
            "urls.py",
        ],
        "services": [
            "__init__.py",
            "pricing.py",
            "prediction.py",
            "comparison.py",
        ],
        "api": [
            "__init__.py",
            "views.py",
        ],
        "templates/core": [
            "home.html",
            "asset_detail.html",
            "comparison.html",
            "prediction.html",
        ],
        "static/core/css": [],
        "static/core/js": [],
        "migrations": ["__init__.py"],
    },
    "scraper": {
        "": ["__init__.py", "normalize.py", "store.py", "runner.py"],
        "fetchers": [
            "__init__.py",
            "fx.py",
            "metals.py",
            "crypto.py",
        ],
    },
    "sync": [
        "__init__.py",
        "mongo_client.py",
        "sync_prices.py",
        "runner.py",
    ],
    "logs": [
        "web.log",
        "scraper.log",
        "sync.log",
    ],
    "scripts": [
        "run_scraper.sh",
        "run_sync.sh",
    ],
}

def create_structure(base, tree):
    for name, content in tree.items():
        path = base / name
        path.mkdir(parents=True, exist_ok=True)

        if isinstance(content, list):
            for file in content:
                (path / file).touch(exist_ok=True)

        elif isinstance(content, dict):
            for sub, files in content.items():
                sub_path = path / sub
                sub_path.mkdir(parents=True, exist_ok=True)
                for file in files:
                    (sub_path / file).touch(exist_ok=True)

if __name__ == "__main__":
    create_structure(BASE_DIR, structure)
    print("✅ Structure du projet créée avec succès")
