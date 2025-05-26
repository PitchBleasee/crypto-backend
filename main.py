import os
import requests
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Literal

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYMBOL_MAP = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "ada": "cardano",
    "doge": "dogecoin",
    "sol": "solana",
    "bnb": "binancecoin",
    "xrp": "ripple",
    "ltc": "litecoin"
}

BINANCE_SYMBOL_MAP = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "cardano": "ADAUSDT",
    "dogecoin": "DOGEUSDT",
    "solana": "SOLUSDT",
    "ripple": "XRPUSDT",
    "binancecoin": "BNBUSDT",
    "litecoin": "LTCUSDT"
}

@app.get("/")
def root():
    return {"message": "Crypto backend online with Binance API"}

def resolve_symbol_to_id(symbol: str):
    symbol = symbol.lower()
    if symbol in SYMBOL_MAP.values():
        return symbol
    coin_id = SYMBOL_MAP.get(symbol)
    if not coin_id:
        raise HTTPException(status_code=404, detail="Simbolo non riconosciuto o supportato.")
    return coin_id

def get_binance_klines(coin_id: str, interval: str):
    symbol = BINANCE_SYMBOL_MAP.get(coin_id.lower())
    if not symbol:
        raise HTTPException(status_code=400, detail=f"Coin non supportata da Binance: {coin_id}")
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": 100}
    res = requests.get(url, params=params, timeout=10)
    res.raise_for_status()
    data = res.json()
    return [{"timestamp": int(c[0]), "price": float(c[4])} for c in data]

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

@app.get("/analyze")
def analyze(symbol: str = "bitcoin", interval: Literal["1d", "7d", "30d"] = "30d"):
    try:
        coin_id = resolve_symbol_to_id(symbol)
        interval_map = {"1d": "1h", "7d": "4h", "30d": "1d"}
        binance_interval = interval_map.get(interval, "1d")
        raw_data = get_binance_klines(coin_id, binance_interval)

        df = pd.DataFrame(raw_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["price"] = df["price"].astype(float)
        df["sma"] = df["price"].rolling(window=7).mean()
        df["ema"] = df["price"].ewm(span=7, adjust=False).mean()
        df["bb_upper"] = df["sma"] + 2 * df["price"].rolling(window=7).std()
        df["bb_lower"] = df["sma"] - 2 * df["price"].rolling(window=7).std()
        df["rsi"] = compute_rsi(df["price"])
        df = df.dropna()
        latest = df.iloc[-1]

        return {
            "symbol": coin_id,
            "date": str(latest["timestamp"]),
            "price": round(latest["price"], 4),
            "sma": round(latest["sma"], 4),
            "ema": round(latest["ema"], 4),
            "bb_upper": round(latest["bb_upper"], 4),
            "bb_lower": round(latest["bb_lower"], 4),
            "rsi": round(latest["rsi"], 2),
            "macd": None,
            "signal": None,
            "support": round(df["price"].min(), 2),
            "resistance": round(df["price"].max(), 2),
            "gpt_summary": "GPT disabilitato.",
            "news": [],
            "history": {
                "dates": df["timestamp"].dt.strftime("%Y-%m-%d").tolist(),
                "prices": df["price"].round(2).tolist(),
                "sma": df["sma"].round(2).tolist(),
                "bb_upper": df["bb_upper"].round(2).tolist(),
                "bb_lower": df["bb_lower"].round(2).tolist()
            }
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Errore Binance: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")

@app.get("/market-scan")
def market_scan():
    try:
        coins = ["bitcoin", "ethereum", "cardano", "dogecoin", "solana", "ripple"]
        result = []
        for coin in coins:
            try:
                data = get_binance_klines(coin, "1d")[-2:]
                change = ((data[-1]['price'] - data[0]['price']) / data[0]['price']) * 100
                result.append({"id": coin, "name": coin.capitalize(), "symbol": coin[:3], "volatility_score": round(change, 2)})
            except:
                continue
        return {"top_volatile": sorted(result, key=lambda x: -abs(x["volatility_score"]))[:5]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore market scan: {str(e)}")

@app.get("/analyze-multi")
def analyze_multi():
    scan = market_scan()
    return {"analysis": [analyze(symbol=c["id"]) for c in scan.get("top_volatile", [])]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

