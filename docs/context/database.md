# Database (PostgreSQL)

One `chat_thread` per meeting session; every event (transcript, OCR text, typed message, agent response) is a `chat_message`. All ids are `uuid` (`gen_random_uuid()`; the app also passes the event's uuid4 so an event keeps its id from bus to DB).

## Code layout
- `models/`: SQLAlchemy 2.0 ORM models (`base.py`, `chat_thread.py`, `chat_message.py`). The `metadata` column is the attribute `meta` (declarative reserves `metadata`). Tables are created with `Base.metadata.create_all` when the store starts; there are no migrations yet.
- `records/`: frozen dataclasses (`NewMessage`, `Message`, `Thread`) that the rest of the app uses. ORM objects never leave `session/store.py`. No pydantic.
- `session/store.py`: `SessionStore` protocol, `SqlAlchemySessionStore` (Postgres via `postgresql+psycopg`, QueuePool sized from `DB_POOL_*`), `InMemorySessionStore` (tests).

## chat_thread
`id`, `title`, `status` (active|ended), `message_count` (incremented in the same transaction as each message insert; its value is the new message's `seq`), `summary`, `metadata jsonb`, `ended_at`, `created_at`, `updated_at`.

## chat_message
`id`, `thread_id` (FK, cascade), `parent_message_id` (the input a response answers), `seq` (per-thread order, unique with thread_id), `role` (user|assistant|system), `source` (audio|screen|manual|agent), `agent` (conversor|screen_analyzer|chat), `speaker` (interviewer|interviewee|unknown), `message_content`, `model`, `input_tokens`, `output_tokens`, `latency_ms`, `metadata jsonb`, `created_at`, `updated_at`.

Indexes: `chat_message(thread_id, seq)`, `chat_thread(created_at desc)`.

Store tests marked `db` (`pytest -m db`) run in a throwaway `amc_test` schema of the running Postgres and drop it afterwards.
