from utils.preprocess import load_data, preprocess

from agents.monitoring_agent import MonitoringAgent
from agents.detection_agent import DetectionAgent
from agents.decision_agent import DecisionAgent
from agents.response_agent import ResponseAgent
from agents.learning_agent import LearningAgent

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from imblearn.over_sampling import SMOTE
import numpy as np


print("\n🔹 Loading dataset...")
df = load_data("data")
X, y = preprocess(df)

print(f"Dataset shape: {X.shape}")

# SPLIT
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print("\n🔹 Applying SMOTE...")
smote = SMOTE(sampling_strategy=0.5, k_neighbors=2, random_state=42)
X_train, y_train = smote.fit_resample(X_train, y_train)


# INIT AGENTS
monitor = MonitoringAgent()
detector = DetectionAgent()
decision = DecisionAgent()
response = ResponseAgent()
learning = LearningAgent()


# TRAINING PHASE
print("\n🔹 TRAINING PHASE")

monitor.train(X_train)

detector.train(X_train, y_train)

train_probs = detector.detect(X_train)

decision.train(train_probs, y_train)

train_decisions = decision.evaluate(train_probs)

response.train(train_probs, train_decisions, y_train)

learning.improve(detector, X_train, y_train)


# TESTING PHASE
print("\n🔹 TESTING PHASE")

X_filtered = monitor.collect(X_test)

probs = detector.detect(X_filtered)

print("\n📊 Detection Scores (sample):")
print(probs[:10])

decisions = decision.evaluate(probs)

print("\n🧠 Decision Output (sample):")
print(decisions[:10])

print("\n🚨 Response Actions:")
actions = response.act(probs, decisions)

# FINAL PREDICTION
y_pred = np.array(decisions)

print("\n📈 Confusion Matrix:")
print(confusion_matrix(y_test[:len(y_pred)], y_pred))

print("\n📊 Classification Report:")
print(classification_report(y_test[:len(y_pred)], y_pred))