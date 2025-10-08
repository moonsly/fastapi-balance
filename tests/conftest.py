"""
Конфигурация pytest и общие fixtures для E2E тестов
"""

import asyncio
import pytest
import pytest_asyncio
import aiohttp
import multiprocessing
import time
import os
import sys
import uvicorn

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Настройки для тестов
TEST_PORT = 8001
BASE_URL = f"http://localhost:{TEST_PORT}"
TEST_DATABASE_URL = os.getenv(
    'TEST_DATABASE_URL',
    'postgresql://bal_user:bal_passwd@localhost:5432/balance_service_test'
)
CLEAN_DB_AFTER_TESTS = False


def run_test_server(port: int, database_url: str):
    """
    Запускает тестовый API сервер в отдельном процессе

    Args:
        port: порт для запуска сервера
        database_url: URL тестовой базы данных
    """
    # Устанавливаем переменные окружения для тестового сервера
    os.environ['PORT'] = str(port)
    os.environ['DATABASE_URL'] = database_url
    os.environ['DEBUG'] = 'false'

    # Импортируем приложение
    from main import app

    # Запускаем сервер
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="error",
        access_log=False
    )


async def cleanup_test_database():
    """Очищает тестовую базу данных перед запуском тестов"""
    import asyncpg

    try:
        conn = await asyncpg.connect(TEST_DATABASE_URL)

        # Удаляем все записи из таблиц
        await conn.execute("TRUNCATE TABLE transfers CASCADE")
        await conn.execute("TRUNCATE TABLE users RESTART IDENTITY CASCADE")

        await conn.close()
        print("Тестовая база данных очищена")
    except Exception as e:
        print(f"Предупреждение: не удалось очистить тестовую базу данных: {e}")


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для всей сессии тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_server():
    """
    Fixture для запуска тестового API сервера

    Запускает сервер в отдельном процессе и ждет его готовности
    """
    # Запускаем сервер в отдельном процессе
    server_process = multiprocessing.Process(
        target=run_test_server,
        args=(TEST_PORT, TEST_DATABASE_URL),
        daemon=True
    )
    server_process.start()

    # Ждем, пока сервер запустится
    max_retries = 30
    retry_delay = 1

    for i in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BASE_URL}/health") as response:
                    if response.status == 200:
                        print(f"\nТестовый API сервер запущен на порту {TEST_PORT}")
                        break
        except (aiohttp.ClientError, OSError):
            if i < max_retries - 1:
                time.sleep(retry_delay)
            else:
                server_process.terminate()
                server_process.join(timeout=5)
                if server_process.is_alive():
                    server_process.kill()
                raise Exception(
                    f"Не удалось запустить тестовый сервер после {max_retries} попыток"
                )

    # Очищаем тестовую базу данных перед тестами
    await cleanup_test_database()

    yield

    if CLEAN_DB_AFTER_TESTS:
        # Очищаем тестовую базу данных после тестов
        await cleanup_test_database()
        print("Тестовая база данных очищена после выполнения тестов")

    # Останавливаем сервер после тестов
    server_process.terminate()
    server_process.join(timeout=5)

    # Если процесс не завершился, убиваем его принудительно
    if server_process.is_alive():
        server_process.kill()
        server_process.join()

    print(f"\nТестовый API сервер остановлен")


@pytest_asyncio.fixture
async def session(test_server):
    """Создание aiohttp сессии для тестов"""
    async with aiohttp.ClientSession() as session:
        yield session

