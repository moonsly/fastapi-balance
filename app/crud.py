from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import asyncpg
from passlib.context import CryptContext

from models.database import db
from models.models import User, UserCreate, Transfer, TransferResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserCRUD:
    @staticmethod
    def hash_password(password: str) -> str:
        """Хеширует пароль"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Проверяет пароль"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    async def create_user(user_data: UserCreate) -> User:
        """Создает нового пользователя"""
        hashed_password = UserCRUD.hash_password(user_data.password)
        
        query = """
        INSERT INTO users (username, password_hash, balance)
        VALUES ($1, $2, $3)
        RETURNING id, username, balance, created_at, updated_at
        """
        
        row = await db.fetch_one(
            query, 
            user_data.username, 
            hashed_password, 
            user_data.initial_balance
        )
        
        return User(**dict(row))
    
    @staticmethod
    async def get_user_by_username(username: str) -> Optional[User]:
        """Получает пользователя по имени"""
        query = """
        SELECT id, username, balance, created_at, updated_at
        FROM users
        WHERE username = $1
        """
        
        row = await db.fetch_one(query, username)
        if row:
            return User(**dict(row))
        return None
    
    @staticmethod
    async def get_user_by_id(user_id: int) -> Optional[User]:
        """Получает пользователя по ID"""
        query = """
        SELECT id, username, balance, created_at, updated_at
        FROM users
        WHERE id = $1
        """
        
        row = await db.fetch_one(query, user_id)
        if row:
            return User(**dict(row))
        return None
    
    @staticmethod
    async def authenticate_user(username: str, password: str) -> Optional[User]:
        """Аутентификация пользователя"""
        query = """
        SELECT id, username, password_hash, balance, created_at, updated_at
        FROM users
        WHERE username = $1
        """
        
        row = await db.fetch_one(query, username)
        if row and UserCRUD.verify_password(password, row['password_hash']):
            # Возвращаем пользователя без хеша пароля
            user_data = dict(row)
            del user_data['password_hash']
            return User(**user_data)
        return None
    
    @staticmethod
    async def update_balance(user_id: int, new_balance: Decimal) -> bool:
        """Обновляет баланс пользователя"""
        query = """
        UPDATE users
        SET balance = $2
        WHERE id = $1 AND balance >= 0
        """
        
        result = await db.execute_query(query, user_id, new_balance)
        return result == "UPDATE 1"
    
    @staticmethod
    async def get_balance(user_id: int) -> Optional[Decimal]:
        """Получает баланс пользователя"""
        query = "SELECT balance FROM users WHERE id = $1"
        
        row = await db.fetch_one(query, user_id)
        if row:
            return row['balance']
        return None


class TransferCRUD:
    @staticmethod
    async def create_transfer(
        from_user_id: int,
        to_user_id: int, 
        amount: Decimal,
        description: Optional[str] = None
    ) -> Optional[Transfer]:
        """Создает перевод между пользователями с транзакцией"""
        
        async with db.get_connection() as connection:
            async with connection.transaction():
                try:
                    # Проверяем баланс отправителя
                    sender_balance_row = await connection.fetchrow(
                        "SELECT balance FROM users WHERE id = $1 FOR UPDATE",
                        from_user_id
                    )
                    
                    if not sender_balance_row:
                        raise ValueError("Отправитель не найден")
                    
                    sender_balance = sender_balance_row['balance']
                    if sender_balance < amount:
                        raise ValueError("Недостаточно средств")
                    
                    # Проверяем существование получателя
                    receiver_exists = await connection.fetchrow(
                        "SELECT id FROM users WHERE id = $1 FOR UPDATE",
                        to_user_id
                    )
                    
                    if not receiver_exists:
                        raise ValueError("Получатель не найден")
                    
                    # Списываем с отправителя
                    await connection.execute(
                        "UPDATE users SET balance = balance - $2 WHERE id = $1",
                        from_user_id, amount
                    )
                    
                    # Зачисляем получателю
                    await connection.execute(
                        "UPDATE users SET balance = balance + $2 WHERE id = $1",
                        to_user_id, amount
                    )
                    
                    # Создаем запись о переводе
                    transfer_row = await connection.fetchrow("""
                        INSERT INTO transfers (from_user_id, to_user_id, amount, description)
                        VALUES ($1, $2, $3, $4)
                        RETURNING id, from_user_id, to_user_id, amount, description, created_at
                    """, from_user_id, to_user_id, amount, description)
                    
                    return Transfer(**dict(transfer_row))
                    
                except (ValueError, asyncpg.CheckViolationError) as e:
                    # Транзакция автоматически откатится
                    raise e
    
    @staticmethod
    async def get_user_transfers(
        user_id: int, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[TransferResponse]:
        """Получает переводы пользователя (отправленные и полученные)"""
        query = """
        SELECT 
            t.id,
            t.amount,
            t.description,
            t.created_at,
            sender.username as from_username,
            receiver.username as to_username
        FROM transfers t
        JOIN users sender ON t.from_user_id = sender.id
        JOIN users receiver ON t.to_user_id = receiver.id
        WHERE t.from_user_id = $1 OR t.to_user_id = $1
        ORDER BY t.created_at DESC
        LIMIT $2 OFFSET $3
        """
        
        rows = await db.fetch_all(query, user_id, limit, offset)
        
        return [TransferResponse(**dict(row)) for row in rows]
    
    @staticmethod
    async def get_transfer_by_id(transfer_id: int) -> Optional[TransferResponse]:
        """Получает перевод по ID"""
        query = """
        SELECT 
            t.id,
            t.amount,
            t.description,
            t.created_at,
            sender.username as from_username,
            receiver.username as to_username
        FROM transfers t
        JOIN users sender ON t.from_user_id = sender.id
        JOIN users receiver ON t.to_user_id = receiver.id
        WHERE t.id = $1
        """
        
        row = await db.fetch_one(query, transfer_id)
        if row:
            return TransferResponse(**dict(row))
        return None


# Инстансы для удобства использования
user_crud = UserCRUD()
transfer_crud = TransferCRUD()
