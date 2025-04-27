import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import os

# ============ SETTINGS ============ #
FRED_API_KEY = 'your_fred_api_key_here'  # If you have it (optional)
HIGH_IMPACT_KEYWORDS = ['Fed', 'CPI', 'Jobs', 'Powell', 'inflation', 'unemployment', 'GDP']
TODAY = datetime.date.today()

# ============ DATA FETCH ============ #

# 1. Yield Curve Spreads (2s5s and 2s10s)
def get_treasury_spreads():
    tnx = yf.Ticker("^TNX").history(period="1d").iloc[-1]['Close'] / 100  # 10Y yield
    fvxt = yf.Ticker("^FVX").history(period="1d").iloc[-1]['Close'] / 100  # 5Y yield
    twxt = yf.Ticker("^IRX").history(period="1d").iloc[-1]['Close'] / 100  # 2Y yield
    spread_2s5s = twxt - fvxt
    spread_2s10s = twxt - tnx
    return spread_2s5s, spread_2s10s

# 2. VIX, VIX9D Term Structure

def get_vix_structure():
    vix = yf.Ticker("^VIX").history(period="1d").iloc[-1]['Close']
    vix9d = yf.Ticker("^VIX9D").history(period="1d").iloc[-1]['Close']
    term_structure = vix9d - vix
    return vix, vix9d, term_structure

# 3. Expected Move from ATM Straddle (example for SPY)
def get_expected_move():
    spy = yf.Ticker("SPY")
    options = spy.option_chain()
    calls = options.calls
    puts = options.puts
    underlying_price = spy.history(period="1d").iloc[-1]['Close']
    atm_strike = calls.iloc[(calls['strike']-underlying_price).abs().argsort()[:1]]['strike'].values[0]
    call_price = calls[calls['strike']==atm_strike]['lastPrice'].values[0]
    put_price = puts[puts['strike']==atm_strike]['lastPrice'].values[0]
    expected_move = call_price + put_price
    return expected_move, atm_strike

# 4. ES Fair Value vs SPX

def get_fair_value():
    es = yf.Ticker("ES=F").history(period="1d").iloc[-1]['Close']
    spx = yf.Ticker("^GSPC").history(period="1d").iloc[-1]['Close']
    premium_discount = es - spx
    return premium_discount

# 5. News Headlines Scraping

def fetch_headlines():
    url = "https://finance.yahoo.com/"
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    headlines = []
    for item in soup.find_all('h3'):
        text = item.get_text()
        if any(keyword in text for keyword in HIGH_IMPACT_KEYWORDS):
            headlines.append(text)
    return headlines

# ============ RISK SCORING ============ #

def risk_meter(spreads, vix_struct, expected_move, premium_discount):
    points = 0
    spread_2s5s, spread_2s10s = spreads
    vix, vix9d, term_structure = vix_struct
    
    # Yield Curve
    if spread_2s10s > 0:
        points += 1  # steepening is risk-on
    else:
        points -= 1  # inversion is risk-off
    
    # VIX Term Structure
    if term_structure > 0:
        points += 1  # normal term structure
    else:
        points -= 1  # inverted term structure risk-off

    # Expected Move
    if expected_move < 5:
        points += 1  # lower implied volatility
    else:
        points -= 1

    # ES Fair Value
    if premium_discount > 0:
        points += 1  # ES futures in premium
    else:
        points -= 1
    
    return points

# ============ HTML GENERATOR ============ #

def generate_html(data, risk_score, headlines):
    html = f"""
    <html>
    <head><title>Financial Dashboard Report - {TODAY}</title></head>
    <body>
    <h1>Financial Dashboard - {TODAY}</h1>
    <h2>Macro Overview</h2>
    <ul>
        <li>2s5s Spread: {data['spread_2s5s']:.2f}%</li>
        <li>2s10s Spread: {data['spread_2s10s']:.2f}%</li>
    </ul>
    <h2>Volatility</h2>
    <ul>
        <li>VIX: {data['vix']:.2f}</li>
        <li>VIX9D: {data['vix9d']:.2f}</li>
        <li>VIX Term Structure (9D-VIX): {data['term_structure']:.2f}</li>
        <li>Expected Move (ATM Straddle SPY): ${data['expected_move']:.2f} (Strike: {data['atm_strike']})</li>
    </ul>
    <h2>Market Position</h2>
    <ul>
        <li>ES Futures Premium/Discount: {data['premium_discount']:.2f}</li>
    </ul>
    <h2>Risk Meter</h2>
    <p><strong>Risk Score: {risk_score}</strong> ({'Risk-On' if risk_score > 0 else 'Risk-Off'})</p>
    <h2>High Impact News</h2>
    <ul>
    """
    for hl in headlines:
        html += f"<li>{hl}</li>"
    html += """
    </ul>
    </body>
    </html>
    """
    with open("dashboard_report.html", "w") as f:
        f.write(html)

# ============ MAIN RUN ============ #

def main():
    spreads = get_treasury_spreads()
    vix_struct = get_vix_structure()
    expected_move, atm_strike = get_expected_move()
    premium_discount = get_fair_value()
    headlines = fetch_headlines()

    data = {
        'spread_2s5s': spreads[0],
        'spread_2s10s': spreads[1],
        'vix': vix_struct[0],
        'vix9d': vix_struct[1],
        'term_structure': vix_struct[2],
        'expected_move': expected_move,
        'atm_strike': atm_strike,
        'premium_discount': premium_discount,
    }

    risk_score = risk_meter(spreads, vix_struct, expected_move, premium_discount)

    # Terminal Output
    print(f"\nFINANCIAL DASHBOARD - {TODAY}")
    print("==============================")
    print(f"2s5s Spread: {data['spread_2s5s']:.2f}%")
    print(f"2s10s Spread: {data['spread_2s10s']:.2f}%")
    print(f"VIX: {data['vix']:.2f}")
    print(f"VIX9D: {data['vix9d']:.2f}")
    print(f"VIX Term Structure: {data['term_structure']:.2f}")
    print(f"Expected Move (ATM Straddle SPY): ${data['expected_move']:.2f}")
    print(f"ES Futures Premium/Discount: {data['premium_discount']:.2f}")
    print(f"\nRisk Score: {risk_score} ({'Risk-On' if risk_score > 0 else 'Risk-Off'})")
    print("\nHigh Impact News:")
    for hl in headlines:
        print(f" - {hl}")

    # HTML Report
    generate_html(data, risk_score, headlines)

if __name__ == "__main__":
    main()
