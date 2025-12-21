# Lab 2

Konrad Springer

---


```

curl -X POST http://localhost:8000/notifications   -H "Content-Type: application/json"   -d '{
    "recipient":"konrad@example.com",
    "channel":"push",
    "content":"test123",
    "use_user_preferences":true
  }'

```

```

curl -X POST http://localhost:8000/notifications   -H "Content-Type: application/json"   -d '{
    "recipient":"konrad@example.com",
    "channel":"push",
    "content":"delayed messege",
    "scheduled_time": "2025-12-21T13:17:00+01:00",
    "use_user_preferences":true,
    "user_timezone": "Europe/Warsaw"
  }'

```

```

curl -X POST http://localhost:8000/notifications   -H "Content-Type: application/json"   -d '{
    "recipient":"konrad@example.com",
    "channel":"email",
    "content":"email body aaaaaaaa",
    "use_user_preferences":true,
  }'

```
