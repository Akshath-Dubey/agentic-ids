import numpy as np
from sklearn.ensemble import IsolationForest

class MonitoringAgent:

    def __init__(self):
        self.model = IsolationForest(contamination=0.1, random_state=42)

    def train(self, X):
        print("Monitoring Agent: Training anomaly detector...")
        self.model.fit(X)

    def monitor(self, X):

        preds = self.model.predict(X)  # -1 = anomaly, 1 = normal

        logs = []
        sample_size = min(10, len(X))

        for i in range(sample_size):
            logs.append({
                "Flow ID": i,
                "Anomaly Score": int(preds[i]),
                "Status": "Suspicious" if preds[i] == -1 else "Normal"
            })

        return logs