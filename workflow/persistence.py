"""PostgreSQL-backed LangGraph checkpointer (conversation state per thread)."""

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row

from config import get_database_url


def create_checkpointer() -> PostgresSaver:
    """Connect to Postgres and make sure the checkpoint tables exist."""
    connection = psycopg.connect(
        get_database_url(),
        autocommit=True,
        row_factory=dict_row,
    )
    checkpointer = PostgresSaver(connection)
    checkpointer.setup()
    return checkpointer
