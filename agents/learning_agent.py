import numpy as np

class LearningAgent:

    def improve(self, detector, X, y):

        print("Learning Agent: Improving using hard samples...")

        # Get predictions
        preds = detector.model.predict(X)

        # Find errors
        errors = preds != y

        X_hard = X[errors]
        y_hard = y[errors]

        if len(X_hard) == 0:
            print("No errors found. Model already good.")
            return

        # Combine old + hard samples
        sample_size = min(20000, len(X))
        idx = np.random.choice(len(X), sample_size, replace=False)

        X_base = X[idx]
        y_base = y.iloc[idx] if hasattr(y, "iloc") else y[idx]

        X_new = np.vstack((X_base, X_hard))
        y_new = np.hstack((y_base, y_hard))

        # Retrain
        detector.model.fit(X_new, y_new)

        print(f"Learning complete. Used {len(X_hard)} hard samples.")