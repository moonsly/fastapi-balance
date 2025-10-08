"""
E2E автотесты для Balance Service API
Тесты основаны на пунктах 1-9 из CURL_TESTS.md

Тесты автоматически запускают API сервер на отдельном порту (8001)
и используют отдельную тестовую базу данных.
"""

import pytest
import aiohttp
from aiohttp import BasicAuth
from typing import Dict, Any

from .conftest import BASE_URL


class TestBalanceServiceE2E:
    """E2E тесты для Balance Service API"""

    async def register_user(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        initial_balance: float = 1000.00
    ) -> Dict[str, Any]:
        """
        Вспомогательный метод для регистрации пользователя
        """
        url = f"{BASE_URL}/users/register"
        payload = {
            "username": username,
            "password": password,
            "initial_balance": initial_balance
        }

        async with session.post(url, json=payload) as response:
            assert response.status == 201, f"Ожидался статус 201, получен {response.status}"
            data = await response.json()
            return data

    async def get_user_info(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Вспомогательный метод для получения информации о пользователе
        """
        url = f"{BASE_URL}/users/me"
        auth = BasicAuth(username, password)

        async with session.get(url, auth=auth) as response:
            assert response.status == 200, f"Ожидался статус 200, получен {response.status}"
            data = await response.json()
            return data

    async def create_transfer(
        self,
        session: aiohttp.ClientSession,
        from_username: str,
        from_password: str,
        to_username: str,
        amount: float,
        description: str
    ) -> tuple[int, Dict[str, Any]]:
        """
        Вспомогательный метод для создания перевода
        """
        url = f"{BASE_URL}/transfers/"
        auth = BasicAuth(from_username, from_password)
        payload = {
            "to_username": to_username,
            "amount": amount,
            "description": description
        }

        async with session.post(url, json=payload, auth=auth) as response:
            data = await response.json()
            return response.status, data

    async def get_transfers(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str
    ) -> list:
        """
        Вспомогательный метод для получения списка переводов
        """
        url = f"{BASE_URL}/transfers/"
        auth = BasicAuth(username, password)

        async with session.get(url, auth=auth) as response:
            assert response.status == 200, f"Ожидался статус 200, получен {response.status}"
            data = await response.json()
            return data

    async def deposit(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        amount: float
    ) -> tuple[int, Dict[str, Any]]:
        """
        Вспомогательный метод для пополнения баланса
        """
        url = f"{BASE_URL}/balance/deposit"
        auth = BasicAuth(username, password)
        payload = {"amount": amount}

        async with session.post(url, json=payload, auth=auth) as response:
            data = await response.json()
            return response.status, data

    async def withdraw(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        amount: float
    ) -> tuple[int, Dict[str, Any]]:
        """
        Вспомогательный метод для списания с баланса
        """
        url = f"{BASE_URL}/balance/withdraw"
        auth = BasicAuth(username, password)
        payload = {"amount": amount}

        async with session.post(url, json=payload, auth=auth) as response:
            data = await response.json()
            return response.status, data

    @pytest.mark.asyncio
    async def test_01_create_user_john(self, session):
        """
        Тест 1: Создание пользователя john с балансом 1000
        """
        username = "john_test1"
        password = "secret123"
        initial_balance = 1000.00

        data = await self.register_user(session, username, password, initial_balance)

        # Проверяем структуру ответа
        assert "username" in data
        assert "id" in data
        assert "balance" in data
        assert "created_at" in data
        assert "updated_at" in data

        # Проверяем значения
        assert data["username"] == username
        assert float(data["balance"]) == initial_balance
        assert data["id"] > 0

        print(f"\n  Пользователь {username} успешно создан с ID {data['id']} и балансом {data['balance']}")

    @pytest.mark.asyncio
    async def test_02_get_user_info(self, session):
        """
        Тест 2: Получение информации о своем аккаунте
        """
        username = "john_test2"
        password = "secret123"
        initial_balance = 1000.00

        # Регистрируем пользователя
        registered_data = await self.register_user(session, username, password, initial_balance)
        user_id = registered_data["id"]

        # Получаем информацию о пользователе
        user_info = await self.get_user_info(session, username, password)

        # Проверяем данные
        assert user_info["username"] == username
        assert user_info["id"] == user_id
        assert float(user_info["balance"]) == initial_balance
        assert "created_at" in user_info
        assert "updated_at" in user_info

        print(f"\n  Информация о пользователе: ID={user_info['id']}, баланс={user_info['balance']}")

    @pytest.mark.asyncio
    async def test_03_create_recipient_user(self, session):
        """
        Тест 3: Создание пользователя-получателя перевода john2
        """
        username = "john2_test3"
        password = "secret123"
        initial_balance = 1000.00

        data = await self.register_user(session, username, password, initial_balance)

        # Проверяем структуру ответа
        assert data["username"] == username
        assert float(data["balance"]) == initial_balance
        assert data["id"] > 0

        print(f"\n  Пользователь-получатель {username} создан с ID {data['id']}")

    @pytest.mark.asyncio
    async def test_04_successful_transfer(self, session):
        """
        Тест 4: Успешный перевод 500 от john к john2, проверка балансов
        """
        sender_username = "john_test4"
        sender_password = "secret123"
        recipient_username = "john2_test4"
        recipient_password = "secret123"
        transfer_amount = 500.00

        # Регистрируем отправителя и получателя
        await self.register_user(session, sender_username, sender_password, 1000.00)
        await self.register_user(session, recipient_username, recipient_password, 1000.00)

        # Создаем перевод
        status, transfer_data = await self.create_transfer(
            session,
            sender_username,
            sender_password,
            recipient_username,
            transfer_amount,
            "test 500"
        )

        # Проверяем успешность перевода
        assert status == 201, f"Ожидался статус 201, получен {status}"
        assert "id" in transfer_data
        assert transfer_data["from_username"] == sender_username
        assert transfer_data["to_username"] == recipient_username
        assert float(transfer_data["amount"]) == transfer_amount
        assert transfer_data["description"] == "test 500"
        assert "created_at" in transfer_data

        print(f"\n  Перевод создан: ID={transfer_data['id']}, сумма={transfer_data['amount']}")

        # Получаем список переводов
        transfers = await self.get_transfers(session, sender_username, sender_password)
        assert len(transfers) > 0
        assert any(t["id"] == transfer_data["id"] for t in transfers)

        print(f"  Перевод найден в списке переводов")

        # Проверяем баланс отправителя
        sender_info = await self.get_user_info(session, sender_username, sender_password)
        assert float(sender_info["balance"]) == 500.00
        print(f"  Баланс отправителя после перевода: {sender_info['balance']}")

        # Проверяем баланс получателя
        recipient_info = await self.get_user_info(session, recipient_username, recipient_password)
        assert float(recipient_info["balance"]) == 1500.00
        print(f"  Баланс получателя после перевода: {recipient_info['balance']}")

    @pytest.mark.asyncio
    async def test_05_insufficient_funds_error(self, session):
        """
        Тест 5: Проверка ошибки - недостаточно средств на балансе
        """
        sender_username = "john_test5"
        sender_password = "secret123"
        recipient_username = "john2_test5"
        recipient_password = "secret123"

        # Регистрируем пользователей
        await self.register_user(session, sender_username, sender_password, 1000.00)
        await self.register_user(session, recipient_username, recipient_password, 1000.00)

        # Пытаемся перевести больше, чем есть на балансе
        status, error_data = await self.create_transfer(
            session,
            sender_username,
            sender_password,
            recipient_username,
            5000.00,
            "test 5000"
        )

        # Проверяем, что получена ошибка
        assert status == 400, f"Ожидался статус 400, получен {status}"
        assert "detail" in error_data
        assert "Недостаточно средств" in error_data["detail"]

        print(f"\n  Ошибка недостаточности средств обработана корректно: {error_data['detail']}")

    @pytest.mark.asyncio
    async def test_06_self_transfer_error(self, session):
        """
        Тест 6: Проверка ошибки - перевод самому себе
        """
        username = "john_test6"
        password = "secret123"

        # Регистрируем пользователя
        await self.register_user(session, username, password, 1000.00)

        # Пытаемся перевести самому себе
        status, error_data = await self.create_transfer(
            session,
            username,
            password,
            username,
            500.00,
            "test self transfer - error"
        )

        # Проверяем, что получена ошибка
        assert status == 400, f"Ожидался статус 400, получен {status}"
        assert "detail" in error_data
        assert "Нельзя переводить деньги самому себе" in error_data["detail"]

        print(f"\n  Ошибка перевода самому себе обработана корректно: {error_data['detail']}")

    @pytest.mark.asyncio
    async def test_07_negative_amount_error(self, session):
        """
        Тест 7: Проверка ошибки - перевод отрицательной суммы
        """
        sender_username = "john_test7"
        sender_password = "secret123"
        recipient_username = "john2_test7"
        recipient_password = "secret123"

        # Регистрируем пользователей
        await self.register_user(session, sender_username, sender_password, 1000.00)
        await self.register_user(session, recipient_username, recipient_password, 1000.00)

        # Пытаемся перевести отрицательную сумму
        status, error_data = await self.create_transfer(
            session,
            sender_username,
            sender_password,
            recipient_username,
            -1,
            "test negative sum transfer - error"
        )

        # Проверяем, что получена ошибка валидации
        assert status == 422, f"Ожидался статус 422, получен {status}"
        assert "detail" in error_data

        # Проверяем, что это ошибка валидации Pydantic
        if isinstance(error_data["detail"], list):
            error = error_data["detail"][0]
            assert error["type"] == "greater_than"
            assert "amount" in error["loc"]
            print(f"\n  Ошибка отрицательной суммы обработана корректно: {error['msg']}")
        else:
            # Если API возвращает другой формат ошибки
            assert "greater than" in str(error_data["detail"]).lower() or "положительн" in str(error_data["detail"]).lower()
            print(f"\n  Ошибка отрицательной суммы обработана корректно: {error_data['detail']}")

    @pytest.mark.asyncio
    async def test_08_zero_amount_error(self, session):
        """
        Тест 8: Проверка ошибки - перевод нулевой суммы
        """
        sender_username = "john_test8"
        sender_password = "secret123"
        recipient_username = "john2_test8"
        recipient_password = "secret123"

        # Регистрируем пользователей
        await self.register_user(session, sender_username, sender_password, 1000.00)
        await self.register_user(session, recipient_username, recipient_password, 1000.00)

        # Пытаемся перевести нулевую сумму
        status, error_data = await self.create_transfer(
            session,
            sender_username,
            sender_password,
            recipient_username,
            0,
            "test zero sum transfer - error"
        )

        # Проверяем, что получена ошибка валидации
        assert status == 422, f"Ожидался статус 422, получен {status}"
        assert "detail" in error_data

        # Проверяем, что это ошибка валидации Pydantic
        if isinstance(error_data["detail"], list):
            error = error_data["detail"][0]
            assert error["type"] == "greater_than"
            assert "amount" in error["loc"]
            assert error["input"] == 0
            print(f"\n  Ошибка нулевой суммы обработана корректно: {error['msg']}")
        else:
            # Если API возвращает другой формат ошибки
            assert "greater than" in str(error_data["detail"]).lower() or "положительн" in str(error_data["detail"]).lower()
            print(f"\n  Ошибка нулевой суммы обработана корректно: {error_data['detail']}")

    @pytest.mark.asyncio
    async def test_09_nonexistent_user_error(self, session):
        """
        Тест 9: Проверка ошибки - перевод несуществующему пользователю
        """
        sender_username = "john_test9"
        sender_password = "secret123"
        nonexistent_username = "not_exists_user_9999"

        # Регистрируем только отправителя
        await self.register_user(session, sender_username, sender_password, 1000.00)

        # Пытаемся перевести несуществующему пользователю
        status, error_data = await self.create_transfer(
            session,
            sender_username,
            sender_password,
            nonexistent_username,
            10.00,
            "test transfer to nonexisting user"
        )

        # Проверяем, что получена ошибка
        assert status == 404, f"Ожидался статус 404, получен {status}"
        assert "detail" in error_data
        assert nonexistent_username in error_data["detail"] or "не найден" in error_data["detail"]

        print(f"\n  Ошибка перевода несуществующему пользователю обработана корректно: {error_data['detail']}")

    @pytest.mark.asyncio
    async def test_10_deposit(self, session):
        """
        Тест 10: Пополнение баланса на 10
        """
        username = "john_test10"
        password = "secret123"
        initial_balance = 1000.00
        deposit_amount = 10.00

        # Регистрируем пользователя
        await self.register_user(session, username, password, initial_balance)

        # Пополняем баланс
        status, deposit_data = await self.deposit(
            session,
            username,
            password,
            deposit_amount
        )

        # Проверяем успешность операции
        assert status == 200, f"Ожидался статус 200, получен {status}"
        assert "balance" in deposit_data
        assert float(deposit_data["balance"]) == initial_balance + deposit_amount

        print(f"\n  Баланс пополнен на {deposit_amount}, новый баланс: {deposit_data['balance']}")

    @pytest.mark.asyncio
    async def test_11_withdraw(self, session):
        """
        Тест 11: Списание с баланса 10
        """
        username = "john_test11"
        password = "secret123"
        initial_balance = 1000.00
        withdraw_amount = 10.00

        # Регистрируем пользователя
        await self.register_user(session, username, password, initial_balance)

        # Списываем с баланса
        status, withdraw_data = await self.withdraw(
            session,
            username,
            password,
            withdraw_amount
        )

        # Проверяем успешность операции
        assert status == 200, f"Ожидался статус 200, получен {status}"
        assert "balance" in withdraw_data
        assert float(withdraw_data["balance"]) == initial_balance - withdraw_amount

        print(f"\n  С баланса списано {withdraw_amount}, новый баланс: {withdraw_data['balance']}")


if __name__ == "__main__":
    # Для запуска тестов напрямую через python
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))

