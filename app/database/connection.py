import os

import psycopg2
from psycopg2 import OperationalError, sql
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker
import streamlit as st

from app.models.user import Base


def get_db_config():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        parsed = make_url(database_url)
        return {
            "host": parsed.host or "localhost",
            "port": str(parsed.port or 5432),
            "dbname": parsed.database or "expense_tracker",
            "user": parsed.username or "postgres",
            "password": parsed.password or "",
            "url": database_url,
        }

    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": os.getenv("PGPORT", "5432"),
        "dbname": os.getenv("PGDATABASE", "expense_tracker"),
        "user": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", ""),
    }


def build_database_url(cfg):
    if cfg.get("url"):
        return cfg["url"]
    return str(
        URL.create(
            "postgresql+psycopg2",
            username=cfg["user"],
            password=cfg["password"],
            host=cfg["host"],
            port=int(cfg["port"]),
            database=cfg["dbname"],
        )
    )


def create_database_if_missing(cfg):
    dbname = cfg["dbname"]
    maintenance_cfg = dict(cfg)
    maintenance_cfg["dbname"] = "postgres"

    conn = psycopg2.connect(**maintenance_cfg)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            exists = cur.fetchone() is not None
            if not exists:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
    finally:
        conn.close()


@st.cache_resource
def get_engine():
    cfg = get_db_config()
    return create_engine(build_database_url(cfg), future=True, pool_pre_ping=True)


@st.cache_resource
def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def get_session():
    return get_session_factory()()


def init_db():
    cfg = get_db_config()
    try:
        Base.metadata.create_all(bind=get_engine())
    except OperationalError as exc:
        if "does not exist" in str(exc).lower():
            create_database_if_missing(cfg)
            get_engine.clear()
            get_session_factory.clear()
            Base.metadata.create_all(bind=get_engine())
        else:
            raise
