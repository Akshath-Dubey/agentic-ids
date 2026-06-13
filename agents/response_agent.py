import numpy as np
from sklearn.ensemble import RandomForestClassifier

class ResponseAgent:

    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.actions = ["ALLOW", "MONITOR", "RATE_LIMIT", "BLOCK", "ALERT"]

    def train(self, probs, decisions, y):

        X = np.column_stack((probs, decisions))

        y_actions = []

        for p, d in zip(probs, decisions):
            if d == 0:
                y_actions.append(0)
            else:
                if p > 0.9:
                    y_actions.append(4)
                elif p > 0.75:
                    y_actions.append(3)
                elif p > 0.6:
                    y_actions.append(2)
                else:
                    y_actions.append(1)

        self.model.fit(X, y_actions)

    def act(self, probs, decisions):
        X = np.column_stack((probs, decisions))
        preds = self.model.predict(X)
        return [self.actions[p] for p in preds]