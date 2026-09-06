# SPX Signal Bot (Ideas Only – No Trading)

Simple Telegram bot that analyzes the S&P 500 and sends options strategy ideas (Call / Put / Iron Condor / Butterfly) based on market regime.

**This bot never places trades.** It only sends ideas to your Telegram.

## Features
- Detects Trending Bull / Trending Bear / Ranging
- Suggests Call, Put, Iron Condor or Butterfly with approximate strikes
- Sends clean messages to Telegram
- Runs only during US market hours (optional)

## Setup

1. Clone the repo
2. Install requirements:
   ```bash
   pip install -r requirements.txt
