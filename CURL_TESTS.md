1) создать пользователя john с балансом 1000
```bash
curl -X POST "http://localhost:8000/users/register"   -H "Content-Type: application/json"   -d '{
    "username": "john",
    "password": "secret123",
    "initial_balance": 1000.00
  }' | jq
{
    "username": "john",
    "id": 1,
    "balance": "1000.00",
    "created_at": "2025-10-08T14:31:09.049290Z",
    "updated_at": "2025-10-08T14:31:09.049290Z"
}
```

2) информация о своем аккаунте - баланс, ИД, дата создания/обновления
```bash
curl -s -u john:secret123 "http://localhost:8000/users/me"  | jq
{
  "username": "john",
  "id": 1,
  "balance": "1000.00",
  "created_at": "2025-10-08T14:31:09.049290Z",
  "updated_at": "2025-10-08T14:31:09.049290Z"
}
```

3) создать пользователя-получателя перевода john2
```bash
curl -X POST "http://localhost:8000/users/register"   -H "Content-Type: application/json"   -d '{
    "username": "john2",
    "password": "secret123",
    "initial_balance": 1000.00
  }' | jq
{
  "username": "john2",
  "id": 2,
  "balance": "1000.00",
  "created_at": "2025-10-08T14:37:45.403039Z",
  "updated_at": "2025-10-08T14:37:45.403039Z"
}
```

4) перевод 500 john1 -> john2, проверка создания перевода в /transfers, новых балансов
```bash
curl -u john:secret123  -X 'POST'   'http://192.168.1.91:8000/transfers/'   -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '{
  "to_username": "john2",
  "amount": 500,
  "description": "test 500"
}' | jq
{
  "id": 1,
  "from_username": "john",
  "to_username": "john2",
  "amount": "500.00",
  "description": "test 500",
  "created_at": "2025-10-08T14:41:45.318787Z"
}

curl -u john:secret123  -X 'GET'   'http://192.168.1.91:8000/transfers/'
[{"id":1,"from_username":"john","to_username":"john2","amount":"500.00","description":"test 500","created_at":"2025-10-08T14:41:45.318787Z"}]

curl -s -u john:secret123 "http://localhost:8000/users/me"  | jq .balance
"500.00"
curl -s -u john2:secret123 "http://localhost:8000/users/me"  | jq .balance
"1500.00"

```

5) проверка ошибки - перевод 5000, недостаточно средств на балансе
```bash
curl -u john:secret123  -X 'POST'   'http://192.168.1.91:8000/transfers/'   -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '{
  "to_username": "john2",
  "amount": 5000,
  "description": "test 5000"
}'
{"detail":"Недостаточно средств"}
```

6) проверка ошибки - перевод самому себе
```bash
curl -u john:secret123  -X 'POST'   'http://192.168.1.91:8000/transfers/'   -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '{
  "to_username": "john",
  "amount": 500,
  "description": "test self transfer - error"
}' | jq
{
  "detail": "Нельзя переводить деньги самому себе"
}
```

7) проверка ошибки - перевод отрицательной суммы
```bash
curl -u john:secret123  -X 'POST'   'http://192.168.1.91:8000/transfers/'   -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '{
  "to_username": "john2",
  "amount": -1,
  "description": "test negative sum transfer - error"
}' | jq
{
  "detail": [
    {
      "type": "greater_than",
      "loc": [
        "body",
        "amount"
      ],
      "msg": "Input should be greater than 0",
      "input": 0,
      "ctx": {
        "gt": 0
      }
    }
  ]
}
```

8) проверка ошибки - перевод 0 суммы
```bash
curl -u john:secret123  -X 'POST'   'http://192.168.1.91:8000/transfers/'   -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '{
  "to_username": "john2",
  "amount": 0,
  "description": "test negative sum transfer - error"
}' | jq
{
  "detail": [
    {
      "type": "greater_than",
      "loc": [
        "body",
        "amount"
      ],
      "msg": "Input should be greater than 0",
      "input": 0,
      "ctx": {
        "gt": 0
      }
    }
  ]
}
```

9) проверка ошибки - перевод несуществующему пользователю
```bash
curl -s -u john:secret123  -X 'POST'   'http://192.168.1.91:8000/transfers/'   -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '{
  "to_username": "not_exists",
  "amount": 10,
  "description": "test transfer to nonexisting user"
}' | jq
{
  "detail": "Пользователь 'not_exists' не найден"
}
```
