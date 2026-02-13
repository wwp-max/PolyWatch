import pandas as pd
import numpy as np


class ZScoreDetector:
    def __init__(self, window: int = 30, threshold: float = 2.5):
        """
        window: rolling window size
        threshold: z-score cutoff
        """
        self.window = window
        self.threshold = threshold

    def detect(self, price_series: pd.Series) -> pd.DataFrame:
        """
        Returns DataFrame with z-score and anomaly flag
        """
        rolling_mean = price_series.rolling(self.window).mean()
        rolling_std = price_series.rolling(self.window).std()

        z_scores = (price_series - rolling_mean) / rolling_std

        result = pd.DataFrame({
            "price": price_series,
            "z_score": z_scores,
            "is_anomaly": np.abs(z_scores) > self.threshold
        })

        return result

if __name__ == "__main__":
    import pandas as pd
    import numpy as np

    # 生成模拟价格数据
    np.random.seed(42)
    prices = pd.Series(np.random.normal(100, 1, 200))

    # 注入异常 spike
    prices.iloc[120] += 10

    detector = ZScoreDetector(window=20, threshold=2.5)
    result = detector.detect(prices)

    print("Anomalies detected:", result["is_anomaly"].sum())
    print(result[result["is_anomaly"] == True])

