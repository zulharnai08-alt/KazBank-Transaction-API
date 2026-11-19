# KazBank — Step 5: Error Handling in psycopg3

Этот patch заменяет два файла в существующем Step 4 проекте:

- `app/routes/customers.py`
- `app/routes/transfers.py`

Не заменяйте `.env`, `run.py`, `app/db.py` или `app/__init__.py`.

## Требования Step 5

1. `POST /customers` обрабатывает `UniqueViolation` → HTTP 409.
2. `POST /customers` обрабатывает `NotNullViolation` → HTTP 400.
3. Ошибка подключения `OperationalError` → HTTP 503.
4. `with_retry()` повторяет транзакцию при `SerializationFailure` (SQLSTATE 40001) до 3 попыток и применяется к `/transfer`.
5. Тестирование выполняется через PowerShell запросы ниже.

## Установка и запуск

Из папки `kazbank_project` в терминале VS Code:

```powershell
pip install -r requirements.txt
python run.py
```

Оставьте этот терминал открытым. Все запросы запускайте во втором терминале.

## Test A — duplicate email (ожидается HTTP 409)

В seed данных уже есть `arman@example.com`:

```powershell
$body = @{
    full_name = "Duplicate Test"
    city = "Almaty"
    email = "arman@example.com"
} | ConvertTo-Json

try {
    Invoke-RestMethod -Uri "http://127.0.0.1:5000/customers" -Method POST -ContentType "application/json" -Body $body
} catch {
    [int]$_.Exception.Response.StatusCode
    $_.ErrorDetails.Message
}
```

Ожидаемый HTTP статус: `409` и сообщение `Email already registered`.

## Test B — missing required field / NotNullViolation (ожидается HTTP 400)

В таблице `customers` поля `full_name` и `email` имеют NOT NULL. Здесь намеренно отсутствует `full_name`:

```powershell
$body = @{
    city = "Almaty"
    email = "missing-name-step5@example.com"
} | ConvertTo-Json

try {
    Invoke-RestMethod -Uri "http://127.0.0.1:5000/customers" -Method POST -ContentType "application/json" -Body $body
} catch {
    [int]$_.Exception.Response.StatusCode
    $_.ErrorDetails.Message
}
```

Ожидаемый HTTP статус: `400`, сообщение содержит `Missing required field`.

## Test C — normal customer creation (ожидается HTTP 201)

Используйте уникальный email:

```powershell
$body = @{
    full_name = "Step Five Test"
    city = "Almaty"
    email = "step5-test-001@example.com"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:5000/customers" -Method POST -ContentType "application/json" -Body $body
```

Ожидаемый HTTP статус: `201`. Если запускаете запрос повторно, второй запрос должен вернуть `409`, так как email уже занят.

## Test D — database unavailable / OperationalError (ожидается HTTP 503)

Этот тест временно останавливает PostgreSQL. Сохраните все данные и выполняйте его только в конце.

1. Откройте PowerShell **от имени администратора**.
2. Остановите PostgreSQL:

```powershell
Stop-Service postgresql-x64-18
```

3. Пока служба остановлена, во втором терминале отправьте запрос к Flask:

```powershell
$body = @{
    full_name = "Database Down Test"
    city = "Almaty"
    email = "db-down-step5@example.com"
} | ConvertTo-Json

try {
    Invoke-RestMethod -Uri "http://127.0.0.1:5000/customers" -Method POST -ContentType "application/json" -Body $body
} catch {
    [int]$_.Exception.Response.StatusCode
    $_.ErrorDetails.Message
}
```

Ожидаемый HTTP статус: `503` и `Database unavailable`.

4. **Сразу восстановите PostgreSQL** в административном PowerShell:

```powershell
Start-Service postgresql-x64-18
```

Перед продолжением убедитесь, что служба снова имеет статус `Running`.

## Test E — retry wrapper на SerializationFailure

Этот тест искусственно вызывает два SerializationFailure, затем успешный результат. Он проверяет сам retry wrapper без изменения банковских балансов:

```powershell
python test_retry.py
```

Ожидаемый вывод:

```text
Result: {'status': 'success'}
Function calls: 3
Retry attempts: 3
```

## Test F — POST /transfer

Убедитесь, что PostgreSQL снова работает и Flask запущен:

```powershell
$body = @{
    from_account_id = 1
    to_account_id = 2
    amount = 1000
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:5000/transfer" -Method POST -ContentType "application/json" -Body $body
```

Ожидается `status = success`, `isolation_level = SERIALIZABLE` и `retry_attempts` (обычно 1; при конкурентном конфликте может быть 2 или 3).

## Сдача

Сохраните скриншоты реальных результатов:

- duplicate email → 409;
- missing required field → 400;
- database stopped → 503;
- `test_retry.py` показывает 3 вызова после двух ошибок сериализации;
- успешный `/transfer` с `SERIALIZABLE` и `retry_attempts`.

Не отправляйте `.env` или пароль PostgreSQL в GitLab.
