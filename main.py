from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import requests
from functools import lru_cache
from datetime import datetime
import os
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class History(BaseModel):
    dates: List[str]
    prices: List[float]
    sma: List[Optional[float]]
    bb_upper: List[Optional[float]]
    bb_lower: List[Optional[float]]

class NewsItem(BaseModel):
    title: str
    url: str
    source: str

class AnalysisResponse(BaseModel):
    symbol: str
    date: str
    price: float
    sma: float
    ema: float
    bb_upper: float
    bb_lower: float
    rsi: float
    macd: float
    signal: float
    support: float
    resistance: float
    gpt_summary: str
    news: List[NewsItem]
    history: History

@lru_cache(maxsize=64)
def get_market_chart(coin_id: str):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": "30"}
    res = requests.get(url, params=params, timeout=10)
    res.raise_for_status()
    return res.json()

@lru_cache(maxsize=128)
def resolve_symbol_to_id(symbol: str):
    url = "https://api.coingecko.com/api/v3/coins/list"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
    except requests.exceptions.HTTPError:
        raise HTTPException(status_code=503, detail="Limite raggiunto su CoinGecko. Riprova più tardi.")
    coins = res.json()
    match = next((coin for coin in coins if coin["symbol"].lower() == symbol.lower()), None)
    if not match:
        raise HTTPException(status_code=404, detail="Simbolo non trovato")
    return match["id"]

def compute_macd(series, span_short=12, span_long=26, span_signal=9):
    ema_short = series.ewm(span=span_short, adjust=False).mean()
    ema_long = series.ewm(span=span_long, adjust=False).mean()
    macd = ema_short - ema_long
    signal = macd.ewm(span=span_signal, adjust=False).mean()
    return macd, signal

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

@app.get("/")
def root():
    return {"message": "Crypto backend online with CoinGecko and error handling"}

@app.get("/analyze", response_model=AnalysisResponse)
def analyze(symbol: str = "bitcoin"):
    coin_id = resolve_symbol_to_id(symbol)
    data = get_market_chart(coin_id)
    prices = data.get("prices", [])
    if not prices or len(prices) < 10:
        raise HTTPException(status_code=422, detail="Dati insufficienti.")

    df = pd.DataFrame(prices, columns=["timestamp", "price"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["price"] = df["price"].astype(float)
    df["sma"] = df["price"].rolling(window=7).mean()
    df["ema"] = df["price"].ewm(span=7, adjust=False).mean()
    df["bb_upper"] = df["sma"] + 2 * df["price"].rolling(window=7).std()
    df["bb_lower"] = df["sma"] - 2 * df["price"].rolling(window=7).std()
    df["rsi"] = compute_rsi(df["price"])
    macd_series, signal_series = compute_macd(df["price"])

    df = df.replace([float("inf"), float("-inf")], None)
    df = df.fillna(value=None)

    latest = df.iloc[-1]

    return AnalysisResponse(
        symbol=symbol,
        date=str(latest["timestamp"]),
        price=round(latest["price"], 4),
        sma=round(latest["sma"], 4) if latest["sma"] is not None else None,
        ema=round(latest["ema"], 4) if latest["ema"] is not None else None,
        bb_upper=round(latest["bb_upper"], 4) if latest["bb_upper"] is not None else None,
        bb_lower=round(latest["bb_lower"], 4) if latest["bb_lower"] is not None else None,
        rsi=round(latest["rsi"], 2) if latest["rsi"] is not None else None,
        macd=round(macd_series.iloc[-1], 4) if pd.notna(macd_series.iloc[-1]) else None,
        signal=round(signal_series.iloc[-1], 4) if pd.notna(signal_series.iloc[-1]) else None,
        support=round(df["price"].min(), 2),
        resistance=round(df["price"].max(), 2),
        gpt_summary="GPT disabilitato.",
        news=[],
        history=History(
            dates=df["timestamp"].dt.strftime("%Y-%m-%d").tolist(),
            prices=df["price"].round(2).tolist(),
            sma=df["sma"].round(2).fillna(0).tolist(),
            bb_upper=df["bb_upper"].round(2).fillna(0).tolist(),
            bb_lower=df["bb_lower"].round(2).fillna(0).tolist()
        )
    )

@app.get("/market-scan")
def market_scan():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 10, "page": 1}
    res = requests.get(url, params=params, timeout=10)
    res.raise_for_status()
    coins = res.json()
    result = []
    for coin in coins:
        result.append({
            "id": coin["id"],
            "name": coin["name"],
            "symbol": coin["symbol"],
            "volatility_score": round(coin.get("price_change_percentage_24h") or 0, 2)
        })
    return {"top_volatile": sorted(result, key=lambda x: -abs(x["volatility_score"]))[:5]}

@app.get("/analyze-multi")
def analyze_multi():
    scan = market_scan()
    return {"analysis": [analyze(symbol=c["symbol"]) for c in scan.get("top_volatile", [])]}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
