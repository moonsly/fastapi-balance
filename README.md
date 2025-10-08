# Balance Service API

Простой сервис управления балансами пользователей на FastAPI и PostgreSQL.

## Функциональность

- Регистрация и аутентификация пользователей
- Управление балансом (пополнение, списание)
- Переводы между пользователями
- История операций
- Basic HTTP Authentication
- E2E тесты на aiohttp

## Установка

1. Клонируйте репозиторий и перейдите в директорию:
```bash
cd fastapi-balance
```

2. Создайте виртуальное окружение:
```bash
virtualenv -p python3.10 ./venv

source venv/bin/activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Настройте PostgreSQL:
```sql
CREATE DATABASE balance_service;
CREATE USER bal_user WITH PASSWORD 'bal_passwd';
GRANT ALL PRIVILEGES ON DATABASE balance_service TO bal_user;

\c balance_service
GRANT ALL PRIVILEGES ON SCHEMA public TO bal_user;
```

Схема БД создается автоматически при первом запуске main.py

5. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

Укажите в `.env` ваши настройки БД, хост/порт.

## Запуск

```bash
python main.py
```

Или через uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API будет доступен по адресу: http://localhost:8000

Документация Swagger: http://localhost:8000/docs

## Авторизация

API использует Basic HTTP Authentication. Передавайте логин и пароль в заголовке:

```
Authorization: Basic base64(username:password)
```

## Примеры использования c CURL

### 1. Регистрация пользователя
```bash
curl -X POST "http://localhost:8000/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john",
    "password": "secret123",
    "initial_balance": 1000.00
  }'
```

### 2. Получение баланса
```bash
curl -u john:secret123 -X GET "http://localhost:8000/balance/"

{"balance":"1008.00"}
```

### 3. Пополнение баланса
```bash
curl -u john:secret123 -X POST "http://localhost:8000/balance/deposit" \
  -H "Content-Type: application/json" \
  -d '{"amount": 500.00}'

{"message":"Баланс пополнен на 500.00. Новый баланс: 1008.00","balance":"1008.00"}
```

[CURL_TESTS.md](CURL_TESTS.md) - другие API запросы с CURL

## База данных

Сервис автоматически создает необходимые таблицы при запуске:

- `users` - пользователи и их балансы
- `transfers` - история переводов

## Безопасность

- Пароли хешируются с помощью bcrypt
- Переводы выполняются в транзакциях
- Проверка прав доступа к переводам
- Валидация входных данных

## Производительность

- Пул соединений с базой данных
- Индексы на часто используемых полях
- Пагинация для списка переводов /transfers

## Запуск Е2Е тестов

1. Создайте отдельную БД для тестов
```sql
CREATE DATABASE balance_service_test;
CREATE USER bal_user WITH PASSWORD 'bal_passwd';
GRANT ALL PRIVILEGES ON DATABASE balance_service_test TO bal_user;

\c balance_service_test
GRANT ALL PRIVILEGES ON SCHEMA public TO bal_user;
```

2. Укажите в tests/conftest.py конфигурацию подключения к БД
```python
TEST_DATABASE_URL = os.getenv(
    'TEST_DATABASE_URL',
    'postgresql://bal_user:bal_passwd@localhost:5432/balance_service_test'
)
```

3. Запустите Е2Е тесты
```bash
./run_tests.sh
```

<details>
  <summary>Пример запуска Е2Е тестов</summary>

  ```bash
============================================================== test session starts ===============================================================
platform linux -- Python 3.12.3, pytest-8.4.2, pluggy-1.6.0 -- /home/zak/work/fastapi-balance/env/bin/python
cachedir: .pytest_cache
rootdir: /home/zak/work/fastapi-balance
plugins: locust-2.41.5, anyio-4.11.0, asyncio-1.2.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 11 items

tests/test_e2e_api.py::TestBalanceServiceE2E::test_01_create_user_john База данных инициализирована

Тестовый API сервер запущен на порту 8001
Тестовая база данных очищена

  Пользователь john_test1 успешно создан с ID 1 и балансом 1000.00
PASSED
tests/test_e2e_api.py::TestBalanceServiceE2E::test_02_get_user_info
  Информация о пользователе: ID=2, баланс=1000.00
PASSED
tests/test_e2e_api.py::TestBalanceServiceE2E::test_03_create_recipient_user
  Пользователь-получатель john2_test3 создан с ID 3
PASSED
tests/test_e2e_api.py::TestBalanceServiceE2E::test_04_successful_transfer
  Перевод создан: ID=1, сумма=500.00
  Перевод найден в списке переводов
  Баланс отправителя после перевода: 500.00
  Баланс получателя после перевода: 1500.00
PASSED
tests/test_e2e_api.py::TestBalanceServiceE2E::test_05_insufficient_funds_error
  Ошибка недостаточности средств обработана корректно: Недостаточно средств
PASSED
tests/test_e2e_api.py::TestBalanceServiceE2E::test_06_self_transfer_error
  Ошибка перевода самому себе обработана корректно: Нельзя переводить деньги самому себе
PASSED
tests/test_e2e_api.py::TestBalanceServiceE2E::test_07_negative_amount_error
  Ошибка отрицательной суммы обработана корректно: Input should be greater than 0
PASSED
tests/test_e2e_api.py::TestBalanceServiceE2E::test_08_zero_amount_error
  Ошибка нулевой суммы обработана корректно: Input should be greater than 0
PASSED
tests/test_e2e_api.py::TestBalanceServiceE2E::test_09_nonexistent_user_error
  Ошибка перевода несуществующему пользователю обработана корректно: Пользователь 'not_exists_user_9999' не найден
PASSED
tests/test_e2e_api.py::TestBalanceServiceE2E::test_10_deposit
  Баланс пополнен на 10.0, новый баланс: 1010.00
PASSED
tests/test_e2e_api.py::TestBalanceServiceE2E::test_11_withdraw
  С баланса списано 10.0, новый баланс: 990.00
PASSEDПодключение к базе данных закрыто

Тестовый API сервер остановлен


=============================================================== 11 passed in 7.21s ===============================================================

=== Все тесты пройдены успешно ===
  ```
</details>

4. БД с результатами запуска тестов

Можно посмотреть созданные users, transfers в результате тестов - в БД balance_service_test
<details>
  <summary>БД после запуска Е2Е тестов</summary>
```sql
balance_service_test=# select id, username, balance, created_at from users; 
 id |  username   | balance |          created_at           
----+-------------+---------+-------------------------------
  1 | john_test1  | 1000.00 | 2025-10-08 16:20:49.804407+00
  2 | john_test2  | 1000.00 | 2025-10-08 16:20:50.022557+00
  3 | john2_test3 | 1000.00 | 2025-10-08 16:20:50.458461+00
  4 | john_test4  |  500.00 | 2025-10-08 16:20:50.692201+00
  5 | john2_test4 | 1500.00 | 2025-10-08 16:20:50.910424+00
  6 | john_test5  | 1000.00 | 2025-10-08 16:20:51.984605+00
  7 | john2_test5 | 1000.00 | 2025-10-08 16:20:52.187738+00
  8 | john_test6  | 1000.00 | 2025-10-08 16:20:52.602613+00
  9 | john_test7  | 1000.00 | 2025-10-08 16:20:53.019554+00
 10 | john2_test7 | 1000.00 | 2025-10-08 16:20:53.229198+00
 11 | john_test8  | 1000.00 | 2025-10-08 16:20:53.688282+00
 12 | john2_test8 | 1000.00 | 2025-10-08 16:20:53.910521+00
 13 | john_test9  | 1000.00 | 2025-10-08 16:20:54.387303+00
 14 | john_test10 | 1010.00 | 2025-10-08 16:20:54.836006+00
 15 | john_test11 |  990.00 | 2025-10-08 16:20:55.29412+00
(15 rows)
```
</details>
