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
bash dev.sh docker:up    # docker compose up --build (app + postgres)
bash dev.sh docker:down  # docker compose down
```

## Docker
- `Dockerfile` — python:3.14-slim, poetry install --only main (без dev)
- `docker-compose.yml` — сервисы `db` (postgres:16) и `app`
- Конфиг из env: `DATABASE_URL`, `SECRET_KEY` (db_config.py в контейнер не попадает — в .dockerignore)
- При старте: `alembic upgrade head` → `uvicorn main:app`
- uvicorn — в основных зависимостях (нужен для запуска контейнера)

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
- POST /api/messages/{id}/forward — `{group_id}` (auth), копия в др. группу с forwarded_from_id/forwarded_group_id
- POST /api/messages/{id}/pin — закрепить (auth, один пин на группу в chat_group.pinned_message_id)
- POST /api/messages/{id}/unpin — открепить (auth)
- WS /api/ws/{group_id}?token= — реальное время: события `new_message`, `update_message`, `delete_message`, `mention`, `presence`, `pin_message`, `unpin_message`
- POST /api/groups — `{name}` (auth, создатель становится участником)
- GET /api/groups — список групп пользователя с member_count (auth)
- POST /api/groups/{id}/members — `{username}` (auth)
- POST /api/groups/{id}/join — вступить в группу (auth)
- GET /api/groups/{id}/members — список участников с ролями (public)
- PUT /api/groups/{id}/members/{username}/role — `{role}` admin/moderator/member (auth, только админ)
- DELETE /api/groups/{id}/members/{username} — удалить участника (auth, только админ)
- POST /api/groups/{id}/members/{username}/ban — забанить (auth, только админ, запрещает вступление/добавление)
- POST /api/groups/{id}/members/{username}/unban — разбанить (auth, только админ)
- GET /api/groups/{id}/banned — список забаненных (auth, только админ)
- POST /api/groups/{id}/members/{username}/mute — запрет писать (auth, только админ; блокирует POST /messages и forward)
- POST /api/groups/{id}/members/{username}/unmute — снять запрет (auth, только админ)
- POST /api/directs — `{username}`, создать/вернуть личный чат 1-на-1 (auth, idempotent)
- GET /api/directs — список личных чатов с peer (auth)
- Личные чаты: Group.is_direct=True, ровно 2 участника; в них запрещены add-member/join/leave

## Models
- Message.reply_to_id — FK на Message.id, опционально
- Message.forwarded_from_id — FK на Message.id (ON DELETE SET NULL), forwarded_group_id — исходная группа
- Message.group_id — FK на chat_group.id, index
- User.date_of_birth — опционально, строка
- Group.__tablename__ = "chat_group"
- Group.is_direct — bool (по умолчанию False), личные чаты
- Group.pinned_message_id — закреплённое сообщение группы (один пин)
- GroupMember.__tablename__ = "group_member"
- GroupMember.role — admin/moderator/member (по умолчанию member; создатель группы становится admin)
- GroupMember.muted — bool, запрет писать сообщения
- GroupBan.__tablename__ = "group_ban" — бан-лист (group_id, username)

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
- GET /api/users/{username}/status — статус онлайн/офлайн (public), по активным WS-подключениям
- GET /api/users/me — профиль текущего пользователя (auth)
- PUT /api/users/me — изменить username/date_of_birth (auth, обновляет Message/GroupMember)
- PUT /api/users/me/password — сменить пароль (auth, `{current_password, new_password}`)
