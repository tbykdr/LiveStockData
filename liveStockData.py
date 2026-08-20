import threading
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.dates as mdates
import yfinance as yf
from collections import deque
from datetime import datetime

class LiveStockData:
    def __init__(self, tickers: list[str], max_points: int = 200, delay: int = 500) -> None:
        self.tickers = tickers
        self.max_points = max_points
        self.delay = delay
        self.data = {t: deque(maxlen=max_points) for t in tickers}
        self.lock = threading.Lock()

    def seed_recent_history(self) -> None: #need to fix
        for t in self.tickers:
            try:
                hist = yf.Ticker(t).history(period="1d", interval="1m")
                hist = hist.tail(self.max_points)
                with self.lock:
                    for ts, row in hist.iterrows():
                        self.data[t].append((ts.to_pydatetime(), row["Close"]))
            except Exception as e:
                print(f"Could not load history for {t}: {e}")

    def message_handler(self, message: dict) -> None:
        # print("Received message")
        symbol = message.get("id")
        price = message.get("price")
        if symbol in self.data and price is not None:
            with self.lock:
                self.data[symbol].append((datetime.now(), price))

    def start_websocket(self) -> None:
        with yf.WebSocket() as ws:
            ws.subscribe(self.tickers)
            ws.listen(self.message_handler)

    def get_live_data(self) -> None:
        ws_thread = threading.Thread(target=self.start_websocket, daemon=True)
        ws_thread.start()

    def show_live_chart(self, do_seed_data: bool = False) -> None:
        if do_seed_data:
            self.seed_recent_history()

        self.get_live_data()

        fig, ax = plt.subplots(figsize=(10, 6))
        lines = {t: ax.plot([], [], label=t)[0] for t in self.tickers}

        ax.set_xlabel("Time")
        ax.set_ylabel("Price ($)")
        ax.set_title("Live Stock Prices")
        ax.legend(loc="upper left")
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M:%S"))
        fig.autofmt_xdate()

        def update(_frame) -> list:
            with self.lock:
                snapshot = {t: list(d) for t, d in self.data.items()}

            for t, line in lines.items():
                points = snapshot[t]
                if not points:
                    continue
                times, prices = zip(*points)
                line.set_data(mdates.date2num(times), prices)
            
            ax.relim()
            ax.autoscale_view()
            return list(lines.values())
            
        ani = animation.FuncAnimation(fig, update, interval=self.delay, blit=False)
            
        plt.tight_layout()
        plt.show()



if __name__ == "__main__":
    appleData = LiveStockData(tickers=["AAPL"], max_points=200, delay=500)
    appleData.show_live_chart()
