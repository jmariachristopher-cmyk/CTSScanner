import streamlit as st
import pandas as pd
import numpy as np
from angelone_client import AngelOneClient

st.set_page_config(page_title="Abandoned Baby Camarilla R3/S3 Scanner", page_icon="🔎", layout="wide")

def add_camarilla(df):
    x=df.copy().sort_values("date").reset_index(drop=True)
    x["session"]=x["date"].dt.date
    daily=(x.groupby("session",sort=True)
             .agg(H=("high","max"),L=("low","min"),C=("close","last"))
             .reset_index())
    h,l,c=daily["H"].shift(1),daily["L"].shift(1),daily["C"].shift(1)
    rng=h-l
    daily["R3"]=c+rng*1.1/4
    daily["S3"]=c-rng*1.1/4
    return x.merge(daily[["session","R3","S3"]],on="session",how="left")

def scan(df, pattern, tolerance, doji_pct, long_factor):
    x=add_camarilla(df)
    x["body"]=(x["close"]-x["open"]).abs()
    x["rng"]=(x["high"]-x["low"]).replace(0,np.nan)
    x["body_pct"]=x["body"]/x["rng"]
    x["avg_body20"]=x["body"].rolling(20,min_periods=5).mean()
    results=[]

    for i in range(2,len(x)):
        d1,d2,d3=x.iloc[i-2],x.iloc[i-1],x.iloc[i]
        if pd.isna(d1["avg_body20"]) or pd.isna(d3["R3"]): continue

        d1_long=d1["body"] >= d1["avg_body20"]*long_factor
        d3_long=d3["body"] >= d3["avg_body20"]*long_factor
        d2_doji=d2["rng"]>0 and d2["body_pct"]<=doji_pct

        bullish=(
            d1["close"]<d1["open"] and d1_long and
            d2_doji and d2["high"]<d1["low"] and
            d3["close"]>d3["open"] and d3_long and
            d3["low"]>d2["high"] and d3["close"]>d1["open"]
        )

        bearish=(
            d1["close"]>d1["open"] and d1_long and
            d2_doji and d2["low"]>d1["high"] and
            d3["close"]<d3["open"] and d3_long and
            d3["high"]<d2["low"] and d3["close"]<d1["open"]
        )

        if pattern=="Bullish Abandoned Baby" and bullish:
            s3=d3["S3"]
            touched=(
                abs(d1["low"]-s3)/abs(s3)*100<=tolerance or
                abs(d2["low"]-s3)/abs(s3)*100<=tolerance or
                abs(d3["low"]-s3)/abs(s3)*100<=tolerance or
                d3["low"]<=s3<=d3["high"]
            )
            if touched and d3["close"]>s3:
                results.append({
                    "Signal":"BULLISH",
                    "Date":d3["date"],
                    "Level":"Camarilla S3",
                    "S3":s3,
                    "Close":d3["close"],
                    "D1":d1["date"],"D2":d2["date"],"D3":d3["date"],
                    "D1 Open":d1["open"],"D1 Low":d1["low"],
                    "D2 High":d2["high"],"D3 Low":d3["low"]
                })

        if pattern=="Bearish Abandoned Baby" and bearish:
            r3=d3["R3"]
            touched=(
                abs(d1["high"]-r3)/abs(r3)*100<=tolerance or
                abs(d2["high"]-r3)/abs(r3)*100<=tolerance or
                abs(d3["high"]-r3)/abs(r3)*100<=tolerance or
                d3["low"]<=r3<=d3["high"]
            )
            if touched and d3["close"]<r3:
                results.append({
                    "Signal":"BEARISH",
                    "Date":d3["date"],
                    "Level":"Camarilla R3",
                    "R3":r3,
                    "Close":d3["close"],
                    "D1":d1["date"],"D2":d2["date"],"D3":d3["date"],
                    "D1 Open":d1["open"],"D1 High":d1["high"],
                    "D2 Low":d2["low"],"D3 High":d3["high"]
                })

    return pd.DataFrame(results)

st.title("🔎 Abandoned Baby — Camarilla R3 / S3 Scanner")
st.caption("V4 • Only Camarilla R3 resistance and S3 support • EMA and other pivot levels removed")

if "results" not in st.session_state:
    st.session_state.results=pd.DataFrame()

with st.sidebar:
    pattern=st.radio("Pattern",["Bullish Abandoned Baby","Bearish Abandoned Baby"])
    timeframe=st.selectbox(
        "Timeframe",
        ["1 Minute","3 Minutes","5 Minutes","10 Minutes","15 Minutes","30 Minutes","1 Hour","1 Day"],
        index=7
    )
    interval={
        "1 Minute":"ONE_MINUTE","3 Minutes":"THREE_MINUTE","5 Minutes":"FIVE_MINUTE",
        "10 Minutes":"TEN_MINUTE","15 Minutes":"FIFTEEN_MINUTE","30 Minutes":"THIRTY_MINUTE",
        "1 Hour":"ONE_HOUR","1 Day":"ONE_DAY"
    }[timeframe]

    tolerance=st.number_input("R3/S3 tolerance (%)",0.05,5.0,0.25,0.05)
    doji_pct=st.number_input("Doji max body / range",0.01,0.50,0.10,0.01)
    long_factor=st.number_input("Long candle / 20-candle average",0.50,5.0,1.20,0.05)
    days=st.number_input("Historical days",1,3650,365,1)
    source=st.radio("Data Source",["Angel One API","Upload CSV"])
    run=st.button("🔍 RUN SCANNER",type="primary",use_container_width=True)

symbols=[
"ASTRAL","CONCOR","KALYANKJIL","GODREJCP","BDL","PAYTM","JUBLFOOD","TMPV","BEL","TECHM",
"SHRIRAMFIN","TATAPOWER","DLF","NTPC","ITC","PFC","SWIGGY","KOTAKBANK","BHARTIARTL","MCX",
"RECLTD","SBIN","COALINDIA","HDFCBANK","INDUSTOWER","BPCL","LICI","INFY","POWERGRID","BSE",
"ADANIENSOL","AXISBANK","HINDZINC","RELIANCE","ICICIBANK","SBICARD","VEDL","HINDALCO","NATIONALUM"
]

st.subheader("Symbols")
symbol_text=st.text_area("NSE symbols","\n".join(symbols),height=170)
symbols=[s.strip().upper() for s in symbol_text.replace(",","\n").splitlines() if s.strip()]

if run:
    combined=[]

    if source=="Upload CSV":
        uploaded=st.file_uploader(
            "Upload OHLC CSV: date, open, high, low, close",
            type=["csv"]
        )
        if uploaded is None:
            st.warning("Upload a CSV and run the scanner.")
        else:
            df=pd.read_csv(uploaded)
            df.columns=[c.strip().lower() for c in df.columns]
            required={"date","open","high","low","close"}
            if not required.issubset(df.columns):
                st.error("CSV must contain: date, open, high, low, close")
            else:
                df["date"]=pd.to_datetime(df["date"])
                r=scan(df,pattern,tolerance,doji_pct,long_factor)
                if not r.empty:
                    r.insert(0,"Symbol","CSV")
                    combined.append(r)

    else:
        try:
            client=AngelOneClient.from_streamlit_secrets()
        except Exception as e:
            st.error(str(e))
            client=None

        if client:
            progress=st.progress(0)
            status=st.empty()

            for n,symbol in enumerate(symbols,1):
                status.write(f"Scanning {symbol} — {n}/{len(symbols)}")
                try:
                    df=client.get_historical(symbol,interval,int(days))
                    if df is not None and len(df)>=30:
                        r=scan(df,pattern,tolerance,doji_pct,long_factor)
                        if not r.empty:
                            r.insert(0,"Symbol",symbol)
                            combined.append(r)
                except Exception as e:
                    st.warning(f"{symbol}: {e}")
                progress.progress(n/len(symbols))

            status.success("Scan completed.")

    st.session_state.results=(
        pd.concat(combined,ignore_index=True)
        if combined else pd.DataFrame()
    )

st.divider()
st.subheader(f"{pattern} Signals")

result=st.session_state.results
if result.empty:
    st.info("No signals found with the selected settings.")
else:
    st.success(f"{len(result)} signal(s) found")
    st.dataframe(result,use_container_width=True,hide_index=True)
    st.download_button(
        "⬇️ Download Signals CSV",
        result.to_csv(index=False).encode("utf-8"),
        "abandoned_baby_camarilla_r3_s3_signals.csv",
        "text/csv"
    )

st.divider()
st.subheader("V4 Rules")

if pattern=="Bullish Abandoned Baby":
    st.markdown("""
### 🟢 Bullish Abandoned Baby — Camarilla S3

1. D1 = long red candle
2. D2 = doji
3. D2 High < D1 Low
4. D3 = long green candle
5. D3 Low > D2 High
6. D3 Close > D1 Open
7. Pattern must test **Camarilla S3**
8. D3 must close **above S3**

**Signal = Bullish Abandoned Baby + S3 support rejection**
""")
else:
    st.markdown("""
### 🔴 Bearish Abandoned Baby — Camarilla R3

1. D1 = long green candle
2. D2 = doji
3. D2 Low > D1 High
4. D3 = long red candle
5. D3 High < D2 Low
6. D3 Close < D1 Open
7. Pattern must test **Camarilla R3**
8. D3 must close **below R3**

**Signal = Bearish Abandoned Baby + R3 resistance rejection**
""")

st.info(
    "Camarilla formula: R3 = Previous Close + 1.1 × (Previous High − Previous Low) / 4; "
    "S3 = Previous Close − 1.1 × (Previous High − Previous Low) / 4. "
    "For intraday data these levels use the previous completed trading day's H/L/C."
)
