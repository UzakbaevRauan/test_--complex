# database.py
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String
from databases import Database

DATABASE_URL = "sqlite:///./search_history.db"

database = Database(DATABASE_URL)
metadata = MetaData()

search_history = Table(
    "search_history",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("city", String, unique=True),
    Column("count", Integer),
)

engine = create_engine(DATABASE_URL)
metadata.create_all(engine)
