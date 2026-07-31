# Half Chat

Чат-бекенд на FastAPI + PostgreSQL с JWT-авторизацией, групповыми комнатами и WebSockets в реальном времени.

## Запуск

```bash
bash dev.sh install      # poetry install
bash dev.sh db:init      # создать БД и таблицы
bash dev.sh db:migrate   # применить миграции
bash dev.sh start        # uvicorn main:app --reload
```

## Конфигурация

Credentials БД — в `half_chat/db_config.py` (gitignored, скопируй с `db_config.example.py`), либо через env `DATABASE_URL`.

| Переменная | По умолчанию | Описание |
|---|---|---|
| `DATABASE_URL` | из `db_config.py` | Подключение к БД |
| `SECRET_KEY` | `super-secret-key-change-in-production` | Ключ для JWT |

## Эндпоинты

### Авторизация

| Метод | Путь | Описание | Auth |
|---|---|---|---|
| `POST` | `/api/register` | Регистрация `{username, password, date_of_birth?}` (новый пользователь авто-добавляется в `general`) | Нет |
| `POST` | `/api/login` | Вход, возвращает `access_token` | Нет |

### Пользователи

| Метод | Путь | Описание | Auth |
|---|---|---|---|
| `GET` | `/api/users?q=` | Поиск пользователей по username | Нет |

### Группы

| Метод | Путь | Описание | Auth |
|---|---|---|---|
| `POST` | `/api/groups` | Создать группу `{name}` (создатель становится участником) | Да |
| `GET` | `/api/groups` | Список групп пользователя с `member_count` | Да |
| `POST` | `/api/groups/{id}/members` | Добавить участника `{username}` | Да |
| `POST` | `/api/groups/{id}/join` | Вступить в группу | Да |
| `POST` | `/api/groups/{id}/leave` | Выйти из группы | Да |
| `GET` | `/api/groups/{id}/members` | Список участников группы | Нет |

### Сообщения

| Метод | Путь | Описание | Auth |
|---|---|---|---|
| `POST` | `/api/messages` | Отправить `{text, group_id, reply_to_id?}`; `@username` в тексте создаёт уведомление | Да |
| `GET` | `/api/messages?group_id=&after_id=&limit=` | История сообщений | Нет |
| `PUT` | `/api/messages/{id}` | Редактировать текст | Да (свои) |
| `DELETE` | `/api/messages/{id}` | Удалить сообщение | Да (свои) |

### WebSockets

| Метод | Путь | Описание |
|---|---|---|
| `WS` | `/api/ws/{group_id}?token=` | События: `new_message`, `update_message`, `delete_message`, `mention` |

## Структура БД

```mermaid
erDiagram
    User {
        int id PK
        string username UK
        string password_hash
        string date_of_birth
    }

    chat_group {
        int id PK
        string name
        string created_by
        string created_at
    }

    group_member {
        int id PK
        int group_id FK
        string username
    }

    Message {
        int id PK
        string username
        string text
        string timestamp
        int group_id FK
        int reply_to_id FK
    }

    Message ||--o{ Message : "ответ на сообщение"
    User ||--o{ group_member : "участвует (по username)"
    chat_group ||--o{ group_member : "содержит"
    chat_group ||--o{ Message : "содержит сообщения"
```

## Миграции

```bash
bash dev.sh db:new-migration "описание"   # alembic revision --autogenerate
bash dev.sh db:migrate                    # alembic upgrade head
```

## Стек

- Python 3.14, FastAPI, SQLModel, PostgreSQL
- WebSockets (`websockets`), JWT (`python-jose`), bcrypt (`passlib`)
- Миграции: Alembic
- Линтеры (dev): black, isort, flake8, mypy
