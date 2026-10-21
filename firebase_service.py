import os
from typing import Any

import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account


COLLECTION_NAME = "transactions"
SETTINGS_COLLECTION = "settings"
MONTHLY_GOAL_DOCUMENT = "monthly_goal"


@st.cache_resource
def get_firestore_client() -> firestore.Client:
    firebase_settings = st.secrets.get("firebase", {})
    service_account_info = st.secrets.get("gcp_service_account")
    project_id = (
        firebase_settings.get("project_id")
        or os.getenv("FIREBASE_PROJECT_ID")
        or (
            service_account_info.get("project_id")
            if service_account_info
            else None
        )
        or "despesas"
    )

    if service_account_info:
        credentials = service_account.Credentials.from_service_account_info(
            dict(service_account_info)
        )
        return firestore.Client(project=project_id, credentials=credentials)

    return firestore.Client(project=project_id)


def get_transactions(db: firestore.Client) -> list[dict[str, Any]]:
    query = db.collection(COLLECTION_NAME).order_by(
        "date", direction=firestore.Query.DESCENDING
    )
    transactions = []
    for document in query.stream():
        data = document.to_dict()
        transactions.append(
            {
                "id": document.id,
                "description": str(data.get("description", "")),
                "category": str(data.get("category", "")),
                "type": str(data.get("type", "Despesa")),
                "amount": float(data.get("amount", 0)),
                "date": str(data.get("date", "")),
            }
        )
    return transactions


def get_monthly_goal(db: firestore.Client) -> float:
    document = (
        db.collection(SETTINGS_COLLECTION)
        .document(MONTHLY_GOAL_DOCUMENT)
        .get()
    )
    if not document.exists:
        return 0.0
    return float(document.to_dict().get("amount", 0))


def set_monthly_goal(db: firestore.Client, amount: float) -> None:
    (
        db.collection(SETTINGS_COLLECTION)
        .document(MONTHLY_GOAL_DOCUMENT)
        .set({"amount": amount})
    )


def create_transaction(db: firestore.Client, transaction: dict[str, Any]) -> None:
    db.collection(COLLECTION_NAME).add(transaction)


def update_transaction(
    db: firestore.Client, transaction_id: str, transaction: dict[str, Any]
) -> None:
    db.collection(COLLECTION_NAME).document(transaction_id).update(transaction)


def delete_transaction(db: firestore.Client, transaction_id: str) -> None:
    db.collection(COLLECTION_NAME).document(transaction_id).delete()
