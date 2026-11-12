"""Smoke test: runs the full agent pipeline on a small synthetic CICIDS-shaped
dataset to confirm the code imports and executes end to end. It does NOT
measure detection quality."""
import numpy as np
import pandas as pd

from utils.preprocess import preprocess
from agents.monitoring_agent import MonitoringAgent
from agents.detection_agent import DetectionAgent
from agents.decision_agent import DecisionAgent
from agents.response_agent import ResponseAgent
from agents.learning_agent import LearningAgent


def _synthetic_df(n=400, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(rng.normal(size=(n, 6)),
                      columns=[" Flow Duration", " Total Fwd Packets", "Flow Bytes/s",
                               " Fwd Packet Length Max", " Bwd Packet Length Min", " Flow IAT Mean"])
    labels = np.where(rng.random(n) < 0.3, "DDoS", "BENIGN")
    df.loc[labels == "DDoS", " Flow Duration"] += 3  # make the classes separable
    df[" Label"] = labels
    df.iloc[0, 2] = np.inf  # exercises the inf/NaN cleanup path
    return df


def test_agent_pipeline_runs():
    X, y = preprocess(_synthetic_df())
    assert X.shape[0] == len(y) and X.shape[1] == 6

    monitor, detector, decision, response, learning = (
        MonitoringAgent(), DetectionAgent(), DecisionAgent(), ResponseAgent(), LearningAgent())

    monitor.train(X)
    assert len(monitor.monitor(X)) == 10

    detector.train(X, y)
    probs = detector.detect(X)
    assert probs.shape == (len(y),) and ((probs >= 0) & (probs <= 1)).all()

    decision.train(probs, y)
    decisions = decision.evaluate(probs)
    response.train(probs, decisions, y)
    actions = response.act(probs, decisions)
    assert set(actions) <= set(response.actions)

    learning.improve(detector, X, y)
