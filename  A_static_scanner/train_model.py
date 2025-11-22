# A_static_scanner/train_model.py
import json
import joblib
import os
from feature_extractor import extract_basic_features, features_to_vector
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import lightgbm as lgb
import numpy as np

DATA_PATH = "synthetic_samples.jsonl"
MODEL_OUT = "model_artifacts"
os.makedirs(MODEL_OUT, exist_ok=True)

# Read synthetic data
samples = []
with open(DATA_PATH, "r") as f:
    for line in f:
        samples.append(json.loads(line))

# build features
feat_list = []
labels = []
for s in samples:
    feats = extract_basic_features(s['url'], s['html'])
    feat_list.append(feats)
    labels.append(s['label'])

# choose feature order (must match extract)
feature_order = sorted(feat_list[0].keys())
X = [ [f[k] for k in feature_order] for f in feat_list ]
y = labels

X = np.array(X)
y = np.array(y)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

train_data = lgb.Dataset(X_train, label=y_train)
valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

params = {
    "objective": "binary",
    "metric": "auc",
    "verbosity": -1,
    "boosting_type": "gbdt",
    "num_leaves": 31,
    "learning_rate": 0.05,
    "seed": 42
}

bst = lgb.train(
    params, 
    train_data, 
    num_boost_round=200, 
    valid_sets=[valid_data], 
    callbacks=[lgb.early_stopping(stopping_rounds=20), lgb.log_evaluation(period=0)]
)

# Save model and metadata
joblib.dump(bst, os.path.join(MODEL_OUT, "lgb_model.joblib"))
joblib.dump(feature_order, os.path.join(MODEL_OUT, "feature_order.joblib"))
print("Model saved to", MODEL_OUT)

# Evaluate
y_pred_prob = bst.predict(X_test, num_iteration=bst.best_iteration)
print("ROC AUC:", roc_auc_score(y_test, y_pred_prob))
print(classification_report(y_test, (y_pred_prob > 0.5).astype(int)))
