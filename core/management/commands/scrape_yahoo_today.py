"""
Management command: python manage.py scrape_yahoo_today
Fetches recent prices from Yahoo Finance for commodities and BTC.
"""
from datetime import datetime, timedelta
from decimal import Decimal
import csv
import io
import logging

import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Asset, Price

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Scrape recent Yahoo Finance prices for commodities and bitcoin"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=3,
            help="Number of recent days to fetch (default: 3)",
        )

    def handle(self, *args, **options):
        days = max(1, int(options.get("days", 3)))
        today = datetime.now().date()
        start_date = today - timedelta(days=days)

        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("Yahoo Finance (recent)"))
        self.stdout.write("=" * 70)
        self.stdout.write(f"Periode: {start_date} -> {today} ({days} jours)")
        self.stdout.write("")

        mapping = {
            "GOLD": "GC=F",
            "COPPER": "HG=F",
            "IRON": "TIO=F",
            "BTC": "BTC-USD",
        }

        total_stored = 0
        total_failed = 0

        for asset_code, symbol in mapping.items():
            self.stdout.write(f"\nScraping {asset_code} (Yahoo: {symbol})...")
            try:
                stored, failed = self.fetch_and_store(asset_code, symbol, start_date, today)
                self.ensure_today_price(asset_code, today)
                self.stdout.write(self.style.SUCCESS(f"{asset_code}: {stored} prix stockes"))
                if failed:
                    self.stdout.write(self.style.WARNING(f"{failed} prix echoues"))
                total_stored += stored
                total_failed += failed
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erreur {asset_code}: {e}"))
                total_failed += 1

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("RESUME"))
        self.stdout.write("=" * 70)
        self.stdout.write(f"Stockes: {total_stored}")
        self.stdout.write(f"Echoues: {total_failed}")
        self.stdout.write(f"Total: {total_stored + total_failed}")
        self.stdout.write("=" * 70)

    @retry(stop=stop_after_attempt(6), wait=wait_exponential(multiplier=1, min=2, max=30))
    def fetch_yf(self, yahoo_symbol, start_date, end_date):
        import yfinance as yf

        yf_start = start_date.isoformat()
        yf_end = (end_date + timedelta(days=1)).isoformat()
        df = yf.download(yahoo_symbol, start=yf_start, end=yf_end, interval="1d", progress=False)
        if df is None or df.empty:
            raise ValueError("yfinance returned no data")
        return df

    @retry(stop=stop_after_attempt(6), wait=wait_exponential(multiplier=1, min=2, max=30))
    def request_with_retry(self, url, headers, timeout=20):
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 429:
            raise requests.RequestException(f"429 Too Many Requests for url: {url}")
        resp.raise_for_status()
        return resp

    def fetch_and_store(self, asset_code, yahoo_symbol, start_date, end_date):
        def to_unix(d):
            return int(datetime(d.year, d.month, d.day).timestamp())

        period1 = to_unix(start_date)
        period2 = to_unix(end_date + timedelta(days=1))
        url = (
            f"https://query1.finance.yahoo.com/v7/finance/download/{yahoo_symbol}"
            f"?period1={period1}&period2={period2}&interval=1d&events=history&includeAdjustedClose=true"
        )
        logger.info(f"Yahoo request: {url}")

        df = None
        try:
            df = self.fetch_yf(yahoo_symbol, start_date, end_date)
        except Exception as e:
            logger.warning(f"yfinance failed for {yahoo_symbol}: {e}")
            df = None

        if df is not None and not df.empty:
            return self._store_from_dataframe(asset_code, yahoo_symbol, df)

        logger.warning(f"yfinance empty for {yahoo_symbol}, fallback to CSV")
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
        }
        resp = self.request_with_retry(url, headers=headers, timeout=20)
        csvfile = io.StringIO(resp.text)
        reader = csv.DictReader(csvfile)
        rows = list(reader)
        return self._store_from_rows(asset_code, rows)

    def _store_from_dataframe(self, asset_code, yahoo_symbol, df):
        asset = Asset.objects.filter(code=asset_code).first()
        if asset is None:
            logger.error(f"Actif {asset_code} introuvable")
            return 0, 0

        stored = 0
        failed = 0
        is_multi = hasattr(df, "columns") and hasattr(df.columns, "names")
        for idx, row in df.iterrows():
            price_date = idx.date()
            if is_multi:
                close_val = row.get(("Close", yahoo_symbol))
                if close_val is None and "Close" in df.columns.get_level_values(0):
                    close_series = row.xs("Close")
                    close_val = close_series.iloc[0] if hasattr(close_series, "iloc") else close_series
            else:
                close_val = row.get("Close")

            if close_val is None or str(close_val) in ("nan", "NaN"):
                failed += 1
                continue

            try:
                close_usd = Decimal(str(close_val))
            except Exception:
                failed += 1
                continue

            if self._store_price(asset, price_date, close_usd):
                stored += 1
            else:
                failed += 1

        return stored, failed

    def _store_from_rows(self, asset_code, rows):
        asset = Asset.objects.filter(code=asset_code).first()
        if asset is None:
            logger.error(f"Actif {asset_code} introuvable")
            return 0, 0

        stored = 0
        failed = 0
        for r in rows:
            date_str = r.get("Date")
            close_str = r.get("Close")
            if not date_str or not close_str or close_str in ("", "null", "NaN"):
                failed += 1
                continue

            try:
                price_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                close_usd = Decimal(str(close_str))
            except Exception:
                failed += 1
                continue

            if self._store_price(asset, price_date, close_usd):
                stored += 1
            else:
                failed += 1

        return stored, failed

    def _store_price(self, asset, price_date, close_usd):
        usd_price = Price.objects.filter(asset__code="USD", date=price_date).first()
        if not usd_price:
            usd_price = Price.objects.filter(asset__code="USD", date__lt=price_date).order_by("-date").first()
        if not usd_price:
            return False

        try:
            price_mru = (close_usd * usd_price.price_mru).quantize(Decimal("0.01"))
            with transaction.atomic():
                Price.objects.update_or_create(
                    asset=asset,
                    date=price_date,
                    defaults={"price_mru": price_mru, "source": "yahoo"},
                )
            return True
        except Exception as e:
            logger.error(f"Erreur stockage {asset.code}/{price_date}: {e}")
            return False

    def ensure_today_price(self, asset_code, today):
        asset = Asset.objects.filter(code=asset_code).first()
        if asset is None:
            return
        exists = Price.objects.filter(asset=asset, date=today, source="yahoo").exists()
        if exists:
            return
        last = Price.objects.filter(asset=asset, source="yahoo").order_by("-date").first()
        if not last:
            return
        try:
            with transaction.atomic():
                Price.objects.update_or_create(
                    asset=asset,
                    date=today,
                    defaults={"price_mru": last.price_mru, "source": "yahoo"},
                )
        except Exception as e:
            logger.error(f"Erreur copie prix {asset_code}/{today}: {e}")
