from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def ensure_sqlite_compatibility(engine: Engine) -> None:
    """Apply small, data-preserving fixes until formal migrations are introduced."""
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as connection:
        inspector = inspect(connection)
        if "mentee_profiles" not in inspector.get_table_names():
            return

        columns = {column["name"] for column in inspector.get_columns("mentee_profiles")}
        for column_name in ("resume_file_name", "portfolio_file_name"):
            if column_name not in columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE mentee_profiles ADD COLUMN {column_name} VARCHAR(255)"
                )
