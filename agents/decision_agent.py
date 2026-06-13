import numpy as np

class DecisionAgent:

    def __init__(self):
        self.threshold = 0.7

    def train(self, probs, y):

        best_thresh = 0.5
        best_score = 0

        for t in np.arange(0.3, 0.9, 0.05):
            preds = (probs > t).astype(int)

            tp = ((preds == 1) & (y == 1)).sum()
            fp = ((preds == 1) & (y == 0)).sum()
            fn = ((preds == 0) & (y == 1)).sum()

            precision = tp / (tp + fp + 1e-6)
            recall = tp / (tp + fn + 1e-6)

            f1 = 2 * (precision * recall) / (precision + recall + 1e-6)

            if f1 > best_score:
                best_score = f1
                best_thresh = t

        self.threshold = best_thresh
        print(f"Optimal Threshold Found: {self.threshold:.2f}")

    def evaluate(self, probs):
        return (probs > self.threshold).astype(int)