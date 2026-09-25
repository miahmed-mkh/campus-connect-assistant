import backend.app.models
from backend.app.db.database import Base, engine


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    initialize_database()
    print("Tables PostgreSQL créées avec succès.")
