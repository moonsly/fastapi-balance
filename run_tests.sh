#!/bin/bash

# Скрипт для запуска E2E тестов Balance Service API

set -e

# Параметры по умолчанию
PYTEST_ARGS="-v -s"

# Если переданы аргументы, используем их
if [ $# -gt 0 ]; then
    PYTEST_ARGS="$@"
fi

# Запуск pytest
pytest tests/ $PYTEST_ARGS

# Код выхода pytest
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}=== Все тесты пройдены успешно ===${NC}"
else
    echo -e "\n${RED}=== Некоторые тесты провалились ===${NC}"
fi

exit $TEST_EXIT_CODE

