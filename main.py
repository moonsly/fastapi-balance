import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv

from models.database import init_database, close_database
from app.routes import user_router, balance_router, transfer_router

# Загружаем переменные окружения
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    try:
        await init_database()
        print("База данных инициализирована")
    except Exception as e:
        print(f"Ошибка инициализации базы данных: {e}")
        raise

    yield

    # Shutdown
    try:
        await close_database()
        print("Подключение к базе данных закрыто")
    except Exception as e:
        print(f"Ошибка при закрытии базы данных: {e}")


# Создание экземпляра FastAPI
app = FastAPI(
    title="Balance Service API",
    description="""
    Сервис управления балансами пользователей

    ## Функциональность

    * **Пользователи**: регистрация, аутентификация, получение профиля
    * **Баланс**: получение баланса, пополнение, списание
    * **Переводы**: создание переводов между пользователями, просмотр истории

    ## Авторизация

    API использует Basic HTTP Authentication. Передавайте логин и пароль в заголовке Authorization:
    ```
    Authorization: Basic base64(username:password)
    ```

    ## Примеры использования

    1. Зарегистрируйте пользователя через POST /users/register
    2. Используйте логин и пароль для авторизации в других эндпоинтах
    3. Пополните баланс через POST /balance/deposit
    4. Переведите деньги другому пользователю через POST /transfers/
    """,
    version="1.0.0",
    contact={
        "name": "Balance Service",
        "email": "support@balance-service.com",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan
)

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(user_router)
app.include_router(balance_router)
app.include_router(transfer_router)


@app.get(
    "/",
    tags=["Health"],
    summary="Проверка работоспособности",
    description="Возвращает статус работы сервиса"
)
async def health_check():
    """Проверка работоспособности сервиса"""
    return {
        "status": "ok",
        "message": "Balance Service API работает",
        "version": "1.0.0"
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Детальная проверка здоровья",
    description="Возвращает детальную информацию о состоянии сервиса"
)
async def detailed_health_check():
    """Детальная проверка здоровья сервиса"""
    from models.database import db

    # Проверяем подключение к базе данных
    db_status = "ok"
    try:
        if not db.pool:
            db_status = "no_connection"
        else:
            # Пытаемся выполнить простой запрос
            await db.fetch_one("SELECT 1 as test")
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": "1.0.0",
        "database": {
            "status": db_status,
            "pool_size": len(db.pool._holders) if db.pool else 0
        },
        "message": "Balance Service API"
    }


# Глобальный обработчик исключений
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальный обработчик исключений"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Внутренняя ошибка сервера",
            "detail": str(exc) if os.getenv("DEBUG", "false").lower() == "true" else "Обратитесь к администратору"
        }
    )


if __name__ == "__main__":
    # Настройки для запуска
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
