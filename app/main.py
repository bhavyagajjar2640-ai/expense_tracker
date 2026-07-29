import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from app.database.connection import init_db
from app.routers.users import render_account_sidebar, render_login_signup
from app.services.user_service import (
    delete_rows_from_document,
    load_document_history,
    load_latest_document,
    normalize_expense_dataframe,
    read_uploaded_dataframe,
    replace_active_document,
    save_uploaded_document,
    records_to_dataframe,
)


st.set_page_config(page_title="Expense Tracker", layout="wide")


def logout():
    st.session_state.pop("user", None)
    st.session_state.pop("user_id", None)
    st.session_state.pop("document_id", None)
    st.session_state.pop("document_name", None)
    st.session_state.pop("document_format", None)
    st.session_state.pop("dataframe", None)
    st.rerun()


def ensure_session_document():
    if "user_id" not in st.session_state:
        return
    if "dataframe" in st.session_state and st.session_state.dataframe is not None:
        return

    latest = load_latest_document(st.session_state.user_id)
    if latest:
        st.session_state.document_id = latest["id"]
        st.session_state.document_name = latest["filename"]
        st.session_state.document_format = latest["file_format"]
        st.session_state.dataframe = records_to_dataframe(latest["data_json"])


def render_dashboard():
    ensure_session_document()
    user_name = st.session_state.user
    user_id = st.session_state.user_id
    current_doc_id = st.session_state.get("document_id")

    st.title("💸 Expense Tracker Dashboard")
    st.caption(f"Logged in as {user_name}")

    if render_account_sidebar(user_name):
        logout()

    history = load_document_history(user_id)
    latest = load_latest_document(user_id)

    if latest and "dataframe" not in st.session_state:
        st.session_state.document_id = latest["id"]
        st.session_state.document_name = latest["filename"]
        st.session_state.document_format = latest["file_format"]
        st.session_state.dataframe = records_to_dataframe(latest["data_json"])

    if latest:
        st.info(
            f"Latest saved file: {latest['filename']} | Rows: {latest['row_count']} | "
            f"Uploaded: {pd.to_datetime(latest['uploaded_at']).strftime('%Y-%m-%d %H:%M')}"
        )
    else:
        st.warning("No document has been saved yet for this user.")

    with st.expander("Upload New Document", expanded=True):
        uploaded_file = st.file_uploader(
            "Upload a new CSV or Excel expense document",
            type=["csv", "xlsx", "xls"],
            key=f"uploader_{user_id}",
        )
        if uploaded_file is not None:
            try:
                uploaded_df, file_format = read_uploaded_dataframe(uploaded_file)
                st.dataframe(uploaded_df, use_container_width=True)
                if st.button("Save Uploaded Document to DB"):
                    saved_doc = save_uploaded_document(user_id, uploaded_file, uploaded_df, file_format)
                    st.session_state.document_name = uploaded_file.name
                    st.session_state.document_format = file_format
                    st.session_state.dataframe = uploaded_df
                    if saved_doc:
                        st.session_state.document_id = saved_doc["id"]
                    st.success("Document saved to PostgreSQL.")
                    st.rerun()
            except Exception as exc:
                st.error(f"Could not read the uploaded file: {exc}")

    if "dataframe" not in st.session_state or st.session_state.dataframe is None:
        st.info("Upload a document to start.")
        with st.expander("Saved Document History", expanded=False):
            if history:
                history_df = pd.DataFrame(history)
                history_df["uploaded_at"] = pd.to_datetime(history_df["uploaded_at"]).dt.strftime("%Y-%m-%d %H:%M")
                st.dataframe(history_df, use_container_width=True, hide_index=True)
            else:
                st.info("No saved documents yet.")
        return

    df = normalize_expense_dataframe(st.session_state.dataframe)
    st.session_state.dataframe = df.copy()

    st.sidebar.header("Filtering")
    filtered = df.copy()
    if not filtered.empty:
        date_min = pd.to_datetime(filtered["Date"]).min().date()
        date_max = pd.to_datetime(filtered["Date"]).max().date()
        date_range = st.sidebar.date_input("Select Date Range", [date_min, date_max])

        selected_categories = st.sidebar.multiselect(
            "Category",
            sorted(filtered["Category"].dropna().astype(str).unique().tolist()),
            default=sorted(filtered["Category"].dropna().astype(str).unique().tolist()),
        )

        if "City" in filtered.columns:
            selected_cities = st.sidebar.multiselect(
                "City",
                sorted(filtered["City"].dropna().astype(str).unique().tolist()),
                default=sorted(filtered["City"].dropna().astype(str).unique().tolist()),
            )
        else:
            selected_cities = []

        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1])
        filtered = filtered[
            (pd.to_datetime(filtered["Date"]).between(start_date, end_date))
            & (filtered["Category"].astype(str).isin(selected_categories))
        ]
        if "City" in filtered.columns and selected_cities:
            filtered = filtered[filtered["City"].astype(str).isin(selected_cities)]

    st.subheader("Insights")
    if not filtered.empty:
        highest_row = filtered.loc[filtered["Amount"].idxmax()]
        total = filtered["Amount"].sum()
        average = filtered["Amount"].mean()
        top_category = filtered.groupby("Category")["Amount"].sum().idxmax()
        top_city = "N/A"
        if "City" in filtered.columns and not filtered["City"].dropna().empty:
            top_city = filtered.groupby("City")["Amount"].sum().idxmax()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total", f"₹{round(total, 2)}")
        c2.metric("Average", f"₹{round(average, 2)}")
        c3.metric("Top Category", top_category)
        c4.metric("Top City", top_city)
        st.info(
            f"Highest expense: ₹{highest_row['Amount']} | "
            f"Date: {pd.to_datetime(highest_row['Date']).date()} | "
            f"Category: {highest_row['Category']}"
        )
    else:
        st.warning("No rows match the current filters.")

    st.divider()
    st.subheader("CRUD Operations")
    with st.form("add_expense_form", clear_on_submit=True):
        form_cols = st.columns(4)
        new_date = form_cols[0].date_input("Date")
        
        # Get unique categories from existing data, plus some defaults
        existing_categories = []
        if "Category" in df.columns:
            existing_categories = df["Category"].dropna().unique().tolist()
        default_categories = ["Food", "Transport", "Shopping", "Entertainment", "Utilities", "Health", "Other"]
        all_categories = sorted(list(set(existing_categories + default_categories)))
        
        new_category = form_cols[1].selectbox("Category", options=all_categories)
        new_amount = form_cols[2].number_input("Amount", min_value=0.01, step=1.0)
        
        has_city = "City" in df.columns
        has_desc = "Description" in df.columns
        new_city = form_cols[3].text_input("City") if has_city else ""
        new_description = st.text_input("Description") if has_desc else ""
        add_clicked = st.form_submit_button("Add Row")

    if add_clicked:
        errors = []
        if not new_category:
            errors.append("Category is required.")
        if new_amount <= 0:
            errors.append("Amount must be greater than 0.")
        if has_city and not new_city.strip():
            errors.append("City is required.")
        if has_desc and not new_description.strip():
            errors.append("Description is required.")
            
        if errors:
            for e in errors:
                st.error(e)
        else:
            new_row = {
                "Date": pd.to_datetime(new_date),
                "Category": new_category.strip(),
                "Amount": float(new_amount),
            }
            if has_city:
                new_row["City"] = new_city.strip()
            if has_desc:
                new_row["Description"] = new_description.strip()
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.dataframe = df
            if current_doc_id:
                replace_active_document(user_id, current_doc_id, df)
            st.success("Expense added.")
            st.rerun()

    edited_source = filtered if not filtered.empty else df
    st.subheader("Edit Expenses")
    edited_df = st.data_editor(
        edited_source,
        use_container_width=True,
        num_rows="dynamic",
        key="editor",
    )

    action_cols = st.columns(3)
    with action_cols[0]:
        if st.button("Save Edits to DB"):
            if current_doc_id is None:
                st.error("No active document found.")
            else:
                normalized = normalize_expense_dataframe(edited_df)
                replace_active_document(user_id, current_doc_id, normalized)
                st.session_state.dataframe = normalized
                st.success("Changes saved to PostgreSQL.")
                st.rerun()
    with action_cols[1]:
        delete_indexes = st.multiselect(
            "Select row indexes to delete",
            options=list(edited_df.index),
            default=[],
        )
    with action_cols[2]:
        if st.button("Delete Selected Rows"):
            if current_doc_id is None:
                st.error("No active document found.")
            elif not delete_indexes:
                st.warning("Select at least one row index to delete.")
            else:
                remaining = delete_rows_from_document(user_id, current_doc_id, delete_indexes)
                st.session_state.dataframe = remaining
                st.success("Rows deleted.")
                st.rerun()

    if latest:
        file_bytes = bytes(latest["file_bytes"])
        file_name = latest["filename"]
        mime = "text/csv" if latest["file_format"] == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        st.download_button(
            "Download Current Saved File",
            data=file_bytes,
            file_name=file_name,
            mime=mime,
        )

    st.divider()
    st.subheader("Charts")
    if filtered.empty:
        st.warning("No rows available for charts.")
    else:
        col1, col2 = st.columns(2)
        category_totals = filtered.groupby("Category")["Amount"].sum().sort_values(ascending=False)
        with col1:
            st.caption("Category-wise Expense")
            fig, ax = plt.subplots()
            category_totals.plot(kind="bar", ax=ax)
            ax.set_xlabel("Category")
            ax.set_ylabel("Amount")
            st.pyplot(fig)

        with col2:
            st.caption("Expense Distribution")
            fig2, ax2 = plt.subplots()
            category_totals.plot.pie(autopct="%1.1f%%", ax=ax2)
            ax2.set_ylabel("")
            st.pyplot(fig2)

        st.caption("Monthly Trend")
        trend_df = filtered.copy()
        trend_df["Month"] = pd.to_datetime(trend_df["Date"]).dt.to_period("M")
        monthly = trend_df.groupby("Month")["Amount"].sum()
        fig3, ax3 = plt.subplots()
        monthly.plot(marker="o", ax=ax3)
        ax3.set_xlabel("Month")
        ax3.set_ylabel("Amount")
        st.pyplot(fig3)

    st.divider()
    st.subheader("Data Table and Download")
    st.dataframe(filtered if not filtered.empty else df, use_container_width=True)
    csv = (filtered if not filtered.empty else df).to_csv(index=False).encode("utf-8")
    st.download_button("Download Filtered CSV", csv, "filtered_expenses.csv", "text/csv")

    with st.expander("Saved Document History", expanded=False):
        if history:
            history_df = pd.DataFrame(history)
            history_df["uploaded_at"] = pd.to_datetime(history_df["uploaded_at"]).dt.strftime("%Y-%m-%d %H:%M")
            st.dataframe(history_df, use_container_width=True, hide_index=True)
        else:
            st.info("No saved documents yet.")


def main():
    init_db()

    if "user" not in st.session_state:
        render_login_signup()
        st.stop()

    render_dashboard()


if __name__ == "__main__":
    main()
