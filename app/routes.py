from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from app.auth import get_current_user
from app.crud import user_crud, transfer_crud
from models.models import (
    User, UserCreate, BalanceResponse, TransferRequest, TransferResponse,
    DepositRequest, WithdrawRequest, MessageResponse, ErrorResponse
)

# Роутер для пользователей
user_router = APIRouter(prefix="/users", tags=["Users"])

# Роутер для баланса
balance_router = APIRouter(prefix="/balance", tags=["Balance"])

# Роутер для переводов
transfer_router = APIRouter(prefix="/transfers", tags=["Transfers"])


@user_router.post(
    "/register",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя",
    description="Создает нового пользователя с начальным балансом"
)
async def register_user(user_data: UserCreate):
    """Регистрация нового пользователя"""
    try:
        # Проверяем, не существует ли пользователь
        existing_user = await user_crud.get_user_by_username(user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким именем уже существует"
            )

        user = await user_crud.create_user(user_data)
        return user

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка создания пользователя: {str(e)}"
        )


@user_router.get(
    "/me",
    response_model=User,
    summary="Профиль пользователя",
    description="Возвращает информацию о текущем пользователе"
)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Получить профиль текущего пользователя"""
    return current_user


@balance_router.get(
    "/",
    response_model=BalanceResponse,
    summary="Получить баланс",
    description="Возвращает текущий баланс пользователя"
)
async def get_balance(current_user: User = Depends(get_current_user)):
    """Получить баланс текущего пользователя"""
    balance = await user_crud.get_balance(current_user.id)
    if balance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    return BalanceResponse(balance=balance)


@balance_router.post(
    "/deposit",
    response_model=MessageResponse,
    summary="Пополнить баланс",
    description="Пополняет баланс пользователя на указанную сумму"
)
async def deposit_balance(
    deposit_data: DepositRequest,
    current_user: User = Depends(get_current_user)
):
    """Пополнить баланс"""
    try:
        current_balance = await user_crud.get_balance(current_user.id)
        if current_balance is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )

        new_balance = current_balance + deposit_data.amount
        success = await user_crud.update_balance(current_user.id, new_balance)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось обновить баланс"
            )

        return MessageResponse(
            message=f"Баланс пополнен на {deposit_data.amount}. Новый баланс: {new_balance}",
            balance=new_balance,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка пополнения баланса: {str(e)}"
        )


@balance_router.post(
    "/withdraw",
    response_model=MessageResponse,
    summary="Списать с баланса",
    description="Списывает с баланса пользователя указанную сумму"
)
async def withdraw_balance(
    withdraw_data: WithdrawRequest,
    current_user: User = Depends(get_current_user)
):
    """Списать с баланса"""
    try:
        current_balance = await user_crud.get_balance(current_user.id)
        if current_balance is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )

        if current_balance < withdraw_data.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недостаточно средств на балансе"
            )

        new_balance = current_balance - withdraw_data.amount
        success = await user_crud.update_balance(current_user.id, new_balance)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось обновить баланс"
            )

        return MessageResponse(
            message=f"С баланса списано {withdraw_data.amount}. Новый баланс: {new_balance}",
            balance=new_balance,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка списания с баланса: {str(e)}"
        )


@transfer_router.post(
    "/",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать перевод",
    description="Переводит деньги другому пользователю"
)
async def create_transfer(
    transfer_data: TransferRequest,
    current_user: User = Depends(get_current_user)
):
    """Создать перевод другому пользователю"""
    try:
        # Проверяем, что пользователь не переводит сам себе
        if transfer_data.to_username == current_user.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя переводить деньги самому себе"
            )

        # Находим получателя
        recipient = await user_crud.get_user_by_username(transfer_data.to_username)
        if not recipient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Пользователь '{transfer_data.to_username}' не найден"
            )

        # Создаем перевод
        transfer = await transfer_crud.create_transfer(
            from_user_id=current_user.id,
            to_user_id=recipient.id,
            amount=transfer_data.amount,
            description=transfer_data.description
        )

        if not transfer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось создать перевод"
            )

        # Получаем полную информацию о переводе
        transfer_response = await transfer_crud.get_transfer_by_id(transfer.id)
        return transfer_response

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка создания перевода: {str(e)}"
        )


@transfer_router.get(
    "/",
    response_model=List[TransferResponse],
    summary="Получить переводы",
    description="Возвращает список переводов пользователя (отправленных и полученных)"
)
async def get_user_transfers(
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=100, description="Количество записей"),
    offset: int = Query(default=0, ge=0, description="Смещение")
):
    """Получить переводы пользователя"""
    try:
        transfers = await transfer_crud.get_user_transfers(
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        return transfers

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения переводов: {str(e)}"
        )


@transfer_router.get(
    "/{transfer_id}",
    response_model=TransferResponse,
    summary="Получить перевод по ID",
    description="Возвращает информацию о конкретном переводе"
)
async def get_transfer_by_id(
    transfer_id: int,
    current_user: User = Depends(get_current_user)
):
    """Получить перевод по ID"""
    try:
        transfer = await transfer_crud.get_transfer_by_id(transfer_id)

        if not transfer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Перевод не найден"
            )

        # Проверяем, что пользователь имеет доступ к этому переводу
        sender = await user_crud.get_user_by_username(transfer.from_username)
        recipient = await user_crud.get_user_by_username(transfer.to_username)

        if (not sender or not recipient or
            (current_user.id != sender.id and current_user.id != recipient.id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к этому переводу"
            )

        return transfer

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения перевода: {str(e)}"
        )
