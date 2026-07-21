from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("expense_tracker_api")

from app.database.connection import init_db
from app.services.user_service import (
    authenticate_user,
    register_user,
    load_latest_document,
    records_to_dataframe,
    normalize_expense_dataframe,
    replace_active_document,
    save_uploaded_document
)
from typing import Optional

app = FastAPI(title="Expense Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"API Called: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"API Error: {request.method} {request.url.path} - Error: {str(e)} - Time: {process_time:.4f}s", exc_info=True)
        raise e

@app.on_event("startup")
def on_startup():
    init_db()

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class ExpenseCreate(BaseModel):
    date: str
    category: str
    amount: float
    description: Optional[str] = None
    city: Optional[str] = None

class DummyUpload:
    @property
    def name(self):
        return "mobile_data.csv"
    def getvalue(self):
        return b""

@app.post("/api/login")
def login(req: LoginRequest):
    user = authenticate_user(req.username, req.password)
    if not user:
        logger.warning(f"Failed login attempt for username: {req.username}")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"message": "Login successful", "user": {"id": user["id"], "username": user["username"]}}

@app.post("/api/register")
def register(req: RegisterRequest):
    try:
        register_user(req.username, req.password)
        logger.info(f"Successfully registered new user: {req.username}")
        return {"message": "Registration successful"}
    except ValueError as e:
        logger.warning(f"Registration failed for username {req.username}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/dashboard/{user_id}")
def get_dashboard(user_id: int):
    latest = load_latest_document(user_id)
    if not latest:
        return {"has_data": False, "message": "No document has been saved yet."}
    
    df = records_to_dataframe(latest["data_json"])
    df = normalize_expense_dataframe(df)
    
    if df.empty:
        return {"has_data": False, "message": "Document is empty."}
        
    total = float(df["Amount"].sum())
    average = float(df["Amount"].mean())
    top_category = df.groupby("Category")["Amount"].sum().idxmax()
    top_city = "N/A"
    if "City" in df.columns and not df["City"].dropna().empty:
        top_city = df.groupby("City")["Amount"].sum().idxmax()
        
    highest_row = df.loc[df["Amount"].idxmax()]
    
    # Calculate category totals for a chart
    category_totals = df.groupby("Category")["Amount"].sum().sort_values(ascending=False).to_dict()
    
    return {
        "has_data": True,
        "metrics": {
            "total": total,
            "average": average,
            "top_category": top_category,
            "top_city": top_city,
        },
        "highest_expense": {
            "amount": float(highest_row["Amount"]),
            "date": pd.to_datetime(highest_row["Date"]).strftime("%Y-%m-%d"),
            "category": highest_row["Category"]
        },
        "category_totals": category_totals
    }

@app.get("/api/expenses/{user_id}")
def get_expenses(user_id: int):
    latest = load_latest_document(user_id)
    if not latest:
        return {"expenses": []}
        
    df = records_to_dataframe(latest["data_json"])
    df = normalize_expense_dataframe(df)
    
    if df.empty:
        return {"expenses": []}
    
    # Return expenses sorted by Date descending
    df_sorted = df.sort_values(by="Date", ascending=False)
    
    expenses = []
    for idx, row in df_sorted.iterrows():
        expense = {
            "id": int(idx),
            "date": pd.to_datetime(row["Date"]).strftime("%Y-%m-%d"),
            "category": row["Category"],
            "amount": float(row["Amount"]),
        }
        if "City" in df_sorted.columns and not pd.isna(row["City"]):
             expense["city"] = row["City"]
        if "Description" in df_sorted.columns and not pd.isna(row["Description"]):
             expense["description"] = row["Description"]
             
        expenses.append(expense)
        
    return {"expenses": expenses}

@app.post("/api/expenses/{user_id}")
def create_expense(user_id: int, exp: ExpenseCreate):
    latest = load_latest_document(user_id)
    if not latest:
        df = pd.DataFrame(columns=["Date", "Category", "Amount", "City", "Description"])
        latest = save_uploaded_document(user_id, DummyUpload(), df, "csv")
    else:
        df = records_to_dataframe(latest["data_json"])
        df = normalize_expense_dataframe(df)

    new_row = {
        "Date": pd.to_datetime(exp.date),
        "Category": exp.category,
        "Amount": exp.amount,
    }
    if exp.city is not None: new_row["City"] = exp.city
    if exp.description is not None: new_row["Description"] = exp.description

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    replace_active_document(user_id, latest["id"], df)
    return {"message": "Expense created successfully"}

@app.put("/api/expenses/{user_id}/{expense_id}")
def update_expense(user_id: int, expense_id: int, exp: ExpenseCreate):
    latest = load_latest_document(user_id)
    if not latest:
        raise HTTPException(status_code=404, detail="No document found")
        
    df = records_to_dataframe(latest["data_json"])
    df = normalize_expense_dataframe(df)
    
    if expense_id not in df.index:
        raise HTTPException(status_code=404, detail="Expense not found")
        
    df.at[expense_id, "Date"] = pd.to_datetime(exp.date)
    df.at[expense_id, "Category"] = exp.category
    df.at[expense_id, "Amount"] = exp.amount
    if exp.city is not None: df.at[expense_id, "City"] = exp.city
    if exp.description is not None: df.at[expense_id, "Description"] = exp.description
    
    replace_active_document(user_id, latest["id"], df)
    return {"message": "Expense updated successfully"}

@app.delete("/api/expenses/{user_id}/{expense_id}")
def delete_expense(user_id: int, expense_id: int):
    latest = load_latest_document(user_id)
    if not latest:
        raise HTTPException(status_code=404, detail="No document found")
        
    df = records_to_dataframe(latest["data_json"])
    df = normalize_expense_dataframe(df)
    
    if expense_id not in df.index:
        raise HTTPException(status_code=404, detail="Expense not found")
        
    df = df.drop(index=expense_id).reset_index(drop=True)
    replace_active_document(user_id, latest["id"], df)
    return {"message": "Expense deleted successfully"}
