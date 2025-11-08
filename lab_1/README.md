# Product Management API

System zarządzania produktami z kontrolą zabronionych fraz i historią zmian.

### 1. Instalacja
```bash
poetry install
```

### 2. Konfiguracja bazy danych
Edytuj `.env`:
```bash
SQLALCHEMY_DATABASE_URL="postgresql+psycopg2://user:password@host:port/database"
```

### 3. Uruchomienie
```bash
poetry run uvicorn main:app --reload
```

Aplikacja dostępna pod: **http://localhost:8000**  
Dokumentacja API: **http://localhost:8000/docs**

## Funkcje

### Produkty
- **GET** `/products` - Lista produktów
- **GET** `/products/{id}` - Szczegóły produktu
- **POST** `/products` - Dodaj produkt
- **PUT** `/products/{id}` - Aktualizuj produkt
- **PATCH** `/products/{id}` - Częściowa aktualizacja
- **DELETE** `/products/{id}` - Usuń produkt

### Zabronione Frazy
- **GET** `/banned-phrases` - Lista fraz
- **POST** `/banned-phrases` - Dodaj frazę
- **DELETE** `/banned-phrases/{id}` - Usuń frazę

### Historia
- **GET** `/products/{id}/history` - Historia produktu
- **GET** `/products/history/all` - Cała historia

## Przykład Użycia

### Utworzenie produktu
```bash
curl -X POST http://localhost:8000/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Laptop2024",
    "description": "Profesjonalny laptop",
    "price": 3999.99,
    "quantity": 10,
    "category": "Elektronika"
  }'
```

## Walidacja

### Nazwa produktu
- 3-20 znaków
- Tylko litery i cyfry
- Unikalna

### Ceny według kategorii
| Kategoria | Min | Max |
|-----------|-----|-----|
| Elektronika | 50 PLN | 50,000 PLN |
| Książki | 5 PLN | 500 PLN |
| Odzież | 10 PLN | 5,000 PLN |

### Ilość
- Liczba całkowita ≥ 0

## Testy

TBI

```bash
poetry run behave
```

## Wymagania

- Python 3.10+
- PostgreSQL 12+
- poetry
