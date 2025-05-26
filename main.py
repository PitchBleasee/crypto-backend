import os
import requests
import pandas as pd
import uvicorn
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Crypto backend online with CoinGecko and error handling"}

@app.get("/analyze")
def analyze(symbol: str = "bitcoin"):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart"
        params = {"vs_currency": "usd", "days": "30"}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        prices = data.get("prices", [])
        if not prices or len(prices) < 10:
            return JSONResponse(status_code=422, content={"error": "Dati insufficienti da CoinGecko."})

        df = pd.DataFrame(prices, columns=["timestamp", "price"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["price"] = df["price"].astype(float)

        df["sma"] = df["price"].rolling(window=7).mean()
        df["ema"] = df["price"].ewm(span=7, adjust=False).mean()
        df["bb_upper"] = df["sma"] + 2 * df["price"].rolling(window=7).std()
        df["bb_lower"] = df["sma"] - 2 * df["price"].rolling(window=7).std()
        df["rsi"] = compute_rsi(df["price"])
        latest = df.iloc[-1]

        return {
            "symbol": symbol,
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
        return JSONResponse(status_code=503, content={"error": "Errore nella richiesta a CoinGecko", "details": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Errore interno nel server", "details": str(e)})

@app.get("/market-scan")
def market_scan():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 10, "page": 1}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        coins = response.json()
        result = []
        for coin in coins:
            result.append({
                "id": coin["id"],
                "name": coin["name"],
                "symbol": coin["symbol"],
                "volatility_score": round(coin["price_change_percentage_24h"] or 0, 2)
            })
        return {"top_volatile": sorted(result, key=lambda x: -abs(x["volatility_score"]))[:5]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Errore durante market scan", "details": str(e)})

@app.get("/analyze-multi")
def analyze_multi():
    scan = market_scan()
    return {"analysis": [analyze(symbol=c["id"]) for c in scan.get("top_volatile", [])]}

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)