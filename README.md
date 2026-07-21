# Expense Tracker

## Structure

```text
app/
├── main.py
├── routers/
│   └── users.py
├── repository/
│   └── users_repository.py
├── models/
│   └── user.py
├── services/
│   └── user_service.py
└── database/
    └── connection.py
```

## Run

```bash
streamlit run app.py
```

## Database

- PostgreSQL is used for login and per-user document storage.
- Set `DATABASE_URL` or `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`.
