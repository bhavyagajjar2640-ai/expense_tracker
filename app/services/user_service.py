import io

import bcrypt
import pandas as pd

from app.repository.users_repository import (
    create_document,
    create_user as repo_create_user,
    deactivate_active_documents,
    find_user_by_username,
    get_document_by_id,
    get_latest_active_document,
    list_documents,
    update_document_fields,
)


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password, hashed):
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def authenticate_user(username, password):
    user = find_user_by_username(username)
    if user and check_password(password, user["password_hash"]):
        return user
    return None


from sqlalchemy.exc import IntegrityError, DataError, SQLAlchemyError

def register_user(username, password):
    if find_user_by_username(username):
        raise ValueError("User already exists.")
    try:
        repo_create_user(username, hash_password(password))
    except IntegrityError:
        raise ValueError("User already exists.")
    except SQLAlchemyError as exc:
        raise RuntimeError(f"Database error during registration: {exc}")


def infer_file_format(filename):
    lowered = filename.lower()
    if lowered.endswith(".csv"):
        return "csv"
    if lowered.endswith(".xlsx") or lowered.endswith(".xls"):
        return "xlsx"
    return "csv"


def read_uploaded_dataframe(uploaded_file):
    file_format = infer_file_format(uploaded_file.name)
    raw = io.BytesIO(uploaded_file.getvalue())

    try:
        if file_format == "csv":
            df = pd.read_csv(raw)
        else:
            df = pd.read_excel(raw)
    except pd.errors.ParserError:
        raise ValueError("The uploaded file is not a valid CSV or Excel format.")
    except Exception as exc:
        raise ValueError(f"Failed to read file: {exc}")

    required = {"Date", "Category", "Amount"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    df = df.dropna(subset=["Date", "Category", "Amount"]).copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    df = df.dropna(subset=["Date", "Amount", "Category"]).copy()
    df["Category"] = df["Category"].astype(str)

    if "City" in df.columns:
        df["City"] = df["City"].astype(str)

    return df.reset_index(drop=True), file_format


def dataframe_to_records(df):
    export_df = df.copy()
    if "Date" in export_df.columns:
        export_df["Date"] = pd.to_datetime(export_df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    export_df = export_df.where(pd.notnull(export_df), None)
    return export_df.to_dict(orient="records")


def records_to_dataframe(records):
    if not records:
        return pd.DataFrame(columns=["Date", "Category", "Amount"])

    df = pd.DataFrame(records)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if "Amount" in df.columns:
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    return df


def normalize_expense_dataframe(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["Date", "Category", "Amount"])

    normalized = df.copy()
    if "Date" in normalized.columns:
        normalized["Date"] = pd.to_datetime(normalized["Date"], errors="coerce")
    if "Amount" in normalized.columns:
        normalized["Amount"] = pd.to_numeric(normalized["Amount"], errors="coerce")
    if "Category" in normalized.columns:
        normalized["Category"] = normalized["Category"].astype(str)
    if "City" in normalized.columns:
        normalized["City"] = normalized["City"].astype(str)
    return normalized.dropna(subset=["Date", "Amount", "Category"]).reset_index(drop=True)


def dataframe_to_file_bytes(df, file_format):
    output = io.BytesIO()
    if file_format == "csv":
        output.write(df.to_csv(index=False).encode("utf-8"))
    else:
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
    output.seek(0)
    return output.getvalue()


def save_uploaded_document(user_id, uploaded_file, df, file_format):
    try:
        deactivate_active_documents(user_id)
        return create_document(
            user_id=user_id,
            filename=uploaded_file.name,
            file_format=file_format,
            file_bytes=uploaded_file.getvalue(),
            data_json=dataframe_to_records(df),
            row_count=len(df),
            is_active=True,
        )
    except SQLAlchemyError as exc:
        raise ValueError(f"Database error while saving document: {exc}")


def replace_active_document(user_id, document_id, df):
    current = get_document_by_id(user_id, document_id)
    if not current:
        raise ValueError("Active document not found")

    try:
        return update_document_fields(
            user_id,
            document_id,
            data_json=dataframe_to_records(df),
            file_bytes=dataframe_to_file_bytes(df, current["file_format"]),
            row_count=len(df),
        )
    except SQLAlchemyError as exc:
        raise ValueError(f"Database error while updating document: {exc}")


def delete_rows_from_document(user_id, document_id, selected_indexes):
    current = get_document_by_id(user_id, document_id)
    if not current:
        raise ValueError("Active document not found")

    df = normalize_expense_dataframe(records_to_dataframe(current["data_json"]))
    remaining = df.drop(index=selected_indexes, errors="ignore").reset_index(drop=True)
    replace_active_document(user_id, document_id, remaining)
    return remaining


def load_latest_document(user_id):
    return get_latest_active_document(user_id)


def load_document_history(user_id):
    return list_documents(user_id)
