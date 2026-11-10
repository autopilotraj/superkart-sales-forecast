import json
import joblib
import pandas as pd
from flask import Flask, request, jsonify

superkart_api = Flask("SuperKart")

# Load the saved pipeline (preprocessing + model) and its record file
model = joblib.load("superkart_model.joblib")
with open("model_info.json") as f:
    model_info = json.load(f)

FEATURES = model_info["features"]
NUMERIC = ["Product_Weight", "Product_Allocated_Area", "Product_MRP", "Store_Age_Years"]


def review_reasons(row):
    """Reasons a forecast should be checked by a planner before it is used."""
    reasons = []
    if row["Store_Type"] in model_info["review_store_types"]:
        reasons.append("Food Mart forecasts have higher error")
    if row["Store_Type"] not in model_info["known_store_types"]:
        reasons.append("Store type not seen in training")
    for col, (low, high) in model_info["training_ranges"].items():
        if not low <= row[col] <= high:
            reasons.append(f"{col} outside training range")
    return reasons


@superkart_api.get("/")
def home():
    return jsonify({"message": "Welcome to the SuperKart Sales Forecasting API",
                    "model_version": model_info["model_version"],
                    "trained_on": model_info["trained_on"],
                    "test_metrics": model_info["test_metrics"]})


# Prediction for a single product
@superkart_api.post("/v1/predict")
def predict_sales():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    missing = [col for col in FEATURES if col not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    try:
        sample = {col: data[col] for col in FEATURES}
        for col in NUMERIC:
            sample[col] = float(sample[col])
    except (TypeError, ValueError):
        return jsonify({"error": f"These fields must be numbers: {NUMERIC}"}), 400

    prediction = model.predict(pd.DataFrame([sample]))[0]
    reasons = review_reasons(sample)
    return jsonify({"Sales": round(float(prediction), 2),
                    "Needs_Review": len(reasons) > 0,
                    "Review_Reasons": reasons,
                    "model_version": model_info["model_version"]})


# Prediction for a batch of products sent as a CSV file
@superkart_api.post("/v1/predictbatch")
def predict_sales_batch():
    if "file" not in request.files:
        return jsonify({"error": "Upload a CSV file using the field name 'file'"}), 400

    input_data = pd.read_csv(request.files["file"])
    missing = [col for col in FEATURES if col not in input_data.columns]
    if missing:
        return jsonify({"error": f"Missing columns: {missing}"}), 400

    try:
        input_data[NUMERIC] = input_data[NUMERIC].astype(float)
    except ValueError:
        return jsonify({"error": f"These columns must be numbers: {NUMERIC}"}), 400

    predictions = model.predict(input_data[FEATURES])
    return jsonify({str(i): round(float(p), 2) for i, p in enumerate(predictions)})


if __name__ == "__main__":
    superkart_api.run(debug=True)
