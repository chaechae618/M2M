from sqlalchemy import create_engine, inspect

from app.db.sqlite_compat import ensure_sqlite_compatibility


def test_sqlite_compatibility_adds_file_name_columns_without_losing_data() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE mentee_profiles (
                id VARCHAR(40) PRIMARY KEY,
                resume_url VARCHAR(1000),
                portfolio_url VARCHAR(1000)
            )
            """
        )
        connection.exec_driver_sql(
            "INSERT INTO mentee_profiles (id, resume_url) VALUES ('mte_existing', '/resume.pdf')"
        )

    ensure_sqlite_compatibility(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("mentee_profiles")}
    assert {"resume_file_name", "portfolio_file_name"}.issubset(columns)
    with engine.connect() as connection:
        row = connection.exec_driver_sql(
            "SELECT id, resume_url FROM mentee_profiles WHERE id = 'mte_existing'"
        ).one()
    assert row == ("mte_existing", "/resume.pdf")
