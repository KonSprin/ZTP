from src import models, database

def init_db():
    """Inicjalizacja bazy danych"""
    models.Base.metadata.create_all(bind=database.engine)
    print("Baza danych zainicjalizowana")

if __name__ == "__main__":
    init_db()
