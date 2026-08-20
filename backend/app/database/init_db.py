import logging
import re

from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateTable

from app.database.database import Base, engine

# Import models so they're registered on Base.metadata before create_all runs.
from app.models import job, resume, screening  # noqa: F401

logger = logging.getLogger(__name__)


def _default_literal(column) -> str | None:
    """SQL literal for a column's Python-level scalar default, used to backfill NULLs
    a prior bare ALTER TABLE ADD COLUMN left behind (it never applies a value, only a
    prior ADD COLUMN in this same migration path could have done that) in a column
    that's NOT NULL in the current model. Returns None for defaults that aren't a
    simple scalar (list/dict/callable) - those columns never end up NULL in practice
    because the ORM always supplies them on insert.
    """
    if column.default is None or not column.default.is_scalar:
        return None
    value = column.default.arg
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return None


def _rebuild_table(conn, table, existing_column_names: set[str]) -> None:
    """SQLite can ADD a column but can never ALTER an existing column's NOT NULL
    constraint (e.g. ScreeningResult.match_score becoming nullable so ineligible
    candidates can store score=None instead of a contaminated 0.0 - Section 7).

    Rebuilds the table via SQLite's documented copy/drop/rename procedure, preserving
    every existing row; columns that are new in the current model come back NULL/
    default for pre-existing rows, exactly like a normal ADD COLUMN would.
    """
    temp_name = f"{table.name}__migrate"
    # SQLite's DDL isn't reliably rolled back by the enclosing transaction on error, so
    # a prior failed migration attempt can leave this temp table behind - clear it first
    # so retries (e.g. after fixing a bug in this migration itself) are idempotent.
    conn.execute(text(f'DROP TABLE IF EXISTS "{temp_name}"'))
    create_sql = str(CreateTable(table).compile(engine)).strip()
    # The compiled DDL doesn't quote unreserved identifiers, so target only the table
    # name that follows "CREATE TABLE" (leaving column names/types untouched).
    create_sql = re.sub(
        rf'(CREATE TABLE )"?{re.escape(table.name)}"?', rf'\1"{temp_name}"', create_sql, count=1
    )
    conn.execute(text(create_sql))

    common_columns = [c for c in table.columns if c.name in existing_column_names]
    insert_cols_sql = ", ".join(f'"{c.name}"' for c in common_columns)

    select_exprs = []
    for c in common_columns:
        default_literal = _default_literal(c) if not c.nullable else None
        select_exprs.append(f'COALESCE("{c.name}", {default_literal})' if default_literal is not None else f'"{c.name}"')
    select_cols_sql = ", ".join(select_exprs)

    conn.execute(
        text(f'INSERT INTO "{temp_name}" ({insert_cols_sql}) SELECT {select_cols_sql} FROM "{table.name}"')
    )

    conn.execute(text(f'DROP TABLE "{table.name}"'))
    conn.execute(text(f'ALTER TABLE "{temp_name}" RENAME TO "{table.name}"'))

    for index in table.indexes:
        conn.execute(text(f'DROP INDEX IF EXISTS "{index.name}"'))
        idx_cols = ", ".join(f'"{c.name}"' for c in index.columns)
        conn.execute(text(f'CREATE INDEX "{index.name}" ON "{table.name}" ({idx_cols})'))

    logger.info("Rebuilt table %s to apply column/nullability changes", table.name)


def _sync_schema() -> None:
    """SQLite has no migration framework in this project (Base.metadata.create_all
    only creates *new* tables). For an existing local dev DB file created before the
    eligibility-screening columns were added, bring it up to date so upgrading never
    requires deleting local data:
      - a genuinely new column is added with ALTER TABLE ADD COLUMN.
      - a column whose nullability narrowed in the DB but widened in the model (NOT
        NULL -> nullable) requires a full table rebuild, since SQLite can't ALTER that.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in Base.metadata.tables.values():
            if table.name not in existing_tables:
                continue

            existing_columns = {col["name"]: col for col in inspector.get_columns(table.name)}

            needs_rebuild = any(
                column.nullable and not existing_columns[column.name]["nullable"]
                for column in table.columns
                if column.name in existing_columns and not column.primary_key
            )
            if needs_rebuild:
                _rebuild_table(conn, table, set(existing_columns))
                continue

            for column in table.columns:
                if column.name in existing_columns:
                    continue
                ddl_type = column.type.compile(engine.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {ddl_type}'))
                logger.info("Added missing column %s.%s", table.name, column.name)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        _sync_schema()
