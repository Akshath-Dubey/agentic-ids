import streamlit as st
import pandas as pd
import numpy as np

from utils.preprocess import preprocess
from agents.monitoring_agent import MonitoringAgent
from agents.detection_agent import DetectionAgent
from agents.decision_agent import DecisionAgent
from agents.response_agent import ResponseAgent
from agents.learning_agent import LearningAgent

from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("⚡ Smart Grid IDS Dashboard")

# ---------- LOG SYSTEM ----------
if "logs" not in st.session_state:
    st.session_state.logs = []

def log(msg):
    st.session_state.logs.append(msg)

# ---------- TOP BAR ----------
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    files = st.file_uploader(
        "Upload CICIDS CSV Files",
        type=["csv"],
        accept_multiple_files=True
    )

with col2:
    threshold = st.slider("Sensitivity", 0.0, 1.0, 0.7)

with col3:
    auto_learn = st.checkbox("Auto Learn", value=True)

# ---------- MAIN ----------
if files:

    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

    st.subheader("📄 Dataset Preview")
    st.dataframe(df.head())

    # SPEED OPTIMIZATION
    df = df.sample(n=min(len(df), 40000), random_state=42)

    X, y = preprocess(df)

    st.success(f"Processed Data Shape: {X.shape}")

    # ---------- LOAD AGENTS ----------
    @st.cache_resource
    def load_agents(X, y):

        monitor = MonitoringAgent()
        detector = DetectionAgent()
        decision = DecisionAgent()
        response = ResponseAgent()
        learning = LearningAgent()

        log("Training Monitoring Agent...")
        if hasattr(monitor, "train"):
            monitor.train(X)

        log("Training Detection Agent...")
        detector.train(X, y)

        probs = detector.detect(X)

        log("Training Decision Agent...")
        decision.train(probs, y)

        dec = decision.evaluate(probs)

        log("Training Response Agent...")
        response.train(probs, dec, y)

        return monitor, detector, decision, response, learning

    monitor, detector, decision, response, learning = load_agents(X, y)

    # ---------- RUN SYSTEM ----------
    if st.button("🚀 Run System"):

        st.session_state.logs = []
        log("System started")

        # -------- MONITOR --------
        log("Monitoring traffic...")
        monitor_logs = monitor.monitor(X)

        # -------- DETECT --------
        log("Running detection model...")
        probs = detector.detect(X)

        # -------- DECISION --------
        log(f"Applying threshold: {threshold}")
        decision.threshold = threshold
        decisions = decision.evaluate(probs)

        # -------- RESPONSE --------
        log("Generating response actions...")
        actions = response.act(probs, decisions)

        # -------- LEARNING --------
        if auto_learn:
            log("Learning agent improving model...")
            learning.improve(detector, X, y)
            st.success("✅ Model improved using Learning Agent")
            log("Model updated")

        # ---------- UI TABS ----------
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "🛰 Monitoring", "🧠 Detection", "⚖ Decision",
            "🚨 Response", "📊 Metrics", "🖥 Logs"
        ])

        # ---------- MONITOR ----------
        with tab1:
            if monitor_logs:
                st.dataframe(pd.DataFrame(monitor_logs))
            else:
                st.warning("No monitoring data")

        # ---------- DETECTION ----------
        with tab2:
            st.dataframe(pd.DataFrame({
                "Flow": range(20),
                "Attack Probability": probs[:20]
            }))

        # ---------- DECISION ----------
        with tab3:
            st.dataframe(pd.DataFrame({
                "Flow": range(20),
                "Decision": ["Attack" if d else "Normal" for d in decisions[:20]]
            }))

        # ---------- RESPONSE ----------
        with tab4:
            st.dataframe(pd.DataFrame({
                "Flow": range(20),
                "Action": actions[:20]
            }))

        # ---------- METRICS ----------
        with tab5:

            st.subheader("📊 Performance Evaluation")

            st.markdown(f"""
- Samples: **{len(decisions)}**
- Threshold: **{threshold}**
""")

            cm = confusion_matrix(y[:len(decisions)], decisions)
            tn, fp, fn, tp = cm.ravel()

            colA, colB = st.columns([1, 2])

            # CONFUSION MATRIX
            with colA:
                fig, ax = plt.subplots(figsize=(3, 3))
                ax.imshow(cm)

                for i in range(len(cm)):
                    for j in range(len(cm)):
                        ax.text(j, i, cm[i, j], ha='center', va='center')

                ax.set_xlabel("Predicted")
                ax.set_ylabel("Actual")

                st.pyplot(fig)

            with colB:
                st.markdown(f"""
TP: {tp}  
TN: {tn}  
FP: {fp} ❌ False Alarm  
FN: {fn} ❌ Missed Attack  
""")
                st.text(classification_report(y[:len(decisions)], decisions))

            # ---------- TPR & FPR CURVES ----------
            st.subheader("📈 TPR & FPR vs Threshold")

            thresholds = np.linspace(0, 1, 50)
            tpr_list = []
            fpr_list = []

            y_true = y[:len(probs)]

            for t in thresholds:
                preds = (probs >= t).astype(int)

                cm_temp = confusion_matrix(y_true, preds)
                tn, fp, fn, tp = cm_temp.ravel()

                tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
                fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

                tpr_list.append(tpr)
                fpr_list.append(fpr)

            col1, col2 = st.columns(2)

            # TPR GRAPH
            with col1:
                fig_tpr, ax_tpr = plt.subplots(figsize=(4, 3))
                ax_tpr.plot(thresholds, tpr_list)
                ax_tpr.axvline(x=threshold)

                ax_tpr.set_title("True Positive Rate")
                ax_tpr.set_xlabel("Threshold")
                ax_tpr.set_ylabel("TPR")

                st.pyplot(fig_tpr)

            # FPR GRAPH
            with col2:
                fig_fpr, ax_fpr = plt.subplots(figsize=(4, 3))
                ax_fpr.plot(thresholds, fpr_list)
                ax_fpr.axvline(x=threshold)

                ax_fpr.set_title("False Positive Rate")
                ax_fpr.set_xlabel("Threshold")
                ax_fpr.set_ylabel("FPR")

                st.pyplot(fig_fpr)

        # ---------- LOGS ----------
        with tab6:
            st.text("\n".join(st.session_state.logs[-50:]))

        log("System execution completed")

# ---------- GLOBAL LOG ----------
st.subheader("🖥️ System Logs")
st.text_area("Logs", "\n".join(st.session_state.logs[-30:]), height=200)