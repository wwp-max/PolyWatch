import pandas as pd


class WhaleAlert:
    def __init__(self, size_threshold: float = 200):
        """
        size_threshold: minimum trade size considered a whale trade
        """
        self.size_threshold = size_threshold

    def detect(self, trades: pd.DataFrame) -> pd.DataFrame:
        """
        trades DataFrame must contain a 'trade_size' column
        """
        return trades[trades["trade_size"] >= self.size_threshold]


if __name__ == "__main__":
    # 模拟交易数据
    trades = pd.DataFrame({
        "trade_id": range(10),
        "trade_size": [12, 45, 300, 22, 18, 410, 33, 27, 500, 19]
    })

    alert = WhaleAlert(size_threshold=200)
    whales = alert.detect(trades)

    print("Whale trades detected:")
    print(whales)
