# Half Chat

Чат-бекенд на FastAPI + PostgreSQL с JWT-авторизацией и групповыми комнатами.

## Запуск

```bash
poetry install
poetry run uvicorn main:app --host 0.0.0.0 --port 8000
```

## Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `DATABASE_URL` | `postgresql://user:password@localhost:5432/half_chat` | Подключение к БД |
| `SECRET_KEY` | `super-secret-key-change-in-production` | Ключ для JWT |

## Эндпоинты

### Авторизация

| Метод | Путь | Описание | Auth |
|---|---|---|---|
| `POST` | `/api/register` | Регистрация `{username, password}` | Нет |
| `POST` | `/api/login` | Вход, возвращает `access_token` | Нет |

### Группы

| Метод | Путь | Описание | Auth |
|---|---|---|---|
| `POST` | `/api/groups` | Создать группу `{name}` | Да |
| `GET` | `/api/groups` | Список всех групп | Нет |
| `POST` | `/api/groups/{id}/members` | Добавить участника `{username}` | Да |
| `GET` | `/api/groups/{id}/members` | Список участников группы | Нет |

### Сообщения

| Метод | Путь | Описание | Auth |
|---|---|---|---|
| `POST` | `/api/messages` | Отправить сообщение `{text, group_id}` | Да |
| `GET` | `/api/messages?group_id=&after_id=&limit=` | История сообщений | Нет |
| `PUT` | `/api/messages/{id}` | Редактировать текст | Да (свои) |
| `DELETE` | `/api/messages/{id}` | Удалить сообщение | Да (свои) |

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
    }

    User ||--o{ group_member : "участвует (по username)"
    chat_group ||--o{ group_member : "содержит"
    chat_group ||--o{ Message : "cодержит сообщения"
```

## Стек

- Python 3.14, FastAPI, SQLModel, PostgreSQL
- JWT (`python-jose`), bcrypt (`passlib`)
