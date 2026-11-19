"""Проверка retry wrapper без изменения банковских балансов."""
from psycopg.errors import SerializationFailure

from app.routes.transfers import with_retry

counter = {"calls": 0}


def simulated_operation():
    counter["calls"] += 1
    if counter["calls"] < 3:
        raise SerializationFailure("simulated serialization failure")
    return {"status": "success"}


result, attempts = with_retry(simulated_operation, max_retries=3)
print("Result:", result)
print("Function calls:", counter["calls"])
print("Retry attempts:", attempts)
