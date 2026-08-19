import threading
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.dates as mdates
import yfinance as yf
from collections import deque
from datetime import datetime

TICKERS = ["AAPL"]
MAX_POINTS = 200
DELAY = 500

data = {t: deque(maxlen=MAX_POINTS) for t in TICKERS}
lock = threading.Lock()

def seed_recent_history() -> None: #need to fix
    for t in TICKERS:
        try:
            hist = yf.Ticker(t).history(period="1d", interval="1m")
            hist = hist.tail(MAX_POINTS)
            with lock:
                for ts, row in hist.iterrows():
                    data[t].append((ts.to_pydatetime(), row["Close"]))
        except Exception as e:
            print(f"Could not load history for {t}: {e}")

def message_handler(message: dict) -> None:
    print("Received message")
    symbol = message.get("id")
    price = message.get("price")
    if symbol in data and price is not None:
        with lock:
            data[symbol].append((datetime.now(), price))

def start_websocket() -> None:
    with yf.WebSocket() as ws:
        ws.subscribe(TICKERS)
        ws.listen(message_handler)

def show_live_chart(doSeedData=False) -> None:
    if doSeedData:
        seed_recent_history()

    ws_thread = threading.Thread(target=start_websocket, daemon=True)
    ws_thread.start()

    fig, ax = plt.subplots(figsize=(10, 6))
    lines = {t: ax.plot([], [], label=t)[0] for t in TICKERS}

    ax.set_xlabel("Time")
    ax.set_ylabel("Price ($)")
    ax.set_title("Live Stock Prices")
    ax.legend(loc="upper left")
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M:%S"))
    fig.autofmt_xdate()

    def update(_frame) -> list:
        with lock:
            snapshot = {t: list(d) for t, d in data.items()}

        for t, line in lines.items():
            points = snapshot[t]
            if not points:
                continue
            times, prices = zip(*points)
            line.set_data(mdates.date2num(times), prices)

        ax.relim()
        ax.autoscale_view()
        return list(lines.values())

    ani = animation.FuncAnimation(fig, update, interval=DELAY, blit=False)

    plt.tight_layout()
    plt.show()



if __name__ == "__main__":
    show_live_chart()