from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from datetime import datetime
import random

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
    return {"message": "Crypto backend online!"}

@app.get("/analyze")
def analyze(symbol: str = "bitcoin"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fake_data = {
        "symbol": symbol,
        "date": now,
        "price": round(random.uniform(1000, 30000), 2),
        "rsi": round(random.uniform(20, 80), 2),
        "macd": round(random.uniform(-10, 10), 2),
        "signal": round(random.uniform(-10, 10), 2),
        "sma": round(random.uniform(1000, 30000), 2),
        "ema": round(random.uniform(1000, 30000), 2),
        "bb_upper": round(random.uniform(1000, 32000), 2),
        "bb_lower": round(random.uniform(800, 29000), 2),
        "support": round(random.uniform(1000, 30000), 2),
        "resistance": round(random.uniform(1000, 30000), 2),
        "gpt_summary": f"Simulazione analisi tecnica per {symbol}",
        "news": [
            {"title": f"News 1 su {symbol}", "url": "https://example.com", "source": "Crypto Source"},
            {"title": f"News 2 su {symbol}", "url": "https://example.com", "source": "Crypto Source"}
        ],
        "history": {
            "dates": [f"2024-05-{i+1:02}" for i in range(30)],
            "prices": [round(random.uniform(1000, 30000), 2) for _ in range(30)],
            "sma": [round(random.uniform(1000, 30000), 2) for _ in range(30)],
            "bb_upper": [round(random.uniform(2000, 32000), 2) for _ in range(30)],
            "bb_lower": [round(random.uniform(800, 25000), 2) for _ in range(30)]
        }
    }
    return fake_data

@app.get("/market-scan")
def market_scan():
    return {
        "top_volatile": [
            {"id": "kaspa", "name": "Kaspa", "symbol": "kas", "volatility_score": 9.23},
            {"id": "dogecoin", "name": "Dogecoin", "symbol": "doge", "volatility_score": 7.85},
            {"id": "shiba", "name": "Shiba Inu", "symbol": "shib", "volatility_score": 6.54}
        ]
    }

@app.get("/analyze-multi")
def analyze_multi():
    return {
        "analysis": [
            {
                "symbol": "kaspa",
                "price": 0.123,
                "rsi": 55,
                "macd": 0.004,
                "signal": 0.002,
                "sma": 0.12,
                "ema": 0.125,
                "support": 0.115,
                "resistance": 0.135,
                "gpt_summary": "Kaspa mostra segni di consolidamento.",
                "news": [{"title": "Kaspa to the moon", "url": "https://example.com", "source": "Reddit"}]
            },
            {
                "symbol": "dogecoin",
                "price": 0.08,
                "rsi": 47,
                "macd": -0.002,
                "signal": -0.001,
                "sma": 0.079,
                "ema": 0.081,
                "support": 0.075,
                "resistance": 0.085,
                "gpt_summary": "Dogecoin stabile, ma da monitorare.",
                "news": [{"title": "Elon tweets again", "url": "https://example.com", "source": "Twitter"}]
            }
        ]
    }