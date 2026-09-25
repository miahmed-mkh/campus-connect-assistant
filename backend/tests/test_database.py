from sqlalchemy import text

from backend.app.db.database import engine


def test_database_connection() -> None:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_user, current_database()")
        ).one()

    assert result[0] == "campus_user"
    assert result[1] == "campus_connect"
