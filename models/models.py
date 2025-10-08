from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, validator


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Имя пользователя")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Пароль пользователя")
    initial_balance: Optional[Decimal] = Field(default=Decimal('0.00'), ge=0, description="Начальный баланс")


class User(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    balance: Decimal = Field(..., ge=0, description="Текущий баланс")
    created_at: datetime
    updated_at: datetime


class BalanceResponse(BaseModel):
    balance: Decimal = Field(..., ge=0, description="Текущий баланс")


class TransferRequest(BaseModel):
    to_username: str = Field(..., min_length=3, max_length=50, description="Получатель перевода")
    amount: Decimal = Field(..., gt=0, description="Сумма перевода")
    description: Optional[str] = Field(default=None, max_length=255, description="Описание перевода")

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Сумма перевода должна быть больше нуля')
        # Округляем до 2 знаков после запятой
        return v.quantize(Decimal('0.01'))


class Transfer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_user_id: int
    to_user_id: int
    amount: Decimal = Field(..., gt=0, description="Сумма перевода")
    description: Optional[str] = Field(default=None, description="Описание перевода")
    created_at: datetime


class TransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_username: str
    to_username: str
    amount: Decimal
    description: Optional[str]
    created_at: datetime


class DepositRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Сумма пополнения")

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Сумма пополнения должна быть больше нуля')
        return v.quantize(Decimal('0.01'))


class WithdrawRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Сумма списания")

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Сумма списания должна быть больше нуля')
        return v.quantize(Decimal('0.01'))


class MessageResponse(BaseModel):
    message: str
    balance: Optional[Decimal]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
