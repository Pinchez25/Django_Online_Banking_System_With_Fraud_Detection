import pandas as pd


def detect_fraud(sender_cc_number, receiver_cc_number, amount)->bool:
    is_fraud = False
    model = pd.read_pickle('ml_model/fraud_detection_model.pickle')

    result = model.predict([[sender_cc_number, receiver_cc_number, amount]])

    if result[0] == 1:
        is_fraud = True
    else:
        is_fraud = False

    return is_fraud
