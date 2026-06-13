import numpy as np

try:
    from xgboost import XGBClassifier
    USE_XGB = True
except:
    from sklearn.ensemble import HistGradientBoostingClassifier
    USE_XGB = False


class DetectionAgent:

    def __init__(self):

        if USE_XGB:
            self.model = XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                eval_metric='logloss',
                use_label_encoder=False
            )
        else:
            self.model = HistGradientBoostingClassifier(
                max_iter=100,
                learning_rate=0.1,
                max_depth=6
            )

    def train(self, X, y):
        print("Detection Agent: Training advanced model...")
        self.model.fit(X, y)

    def detect(self, X):
        probs = self.model.predict_proba(X)[:, 1]
        return probs