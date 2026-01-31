import os
import sys
import threading
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Run only when launching the Django server (avoid migrations/management commands)
        if not self._should_run_startup_tasks():
            return

        thread = threading.Thread(target=self._run_startup_scrape, daemon=True)
        thread.start()

    @staticmethod
    def _should_run_startup_tasks():
        if os.environ.get("RUN_MAIN") != "true":
            return False
        args = " ".join(sys.argv)
        return "runserver" in args

    @staticmethod
    def _run_startup_scrape():
        try:
            from django.core.management import call_command
            # First fetch FX rates (USD->MRU) for today
            call_command("scrape_prices")
            # Then fetch Yahoo prices for commodities + BTC (recent days)
            call_command("scrape_yahoo_today", days=3)
        except Exception:
            # Avoid crashing server on startup scrape failures
            pass
