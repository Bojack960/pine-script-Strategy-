import ccxt
import os
import backtrader as bt
import datetime
import schedule
import time
import sqlite3
import pandas as pd

database_file = 'trades.db'

if not os.path.exists(database_file):
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE trades
                      (timestamp text, action text, price real)''')
    conn.commit()
    conn.close()

def welcome_message():
    print("Hello dear user!")
    print("Let's unite to make good profits today.")
    print()

welcome_message()

file_path = input("Enter the login file path: ")

while not os.path.exists(file_path):
    print("File does not exist. Please try again.")
    file_path = input("Enter the login file path: ")

with open(file_path, 'r') as file:
    login_data = file.readlines()

symbol = None
api_key = None
secret_key = None

for line in login_data:
    if line.startswith("Symbol:"):
        symbol = line.split(":")[1].strip()
    elif line.startswith("API Key:"):
        api_key = line.split(":")[1].strip()
    elif line.startswith("Secret Key:"):
        secret_key = line.split(":")[1].strip()

while not symbol:
    print("Symbol not found in the login file. Please try again.")
    symbol = input("Enter the symbol (e.g., BTC/USDT): ")

while not api_key:
    print("API Key not found in the login file. Please try again.")
    api_key = input("Enter your API key: ")

while not secret_key:
    print("Secret Key not found in the login file. Please try again.")
    secret_key = input("Enter your secret key: ")

while True:
    try:
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
        })
        break
    except ccxt.AuthenticationError:
        print("Invalid API key or secret key. Please try again.")
        api_key = None
        secret_key = None
        while not api_key:
            api_key = input("Enter your API key: ")
            if not api_key:
                print("API key is required. Please try again.")

        while not secret_key:
            secret_key = input("Enter your secret key: ")
            if not secret_key:
                print("Secret key is required. Please try again.")

class GetTrendStrategy(bt.Strategy):
    params = (
        ('maxIdLossPcnt', 1),
    )

    def __init__(self):
        self.risk.max_intraday_loss(self.params.maxIdLossPcnt)
        self.open_trades = 0
        self.successful_trades = 0
        self.failed_trades = 0

    def next(self):
        if self.data.close[0] > self.data.open[0] and self.data.open[0] > self.data.close[-1]:
            self.buy()
            self.open_trades += 1

        if self.data.close[0] < self.data.open[0] and self.data.open[0] < self.data.close[-1]:
            self.sell()
            self.open_trades += 1

    def notify_trade(self, trade):
        if trade.status == trade.Closed:
            if trade.pnl > 0:
                self.successful_trades += 1
            else:
                self.failed_trades += 1

def create_report():
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    query_total_trades = "SELECT COUNT(*) FROM trades"
    cursor.execute(query_total_trades)
    total_trades = cursor.fetchone()[0]

    query_successful_trades = "SELECT COUNT(*) FROM trades WHERE action = 'sell' AND price > 0"
    cursor.execute(query_successful_trades)
    successful_trades = cursor.fetchone()[0]

    query_failed_trades = "SELECT COUNT(*) FROM trades WHERE action = 'sell' AND price < 0"
    cursor.execute(query_failed_trades)
    failed_trades = cursor.fetchone()[0]

    print("تقرير بعد 24 ساعة:")
    print("عدد الصفقات الكلي: ", total_trades)
    print("عدد الصفقات الناجحة: ", successful_trades)
    print("عدد الصفقات الخاسعة: ", failed_trades)
    print("عدد الصفقات المفتوحة: ", strategy.open_trades)
    print("نسبة النجاح: ", successful_trades / total_trades * 100, "%")
    print()

    conn.close()

def run_strategy():
    cerebro = bt.Cerebro()
    cerebro.addstrategy(GetTrendStrategy)
    data = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.run()

    create_report()

schedule.every().day.at("00:00").do(run_strategy)

while True:
    schedule.run_pending()
    time.sleep(1)