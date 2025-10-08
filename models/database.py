import asyncpg
import os
from typing import Optional
from contextlib import asynccontextmanager


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        
    async def create_pool(self):
        """Создает пул подключений к базе данных"""
        database_url = os.getenv(
            'DATABASE_URL', 
            'postgresql://postgres:password@localhost:5432/balance_service'
        )
        
        self.pool = await asyncpg.create_pool(
            database_url,
            min_size=1,
            max_size=10,
            command_timeout=60
        )
        
    async def close_pool(self):
        """Закрывает пул подключений"""
        if self.pool:
            await self.pool.close()
    
    @asynccontextmanager
    async def get_connection(self):
        """Контекстный менеджер для получения подключения из пула"""
        if not self.pool:
            raise RuntimeError("Database pool is not initialized")
            
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute_query(self, query: str, *args):
        """Выполняет запрос без возврата данных"""
        async with self.get_connection() as connection:
            return await connection.execute(query, *args)
    
    async def fetch_one(self, query: str, *args):
        """Выполняет запрос и возвращает одну строку"""
        async with self.get_connection() as connection:
            return await connection.fetchrow(query, *args)
    
    async def fetch_all(self, query: str, *args):
        """Выполняет запрос и возвращает все строки"""
        async with self.get_connection() as connection:
            return await connection.fetch(query, *args)


# Глобальный экземпляр базы данных
db = Database()


async def init_database():
    """Инициализация базы данных и создание таблиц"""
    await db.create_pool()
    
    # Создание таблиц
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00 CHECK (balance >= 0),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    create_transfers_table = """
    CREATE TABLE IF NOT EXISTS transfers (
        id SERIAL PRIMARY KEY,
        from_user_id INTEGER NOT NULL REFERENCES users(id),
        to_user_id INTEGER NOT NULL REFERENCES users(id),
        amount DECIMAL(15, 2) NOT NULL CHECK (amount > 0),
        description VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        CHECK (from_user_id != to_user_id)
    );
    """
    
    create_indexes = """
    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
    CREATE INDEX IF NOT EXISTS idx_transfers_from_user ON transfers(from_user_id);
    CREATE INDEX IF NOT EXISTS idx_transfers_to_user ON transfers(to_user_id);
    CREATE INDEX IF NOT EXISTS idx_transfers_created_at ON transfers(created_at);
    """
    
    # Триггер для обновления updated_at
    create_trigger = """
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ language 'plpgsql';

    DROP TRIGGER IF EXISTS update_users_updated_at ON users;
    CREATE TRIGGER update_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """
    
    async with db.get_connection() as connection:
        await connection.execute(create_users_table)
        await connection.execute(create_transfers_table)
        await connection.execute(create_indexes)
        await connection.execute(create_trigger)


async def close_database():
    """Закрытие подключения к базе данных"""
    await db.close_pool()
