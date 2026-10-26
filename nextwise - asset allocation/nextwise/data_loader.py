"""
=============================================================================
  data_loader.py — Yahoo Finance Data Collection & Preprocessing
=============================================================================
  
  CHANGES (v2.1):
    FIX #5  — Return clipping raised from ±20% to ±30% to avoid censoring
              legitimate moves on uranium, silver, small caps.
            — Added smart outlier detection: if >40% of assets move >15%
              on the same day, it's likely a data error → drop that day.
    MINOR   — Improved docstrings and type hints.
=============================================================================
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import streamlit as st
from config import PORTFOLIO, TICKER_FALLBACKS


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Flatten yfinance output robustly
# ─────────────────────────────────────────────────────────────────────────────

def _flatten_yf_columns(data: pd.DataFrame) -> pd.DataFrame:
    """
    yfinance >=0.2.36 always returns MultiIndex columns (Price, Ticker).
    This flattens them to just ticker names for the 'Close' price.
    Handles both old (flat) and new (MultiIndex) formats.
    """
    if data is None or data.empty:
        return pd.DataFrame()
    
    if isinstance(data.columns, pd.MultiIndex):
        # New yfinance format: ('Close', 'GOOG'), ('Close', 'AAPL'), ...
        try:
            if "Close" in data.columns.get_level_values(0):
                prices = data["Close"].copy()
            elif data.columns.nlevels > 1 and "Close" in data.columns.get_level_values(1):
                prices = data.xs("Close", axis=1, level=1).copy()
            else:
                prices = data.copy()
                prices.columns = [col[-1] if isinstance(col, tuple) else col for col in data.columns]
        except Exception:
            prices = data.copy()
            prices.columns = [col[-1] if isinstance(col, tuple) else col for col in data.columns]
        
        if isinstance(prices.columns, pd.MultiIndex):
            prices.columns = [col[-1] if isinstance(col, tuple) else col for col in prices.columns]
        
        if isinstance(prices, pd.Series):
            prices = prices.to_frame()
        
        return prices
    else:
        if "Close" in data.columns:
            return data[["Close"]].copy()
        return data.copy()


def _to_1d_series(obj, name: str = None) -> pd.Series | None:
    """
    Safely convert any yfinance output to a 1D pandas Series.
    Handles DataFrame, Series, and ndim>1 edge cases.
    """
    if obj is None:
        return None
    
    try:
        if isinstance(obj, pd.DataFrame):
            if obj.empty:
                return None
            s = obj.iloc[:, 0].copy()
        elif isinstance(obj, pd.Series):
            s = obj.copy()
        else:
            return None
        
        if hasattr(s, 'values') and s.values.ndim > 1:
            s = pd.Series(s.values.ravel(), index=s.index)
        
        if name:
            s.name = name
        
        return s.dropna()
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# OUTLIER DETECTION (FIX #5)
# ─────────────────────────────────────────────────────────────────────────────

def _clean_returns(returns_df: pd.DataFrame,
                   single_clip: float = 0.30,
                   multi_asset_threshold: float = 0.15,
                   multi_asset_frac: float = 0.40) -> pd.DataFrame:
    """
    Clean return data with two filters:
    
    1. HARD CLIP at ±single_clip (30%) — no single asset can move more.
       This catches genuine data errors (stock splits not adjusted, etc.)
       while preserving legitimate large moves on volatile assets.
    
    2. MULTI-ASSET OUTLIER — if more than multi_asset_frac (40%) of assets
       move more than multi_asset_threshold (15%) on the same day, the
       entire day is likely a data error → drop it.
    
    Parameters
    ----------
    returns_df : daily returns DataFrame
    single_clip : max absolute daily return (default ±30%)
    multi_asset_threshold : per-asset threshold for multi-asset check
    multi_asset_frac : fraction of assets that must exceed threshold
    
    Returns
    -------
    Cleaned returns DataFrame
    """
    df = returns_df.copy()
    
    # Step 1: Hard clip
    df = df.clip(-single_clip, single_clip)
    
    # Step 2: Drop days where too many assets have extreme moves
    n_assets = df.shape[1]
    extreme_count = (df.abs() > multi_asset_threshold).sum(axis=1)
    bad_days = extreme_count > (multi_asset_frac * n_assets)
    
    if bad_days.any():
        n_dropped = bad_days.sum()
        df = df[~bad_days]
        # Log this for the user
        if hasattr(st, 'session_state'):
            st.session_state.setdefault("_data_warnings", []).append(
                f"Dropped {n_dropped} suspicious day(s) where >{int(multi_asset_frac*100)}% "
                f"of assets moved >{int(multi_asset_threshold*100)}%."
            )
    
    return df


# ─────────────────────────────────────────────────────────────────────────────
# CORE DATA DOWNLOAD
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def download_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """
    Download adjusted close prices from Yahoo Finance.
    Returns DataFrame indexed by date, columns = tickers.
    """
    data = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    
    prices = _flatten_yf_columns(data)
    
    prices.columns = [str(c) if not isinstance(c, str) else c for c in prices.columns]
    
    return prices


def download_single_ticker(ticker: str, start: str, end: str) -> pd.Series | None:
    """Download a single ticker with error handling."""
    try:
        df = yf.download(
            ticker,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
        )
        if df is None or len(df) <= 50:
            return None
        
        flat = _flatten_yf_columns(df)
        series = _to_1d_series(flat, name=ticker)
        
        if series is not None and len(series) > 50:
            return series
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# PORTFOLIO DATA LOADER (with fallback logic)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="📡 Downloading market data from Yahoo Finance...")
def load_portfolio_data(lookback_years: int = 3) -> tuple[pd.DataFrame, pd.DataFrame, list[dict], list[str]]:
    """
    Load price data for all portfolio tickers.
    
    Returns:
        prices_df:      DataFrame of daily adjusted close prices
        returns_df:     DataFrame of daily returns
        valid_assets:   List of asset dicts that loaded successfully
        failed_tickers: List of tickers that could not be loaded
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=lookback_years * 365 + 30)).strftime("%Y-%m-%d")

    # ── Step 1: Bulk download all tickers at once ────────────────────────
    all_tickers = [p["ticker"] for p in PORTFOLIO]
    
    progress_bar = st.progress(0, text="Downloading bulk data...")
    
    try:
        bulk_prices = download_prices(all_tickers, start_date, end_date)
    except Exception:
        bulk_prices = pd.DataFrame()
    
    progress_bar.progress(40, text="Checking individual tickers...")

    # ── Step 2: Validate each ticker, try fallbacks if needed ────────────
    valid_assets = []
    failed_tickers = []
    prices_dict: dict[str, pd.Series] = {}
    
    total = len(PORTFOLIO)
    for i, asset in enumerate(PORTFOLIO):
        ticker = asset["ticker"]
        pct = 40 + int(55 * (i + 1) / total)
        progress_bar.progress(pct, text=f"Validating {asset['name']}...")
        
        series = None
        
        # Try from bulk download first
        if not bulk_prices.empty and ticker in bulk_prices.columns:
            series = _to_1d_series(bulk_prices[[ticker]], name=asset["name"])
            if series is not None and len(series) <= 50:
                series = None
        
        # If failed, try individual download
        if series is None:
            s = download_single_ticker(ticker, start_date, end_date)
            if s is not None:
                s.name = asset["name"]
                series = s
        
        # If still failed, try fallbacks
        if series is None and ticker in TICKER_FALLBACKS:
            for fallback in TICKER_FALLBACKS[ticker]:
                s = download_single_ticker(fallback, start_date, end_date)
                if s is not None:
                    s.name = asset["name"]
                    series = s
                    asset = {**asset, "ticker_used": fallback, "ticker_original": ticker}
                    break
        
        # Final check and store
        if series is not None and len(series) > 50:
            assert series.ndim == 1, f"{asset['name']} series is not 1D: shape={series.shape}"
            prices_dict[asset["name"]] = series
            valid_assets.append(asset)
        else:
            failed_tickers.append(ticker)
    
    progress_bar.progress(100, text="Data loaded!")
    
    # ── Step 3: Build clean DataFrames ───────────────────────────────────
    if not prices_dict:
        st.error("No data loaded. Check your internet connection.")
        return pd.DataFrame(), pd.DataFrame(), [], all_tickers
    
    all_dates = sorted(set().union(*(s.index for s in prices_dict.values())))
    prices_df = pd.DataFrame(index=pd.DatetimeIndex(all_dates))
    
    for name, series in prices_dict.items():
        prices_df[name] = series.reindex(prices_df.index)
    
    # Keep requested instruments with shorter listing histories. Never invent
    # pre-listing prices or silently remove them to extend the backtest.
    prices_df = prices_df.ffill(limit=5).dropna()
    if len(prices_df) <= 50:
        st.error("Historique commun insuffisant : au moins 51 cours communs sont nécessaires.")
        return pd.DataFrame(), pd.DataFrame(), [], failed_tickers
    if len(prices_df) < len(all_dates):
        st.info(
            "Backtest limité à l’historique commun des actifs chargés : "
            f"{prices_df.index[0]:%Y-%m-%d} → {prices_df.index[-1]:%Y-%m-%d}."
        )

    # Compute daily simple returns
    returns_df = prices_df.pct_change().dropna()
    
    # ── FIX #5: Smart outlier cleaning (was: clip ±20%) ──────────────────
    returns_df = _clean_returns(returns_df, single_clip=0.30)
    
    return prices_df, returns_df, valid_assets, failed_tickers


# ─────────────────────────────────────────────────────────────────────────────
# BENCHMARK DATA
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_benchmark(ticker: str = "^STOXX50E", lookback_years: int = 3) -> pd.Series:
    """
    Load benchmark returns for Beta calculation.
    Falls back to MSCI World (URTH) if Euro Stoxx fails.
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=lookback_years * 365 + 30)).strftime("%Y-%m-%d")
    
    for t in [ticker, "^STOXX50E", "^STOXX", "URTH", "^GSPC"]:
        series = download_single_ticker(t, start_date, end_date)
        if series is not None and len(series) > 100:
            returns = series.pct_change().dropna().clip(-0.30, 0.30)
            returns = _to_1d_series(returns, name=t)
            if returns is not None:
                return returns
    
    return None


# ─────────────────────────────────────────────────────────────────────────────
# DATA QUALITY REPORT
# ─────────────────────────────────────────────────────────────────────────────

def data_quality_summary(prices_df: pd.DataFrame, valid_assets: list, failed: list) -> dict:
    """Produce a data quality summary for the sidebar."""
    return {
        "total_requested":   len(PORTFOLIO),
        "successfully_loaded": len(valid_assets),
        "failed":            len(failed),
        "failed_tickers":    failed,
        "date_range":        f"{prices_df.index[0].strftime('%Y-%m-%d')} → {prices_df.index[-1].strftime('%Y-%m-%d')}",
        "trading_days":      len(prices_df),
        "avg_nan_pct":       f"{prices_df.isna().mean().mean()*100:.1f}%",
    }