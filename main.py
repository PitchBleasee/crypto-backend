from pydantic import BaseModel
from typing import List, Optional
from functools import lru_cache

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
def get_market_chart(symbol: str):
    url = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart"
    params = {"vs_currency": "usd", "days": "30"}
    res = requests.get(url, params=params, timeout=10)
    res.raise_for_status()
    return res.json()

def compute_macd(series, span_short=12, span_long=26, span_signal=9):
    ema_short = series.ewm(span=span_short, adjust=False).mean()
    ema_long = series.ewm(span=span_long, adjust=False).mean()
    macd = ema_short - ema_long
    signal = macd.ewm(span=span_signal, adjust=False).mean()
    return macd, signal

@app.get("/analyze", response_model=AnalysisResponse)
def analyze(symbol: str = "bitcoin"):
    data = get_market_chart(symbol)
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
    latest = df.iloc[-1]
    return AnalysisResponse(
        symbol=symbol,
        date=str(latest["timestamp"]),
        price=round(latest["price"], 4),
        sma=round(latest["sma"], 4),
        ema=round(latest["ema"], 4),
        bb_upper=round(latest["bb_upper"], 4),
        bb_lower=round(latest["bb_lower"], 4),
        rsi=round(latest["rsi"], 2),
        macd=round(macd_series.iloc[-1], 4),
        signal=round(signal_series.iloc[-1], 4),
        support=round(df["price"].min(), 2),
        resistance=round(df["price"].max(), 2),
        gpt_summary="GPT disabilitato.",
        news=[],
        history=History(
            dates=df["timestamp"].dt.strftime("%Y-%m-%d").tolist(),
            prices=df["price"].round(2).tolist(),
            sma=df["sma"].round(2).tolist(),
            bb_upper=df["bb_upper"].round(2).tolist(),
            bb_lower=df["bb_lower"].round(2).tolist()
        )
    )
