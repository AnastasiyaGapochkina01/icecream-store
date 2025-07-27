# Описание
Простое CRUD приложение для управления ассортиментом магазина мороженого

# Запуск
```bash
python -m src.app
```

# Примеры запросов
```bash
curl -X POST http://localhost:5000/ice_creams \
  -H "Content-Type: application/json" \
  -d '{"name": "Ванильное", "description": "Классическое ванильное", "price": 2.5, "quantity": 100}'

curl http://localhost:5000/ice_creams

curl -X DELETE http://localhost:5000/ice_creams/1
```
