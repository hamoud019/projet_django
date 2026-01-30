"""
Commande Django: python manage.py scrape_historical_yahoo
Rcupre l'historique depuis Yahoo Finance pour GOLD, COPPER et BTC
"""
from django.core.management.base import BaseCommand, CommandError
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import requests
import csv
import io
import random
from tenacity import retry, stop_after_attempt, wait_exponential
from core.models import Asset, Price
from django.db import transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
 help = "Scrape l'historique Yahoo Finance pour les matires premires et bitcoin"

 def add_arguments(self, parser):
  parser.add_argument(
   '--days',
   type=int,
   default=730,
   help='Nombre de jours  rcuprer (dfaut: 730 = 2 ans)'
  )

 def handle(self, *args, **options):
  days = options.get('days', 730)
  if days < 730:
   days = 730
   self.stdout.write(self.style.WARNING(" Minimum 730 jours (2 ans) requis  utilisation de 730 jours."))

  self.stdout.write("=" * 70)
  self.stdout.write(self.style.SUCCESS(" Scraping Yahoo Finance (historique)"))
  self.stdout.write("=" * 70)

  today = datetime.now().date()
  start_date = today - timedelta(days=days)

  self.stdout.write(f" Priode: {start_date}  {today} ({days} jours)")
  self.stdout.write("")

  # Mapping assets -> Yahoo symbols
  mapping = {
   'GOLD': 'GC=F',  # Gold futures
   'COPPER': 'HG=F', # Copper futures
   'BTC': 'BTC-USD', # Bitcoin
   'IRON': 'TIO=F', # Iron ore futures (CME TIO)
  }

  total_stored = 0
  total_failed = 0

  for asset_code, symbol in mapping.items():
   self.stdout.write(f"\n Scraping {asset_code} (Yahoo: {symbol})...")

   try:
    stored, failed = self.fetch_and_store(asset_code, symbol, start_date, today)
    self.stdout.write(self.style.SUCCESS(f" {asset_code}: {stored} prix stocks"))
    if failed > 0:
     self.stdout.write(self.style.WARNING(f" {failed} prix chous"))

    total_stored += stored
    total_failed += failed

   except Exception as e:
    self.stdout.write(self.style.ERROR(f" Erreur {asset_code}: {e}"))
    total_failed += 1

  # Rsum
  self.stdout.write("\n" + "=" * 70)
  self.stdout.write(self.style.SUCCESS(" RSUM"))
  self.stdout.write("=" * 70)
  self.stdout.write(f" Stocks: {total_stored}")
  self.stdout.write(f" chous: {total_failed}")
  self.stdout.write(f" Total: {total_stored + total_failed}")
  self.stdout.write("=" * 70)

 @retry(stop=stop_after_attempt(6), wait=wait_exponential(multiplier=1, min=2, max=30))
 def fetch_yf(self, yahoo_symbol, start_date, end_date):
  """
  Rcupre l'historique via yfinance avec retries exponentiels.
  """
  import yfinance as yf
  yf_start = start_date.isoformat()
  yf_end = (end_date + timedelta(days=1)).isoformat()
  df = yf.download(yahoo_symbol, start=yf_start, end=yf_end, interval='1d', progress=False)
  if df is None or df.empty:
   raise ValueError("yfinance returned no data")
  return df

 @retry(stop=stop_after_attempt(6), wait=wait_exponential(multiplier=1, min=2, max=30))
 def request_with_retry(self, url, headers, timeout=20):
  """Requests wrapper that retries on network errors and treats 429 as retryable."""
  resp = requests.get(url, headers=headers, timeout=timeout)
  if resp.status_code == 429:
   raise requests.RequestException(f"429 Too Many Requests for url: {url}")
  resp.raise_for_status()
  return resp

 def fetch_and_store(self, asset_code, yahoo_symbol, start_date, end_date):
  """
  Tlcharge l'historique CSV depuis Yahoo et stocke les prix en MRU
  """
  # Construire les timestamps Unix (secondes)
  def to_unix(d):
   return int(datetime(d.year, d.month, d.day).timestamp())

  period1 = to_unix(start_date)
  # Yahoo API endpoint expects period2 as end of _next_ day to include end_date
  period2 = to_unix(end_date + timedelta(days=1))

  url = (
   f"https://query1.finance.yahoo.com/v7/finance/download/{yahoo_symbol}"
   f"?period1={period1}&period2={period2}&interval=1d&events=history&includeAdjustedClose=true"
  )

  logger.info(f" Requte Yahoo: {url}")

  # Try yfinance first (handles cookies/crumbs and is more reliable)
  logger.info("Tentative via yfinance...")
  df = None
  try:
   df = self.fetch_yf(yahoo_symbol, start_date, end_date)
  except Exception as e:
   logger.warning(f"yfinance failed for {yahoo_symbol}: {e}")
   df = None

  if df is not None and not df.empty:
   logger.info(f" yfinance: {len(df)} enregistrements reus pour {yahoo_symbol}")
   stored = 0
   failed = 0

   asset = Asset.objects.filter(code=asset_code).first()
   if asset is None:
    logger.error(f"Actif {asset_code} introuvable")
    return 0, 0

   is_multi = hasattr(df, "columns") and hasattr(df.columns, "names")
   for idx, row in df.iterrows():
    price_date = idx.date()
    if is_multi:
     close_val = row.get(('Close', yahoo_symbol))
     if close_val is None and 'Close' in df.columns.get_level_values(0):
      close_series = row.xs('Close')
      close_val = close_series.iloc[0] if hasattr(close_series, 'iloc') else close_series
    else:
     close_val = row.get('Close')
    if close_val is None or str(close_val) in ('nan','NaN'):
     failed += 1
     continue
    try:
     close_usd = Decimal(str(close_val))
    except Exception:
     failed += 1
     continue

    usd_price = Price.objects.filter(asset__code='USD', date=price_date).first()
    if not usd_price:
     usd_price = Price.objects.filter(asset__code='USD', date__lt=price_date).order_by('-date').first()
    if not usd_price:
     failed += 1
     continue

    try:
     price_mru = (close_usd * usd_price.price_mru).quantize(Decimal('0.01'))
     with transaction.atomic():
      Price.objects.update_or_create(asset=asset, date=price_date, defaults={'price_mru': price_mru, 'source': 'yahoo'})
     stored += 1
    except Exception as e:
     logger.error(f"Erreur stockage {asset_code}/{price_date}: {e}")
     failed += 1
     continue

   return stored, failed
  else:
   logger.warning(f"yfinance ne renvoie pas de donnes pour {yahoo_symbol}, fallback vers CSV")

  # Headers et retries pour limiter les 429
  headers = {
   'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
   'Accept': '*/*',
  }

  # Tlcharger en morceaux (chunks) pour viter les throttles
  def daterange_chunks(s_date, e_date, chunk_days=90):
   cur = s_date
   while cur <= e_date:
    chunk_end = min(e_date, cur + timedelta(days=chunk_days - 1))
    yield cur, chunk_end
    cur = chunk_end + timedelta(days=1)

  stored = 0
  failed = 0

  asset = Asset.objects.filter(code=asset_code).first()
  if asset is None:
   logger.error(f"Actif {asset_code} introuvable")
   return 0, 0

  # Tlcharger par chunk
  for chunk_start, chunk_end in daterange_chunks(start_date, end_date, chunk_days=180):
   period1_chunk = to_unix(chunk_start)
   period2_chunk = to_unix(chunk_end + timedelta(days=1))
   url_chunk = (
    f"https://query1.finance.yahoo.com/v7/finance/download/{yahoo_symbol}"
    f"?period1={period1_chunk}&period2={period2_chunk}&interval=1d&events=history&includeAdjustedClose=true"
   )

   try:
    resp = self.request_with_retry(url_chunk, headers=headers, timeout=20)
   except Exception as e:
    logger.error(f"Erreur requte Yahoo {asset_code} chunk {chunk_start}{chunk_end}: {e}")
    failed += 1
    continue

   # Pause courte entre chunks pour rduire la charge
   import time
   time.sleep(4)

   # Lire CSV pour ce chunk
   csvfile = io.StringIO(resp.text)
   reader = csv.DictReader(csvfile)
   rows = list(reader)
   logger.info(f" Chunk {chunk_start}{chunk_end}: {len(rows)} enregistrements reus")
   # traiter lignes du chunk
   for r in rows:
    date_str = r.get('Date')
    close_str = r.get('Close')

    if not date_str or not close_str or close_str in ('', 'null', 'NaN'):
     failed += 1
     continue

    try:
     price_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
     failed += 1
     continue

    try:
     close_usd = Decimal(str(close_str))
    except Exception:
     failed += 1
     continue

    # Chercher le taux USD->MRU pour la mme date (ou dernier disponible avant)
    usd_price = Price.objects.filter(asset__code='USD', date=price_date).first()
    if not usd_price:
     usd_price = Price.objects.filter(asset__code='USD', date__lt=price_date).order_by('-date').first()

    if not usd_price:
     # Pas de taux USD disponible -> on ne peut pas convertir
     failed += 1
     continue

    # Calculer MRU
    try:
     price_mru = (close_usd * usd_price.price_mru).quantize(Decimal('0.01'))
    except Exception:
     failed += 1
     continue

    # Upsert
    try:
     with transaction.atomic():
      price_obj, created = Price.objects.update_or_create(
       asset=asset,
       date=price_date,
       defaults={'price_mru': price_mru, 'source': 'yahoo'}
      )
     stored += 1
    except Exception as e:
     logger.error(f"Erreur stockage {asset_code}/{price_date}: {e}")
     failed += 1
     continue

  return stored, failed
