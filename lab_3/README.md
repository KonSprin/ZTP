# E-commerce Shopping Cart - Event Sourcing + CQRS

Projekt systemu koszyka zakupowego zbudowanego z wykorzystaniem **Event Sourcing** i **CQRS** w Pythonie.

## 🏗️ Architektura

### Event Sourcing
- **Event Store** - wszystkie zmiany stanu zapisywane jako eventy w PostgreSQL
- **Aggregate Root** - `CartAggregate` odtwarza stan poprzez replay eventów
- **Append-only** - eventy nigdy nie są modyfikowane, tylko dodawane
- **Full audit trail** - pełna historia wszystkich operacji

### CQRS (Command Query Responsibility Segregation)
- **Commands** - operacje zmieniające stan (CreateCart, AddItem, RemoveItem, Checkout)
- **Queries** - operacje odczytujące (ViewCart, ViewUserCarts)
- **Write Model** - event store z logiką biznesową
- **Read Model** - zdenormalizowana projekcja dla szybkich odczytów

### Clean Architecture
```
app/
├── domain/              # Logika biznesowa, eventy, aggregate
│   └── cart/
│       ├── events.py    # Domain events
│       ├── commands.py  # Commands
│       └── aggregate.py # Cart aggregate root
├── application/         # Use cases (business logic orchestration)
│   └── cart/
│       ├── create_cart.py
│       ├── add_item.py
│       ├── remove_item.py
│       ├── view_cart.py
│       └── checkout.py
├── infrastructure/      # Implementacje techniczne
│   ├── database.py
│   └── repositories/
│       ├── event_store.py      # Event sourcing repository
│       └── read_model.py       # Read model repository
└── api/                # HTTP API (FastAPI)
    └── v1/
        └── cart.py
```

## 🔑 Kluczowe Cechy

### 1. Optimistic Locking
```sql
-- Unique constraint na (aggregate_id, version) zapewnia spójność
CREATE UNIQUE INDEX idx_aggregate_version 
ON cart_events (aggregate_id, aggregate_version);
```

**Jak działa:**
- Każdy event ma `aggregate_version`
- Przed zapisem sprawdzamy aktualną wersję w bazie
- Jeśli ktoś zapisał między czasem, dostajemy `IntegrityError`
- Retry z najnowszym stanem

**Kod w `event_store.py`:**
```python
async def save_events(self, aggregate_id, events, expected_version):
    current_version = await self._get_current_version(aggregate_id)
    if current_version != expected_version:
        raise ConcurrencyException("Version mismatch")
    # ... save events
```

### 2. Event Replay
Stan agregatu jest odtwarzany z historii eventów:

```python
aggregate = CartAggregate(cart_id)
for event in events:
    aggregate.apply_event(event, is_new=False)
# Stan odtworzony!
```

### 3. Współbieżność
- **Write operations**: Serializable isolation + optimistic locking
- **Read operations**: Read committed (eventual consistency w read model)
- **Multi-device**: Możliwe równoległe dodawanie/usuwanie na różnych urządzeniach
- **Create/Checkout**: Tylko jedno urządzenie (jak w wymaganiach)

## 🚀 Uruchomienie

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Poetry

### Setup

1. **Zainstaluj zależności:**
```bash
poetry install
```

2. **Uruchom infrastrukturę (PostgreSQL + Redis):**
```bash
docker-compose up -d postgres redis
```

3. **Uruchom aplikację lokalnie:**
```bash
# Serwis produktów (mock)
poetry run uvicorn app.products_mock:app --port 8001 --reload

# Główna aplikacja
poetry run uvicorn app.main:app --port 8000 --reload
```

4. **Lub uruchom wszystko w Docker:**
```bash
docker-compose up --build
```

5. **Otwórz w przeglądarce:**
```
http://localhost:8000
```

## 🧪 Testy

```bash
# Uruchom testy jednostkowe
poetry run pytest

# Z coverage
poetry run pytest --cov=app --cov-report=html

# Tylko szybkie testy (bez IO)
poetry run pytest -m "not integration"
```

**Zalety testowania:**
- Use case'y są łatwo testowalne (mockowanie repozytoriów)
- Aggregate testujemy bez bazy danych
- Szybkie testy jednostkowe (< 1s)

## 📊 Baza Danych

### Event Store (Write Model)
```sql
CREATE TABLE cart_events (
    id SERIAL PRIMARY KEY,
    event_id UUID UNIQUE NOT NULL,
    aggregate_id UUID NOT NULL,
    aggregate_version INTEGER NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    occurred_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL,
    UNIQUE (aggregate_id, aggregate_version)  -- Optimistic locking!
);
```

### Read Model (Query)
```sql
CREATE TABLE cart_read_model (
    cart_id UUID PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    items JSONB NOT NULL,
    total_amount FLOAT NOT NULL,
    item_count INTEGER NOT NULL,
    version INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

## 🔄 Przepływ Danych

### Command Flow (Write)
```
HTTP Request
    ↓
FastAPI Endpoint
    ↓
Use Case
    ↓
Load Aggregate (replay events)
    ↓
Execute Command (generate events)
    ↓
Save Events (optimistic locking)
    ↓
Update Read Model
```

### Query Flow (Read)
```
HTTP Request
    ↓
FastAPI Endpoint
    ↓
Query Use Case
    ↓
Read Model Repository
    ↓
Return denormalized data
```

## 📝 API Endpoints

### Commands (Write)
- `POST /api/v1/cart` - Create cart
- `POST /api/v1/cart/{cart_id}/items` - Add item
- `DELETE /api/v1/cart/{cart_id}/items` - Remove item
- `POST /api/v1/cart/{cart_id}/checkout` - Checkout

### Queries (Read)
- `GET /api/v1/cart/{cart_id}` - Get cart details
- `GET /api/v1/cart/user/{user_id}/carts` - Get user's carts

## 🎯 Wymagania Funkcjonalne - Status

✅ Utworzenie nowego koszyka  
✅ Dodawanie produktu do koszyka  
✅ Usuwanie produktu z koszyka  
✅ Przeglądanie zawartości i wartości koszyka  
✅ Finalizacja koszyka (utworzenie zamówienia)  

## 🏆 Wymagania Jakościowe - Status

✅ **Skalowalność** - możliwe horizontalne skalowanie (stateless services)  
✅ **Współbieżność** - optimistic locking, retry mechanism  
✅ **Izolacja użytkowników** - każdy user ma swoje koszyki  
✅ **Spójność operacyjna** - udokumentowane w kodzie (optimistic locking + retry)  

## 🛠️ Stack Technologiczny

- **Python 3.11+**
- **FastAPI** - REST API framework
- **Uvicorn** - ASGI server
- **PostgreSQL** - event store + read model
- **SQLAlchemy Core** - SQL query builder
- **Redis** - caching (gotowe do użycia)
- **httpx** - async HTTP client
- **Poetry** - dependency management
- **Docker** - containerization
- **pytest** - testing

## 🎓 Wzorce i Praktyki

### Wzorce
- ✅ **Event Sourcing** - stan z historii eventów
- ✅ **CQRS** - rozdzielone write/read models
- ✅ **Aggregate Pattern** - CartAggregate jako root
- ✅ **Repository Pattern** - EventStore, ReadModelRepository
- ✅ **Use Case Pattern** - każda operacja = osobny use case

### Praktyki inżynierskie
- ✅ **Clean Architecture** - 3-warstwowa struktura (domain, application, infrastructure)
- ✅ **DRY** - kod się nie powtarza
- ✅ **Testability** - use case'y testowalne bez serwera
- ✅ **Domain-Driven Design** - domena oddzielona od infrastruktury
- ✅ **Dependency Injection** - FastAPI Depends()
- ✅ **Type Hints** - pełne typowanie
- ✅ **Async/Await** - asynchroniczne IO

## 📦 Rozszerzenia (Opcjonalne +0.5/+0.25)

### Blokada produktów (+0.5)
TODO: Implementacja w `ProductReserved`/`ProductReservationReleased` events

**Analiza zalet/wad:**
- **Domena koszyka**: łatwiejsza implementacja, ale tight coupling
- **Domena produktów**: luźne powiązanie, ale bardziej złożone (events across domains)

### Wygasanie koszyka (+0.5)
TODO: Background task sprawdzający `last_activity` i wywołujący `ExpireCart` command

### Powiadomienia o zamówieniu (+0.25)
TODO: 
1. Publish `CartCheckedOut` event do message broker (RabbitMQ/Kafka)
2. Stwórz osobną domenę zamówień nasłuchującą na ten event
3. Wyślij powiadomienie email/SMS

## 🔐 Bezpieczeństwo

**Uwaga:** Mockup nie ma autentykacji!

Do implementacji:
- JWT tokens
- User authentication middleware
- Rate limiting
- Input validation (już jest przez Pydantic)

## 📚 Dokumentacja API

FastAPI generuje automatyczną dokumentację:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🐛 Debug

### Sprawdź eventy w bazie:
```sql
SELECT * FROM cart_events 
WHERE aggregate_id = 'your-cart-id' 
ORDER BY aggregate_version;
```

### Sprawdź read model:
```sql
SELECT * FROM cart_read_model 
WHERE cart_id = 'your-cart-id';
```

### Logi aplikacji:
```bash
docker-compose logs -f app
```

## 📖 Literatura

- [Event Sourcing Pattern](https://martinfowler.com/eaaDev/EventSourcing.html)
- [CQRS Pattern](https://martinfowler.com/bliki/CQRS.html)
- [Domain-Driven Design](https://www.domainlanguage.com/ddd/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
