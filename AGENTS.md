# Nedochat — проектные конвенции

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
- `Dockerfile` — python:3.14-slim, pip install -r requirements.txt (без dev)
- `requirements.txt` — генерируется из poetry.lock: `poetry export -f requirements.txt --output requirements.txt --only main` (требует плагин `poetry-plugin-export`)
- `docker-compose.yml` — сервисы `db` (postgres:16) и `app`
- Конфиг из env: `DATABASE_URL`, `SECRET_KEY` (db_config.py в контейнер не попадает — в .dockerignore)
- При старте: `alembic upgrade head` → `uvicorn main:app`
- uvicorn — в основных зависимостях (нужен для запуска контейнера)

## Структура
```
main.py                  # точка входа (from nedochat.main import app)
nedochat/
  main.py                # FastAPI app, CORS, роутеры, seed general group
  config.py              # SECRET_KEY, ALGORITHM, DATABASE_URL
  db_config.py           # локальные credentials (gitignored)
  database.py            # engine, init_db()
  models.py              # SQLModel: User, Group, GroupMember, Message, MessageVersion, UserBlock
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
- POST /api/register — `{username, password, date_of_birth?, display_name?}`
- POST /api/login — `{username, password}` → `{access_token, token_type}`
- POST /api/messages — `{text, group_id, reply_to_id?}` (auth)
- GET /api/messages?group_id=&after_id=&limit= (auth) — soft-delete: в группах удале. видны только админу, в личных чатах — только автору
- GET /api/messages/search?q=&group_id?=&limit= (auth) — поиск по тексту сообщений (ILIKE) в группах пользователя, с теми же правилами видимости удалённых
- PUT /api/messages/{id} (auth, только свои) — при изменении текста ставит `edited_at` и сохраняет предыдущий текст в `MessageVersion`
- GET /api/messages/{id}/history (auth, автор или участник группы) — `{message_id, current_text, edited_at, versions:[{text, edited_at}]}` (версии = прошлые тексты по порядку)
- DELETE /api/messages/{id} (auth, только свои) — soft-delete (столбец deleted, строку не стирает)
- POST /api/messages/{id}/forward — `{group_id}` (auth), копия в др. группу с forwarded_from_id/forwarded_group_id
- POST /api/messages/{id}/pin — закрепить (auth, один пин на группу в chat_group.pinned_message_id)
- POST /api/messages/{id}/unpin — открепить (auth)
- WS /api/ws/{group_id}?token= — реальное время: события `new_message`, `update_message`, `delete_message`, `mention`, `presence`, `pin_message`, `unpin_message`
- POST /api/groups — `{name, description?}` (auth, создатель становится участником)
- GET /api/groups — список групп пользователя с member_count (auth)
- GET /api/groups/{id} — детали группы (auth, только участник)
- PUT /api/groups/{id} — изменить name/description (auth, только админ, не для личных чатов)
- POST /api/groups/{id}/avatar — загрузить аватар группы (auth, только админ; PNG/JPEG/WebP/GIF, макс. 5 МБ)
- POST /api/groups/{id}/members — `{username}` (auth)
- POST /api/groups/{id}/join — вступить в группу (auth)
- GET /api/groups/{id}/members — список участников с ролями (auth)
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
- Message.deleted — bool (по умолчанию False), soft-delete
- Message.edited_at — Optional[str], ставится при редактировании (признак «изменено»)
- MessageVersion — история: message_id FK, text (прошлый текст), edited_at (когда заменён)
- Message.group_id — FK на chat_group.id, index
- User.date_of_birth — опционально, строка
- User.display_name — опционально, отображаемое имя (отдельно от username)
- User.avatar_url — опционально, путь к аватарке (/static/avatars/u{id}{ext})
- Group.__tablename__ = "chat_group"
- Group.description — опционально
- Group.avatar_url — опционально, аватар группы (/static/avatars/g{id}{ext})
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
- `DATABASE_URL` — из `nedochat/db_config.py` (gitignored) или `DATABASE_URL` env
- `SECRET_KEY` — из env или дефолт
- Чувствительные данные только в `db_config.py`, не в `config.py`

## Эндпоинты (users)
- GET /api/users?q= — поиск пользователей по username (public) — `[{username, display_name}]`
- GET /api/users/{username}/status — статус онлайн/офлайн (public), по активным WS-подключениям
- GET /api/users/me — профиль текущего пользователя (auth) — `{username, display_name, date_of_birth, avatar_url}`
- PUT /api/users/me — изменить username/display_name/date_of_birth (auth, обновляет Message/GroupMember)
- PUT /api/users/me/avatar — загрузить аватар (auth, `multipart/form-data`, поле `file`; PNG/JPEG/WebP/GIF, макс. 5 МБ; файл в `static/avatars/u{id}{ext}`, возвращает `avatar_url`)
- PUT /api/users/me/password — сменить пароль (auth, `{current_password, new_password}`)
- POST /api/users/{username}/block — заблокировать пользователя (auth; idempotent-ish, 400 если уже в списке; запрещает ему писать вам в личку)
- POST /api/users/{username}/unblock — разблокировать (auth)
- GET /api/users/me/blocked — список заблокированных username (auth)

## Блокировка (игнор)
- Таблица `user_block` (blocker_id, blocked_id, unique pair); хранит ID, а не username — не ломается при переименовании
- Заблокированный не может писать/пересылать в личный чат блокирующего (`_check_direct_blocked`, 403)
- Сообщения авторов из чёрного списка скрываются в `GET /api/messages` и `/api/messages/search` (`_blocked_usernames`)

## Аватары
- Общая логика в `nedochat/avatars.py` (`save_avatar`, `delete_avatar`, `is_valid_image`); юзер — `u{id}{ext}`, группа — `g{id}{ext}`
- В Docker `static/` — named volume `avatars` (не пропадают при пересборке)
- Валидация: размер ≤ 5 МБ (413), content-type + магическая сигнатура изображения (400)
