# Nedochat — функции и возможности

Мессенджер на FastAPI + SQLModel + PostgreSQL с JWT-авторизацией, групповыми чатами и WebSockets в реальном времени.

## Пользователи

- **Регистрация и вход**: `POST /api/register`, `POST /api/login` — JWT-токен, пароль хешируется (bcrypt).
- **Профиль**: `username`, `display_name`, `avatar_url`, `date_of_birth`.
- **Редактирование профиля**: имя, отображаемое имя, дата рождения — `PUT /api/users/me`; переименование автоматически обновляет `Message` и `GroupMember`.
- **Аватар**: PNG/JPEG/WebP/GIF до 5 МБ, хранится в `static/avatars/`.
- **Смена пароля**: `PUT /api/users/me/password` (с проверкой текущего).
- **Поиск пользователей**:
  - нечёткий по подстроке `GET /api/users?q=` → `[{username, display_name}]`;
  - точный по уникальному имени `GET /api/users/{username}` (case-sensitive) → полный публичный профиль или 404.
- **Статус онлайн/офлайн**: по активным WebSocket-подключениям.
- **Блокировка (игнор)**: `POST /api/users/{username}/block`, `unblock`, `GET /api/users/me/blocked`. Заблокированный пользователь не может писать вам в личный чат (403), его сообщения скрываются в ленте и поиске.

## Чаты и группы

- **Личные чаты 1-на-1**: `POST /api/directs` (идемпотентно создаёт/возвращает), список — `GET /api/directs`.
- **Группы**: создание с названием и описанием, список групп пользователя с `member_count`, детали, аватар группы.
- **Управление участниками**: добавление, вступление, выход; роли (admin/moderator/member) — только админ.
- **Модерация**: бан/разбан (список забаненных), мьют/анмьют (запрет писать сообщения).
- **Закреплённые сообщения**: один пин на группу (`pinned_message_id`).

## Сообщения

- **Отправка**: текст, ответ (`reply_to_id`), `@username` в тексте создаёт уведомление-упоминание.
- **История**: `GET /api/messages?group_id=&after_id=&limit=`; видимость удалённых — админ в группах, автор в личных чатах.
- **Поиск по тексту**: `GET /api/messages/search?q=&group_id?=` (ILIKE, только в своих группах).
- **Редактирование**: `PUT /api/messages/{id}` — ставит признак «изменено» (`edited_at`).
  - **История версий**: `GET /api/messages/{id}/history` → `{current_text, edited_at, versions:[{text, edited_at}]}`. Каждая правка сохраняется в `MessageVersion`; повторная правка без изменения текста версию не создаёт.
- **Удаление**: soft-delete (строка остаётся, выставляется флаг).
- **Пересылка**: копия в другую группу с информацией об источнике (`forwarded_from_id`/`forwarded_group_id`).
- **Закрепление**: пин/анпин.

## Реальное время (WebSocket)

- `WS /api/ws/{group_id}?token=`
- События: `new_message`, `update_message`, `delete_message`, `mention`, `presence`, `pin_message`, `unpin_message`.

## Права доступа

- Редактирование и удаление сообщения — только автор.
- Роли и бан/мьют участников — только админ группы.
- Доступ к группе — только участники.
- Блокировка пользователя ограничивает общение в личном чате и скрывает сообщения автора.

## Инфраструктура

- **Стек**: FastAPI, SQLModel, PostgreSQL, Alembic; WebSockets (`websockets`), JWT (`python-jose`), bcrypt (`passlib`).
- **Docker**: `app` + `db` (postgres:16); аватарки в named volume `avatars` — не пропадают при пересборке.
- **Качество**: black, isort, flake8, mypy — всё чисто.
- **Миграции**: автогенерация и применение через Alembic (`alembic revision --autogenerate`, `alembic upgrade head`).