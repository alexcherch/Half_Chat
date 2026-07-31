# Half Chat — проектные конвенции

## Стек
- Python 3.14, FastAPI, SQLModel, PostgreSQL
- JWT (python-jose), bcrypt (passlib)
- Миграции: Alembic

## Запуск
```bash
bash dev.sh install      # poetry install
bash dev.sh start        # uvicorn main:app --reload
bash dev.sh db:init      # создать БД и таблицы
bash dev.sh db:migrate   # применить миграции
```

## Структура
```
main.py                  # точка входа (from half_chat.main import app)
half_chat/
  main.py                # FastAPI app, CORS, роутеры, seed general group
  config.py              # SECRET_KEY, ALGORITHM, DATABASE_URL
  db_config.py           # локальные credentials (gitignored)
  database.py            # engine, init_db()
  models.py              # SQLModel: User, Group, GroupMember, Message
  schemas.py             # Pydantic: UserCreate, Token, MessageUpdate, Group*, AddMember
  auth.py                # hash/verify password, JWT, get_current_user
  ws.py                  # ConnectionManager (WebSockets по группам)
  routers/
    auth.py              # POST /api/register, /api/login
    groups.py            # CRUD /api/groups, /api/groups/{id}/members
    messages.py          # CRUD /api/messages, GET /api/messages, reply_to_id
scripts/
  init_db.py             # создание БД + таблиц
alembic/
  versions/              # миграции
```

## Эндпоинты
- Все под `/api/`
- Auth через `Authorization: Bearer <token>`
- POST /api/register — `{username, password, date_of_birth?}`
- POST /api/login — `{username, password}` → `{access_token, token_type}`
- POST /api/messages — `{text, group_id, reply_to_id?}` (auth)
- GET /api/messages?group_id=&after_id=&limit= (public)
- PUT/DELETE /api/messages/{id} (auth, только свои)
- WS /api/ws/{group_id} — реальное время: события `new_message`, `update_message`, `delete_message`
- POST /api/groups — `{name}` (auth, создатель становится участником)
- GET /api/groups — список групп пользователя с member_count (auth)
- POST /api/groups/{id}/members — `{username}` (auth)
- POST /api/groups/{id}/join — вступить в группу (auth)
- GET /api/groups/{id}/members (public)

## Models
- Message.reply_to_id — FK на Message.id, опционально
- Message.group_id — FK на chat_group.id, index
- User.date_of_birth — опционально, строка
- Group.__tablename__ = "chat_group"
- GroupMember.__tablename__ = "group_member"

## Timestamps
- Все в ISO-формате (`datetime.now().isoformat()`)
- Фронтенд сам форматирует отображение

## Миграции
```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
```

## Конфигурация
- `DATABASE_URL` — из `half_chat/db_config.py` (gitignored) или `DATABASE_URL` env
- `SECRET_KEY` — из env или дефолт
- Чувствительные данные только в `db_config.py`, не в `config.py`

## Эндпоинты (users)
- GET /api/users?q= — поиск пользователей по username (public)
