# AGENTS.md

How to run and change Adrobot. See README.md for what the app does.

## Commands

```bash
docker compose up -d                                # Postgres on 5433
cd backend && uv sync && uv run alembic upgrade head
cd backend && uv run fastapi dev app/main.py        # API on :8000, reloads on change
cd frontend && pnpm install && pnpm dev             # UI on :5180, proxies /api to :8000

cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .
cd frontend && pnpm typecheck && pnpm lint && pnpm format:check
```

Run the checks for the side you touched before calling the work done.

## Backend

- Code is split by domain: `app/campaigns` (creator), `app/editor` (streams and offers), `app/offers.py` (catalog), `app/keitaro.py` (API client). A new feature goes into its domain package with its own `router.py`, `service.py` and `schemas.py`.
- Services change the session but never commit. The route commits once, after the whole operation succeeded. Do not add `session.commit()` to a service.
- Only `app/keitaro.py` talks to Keitaro. It has one method per Admin API route and returns plain dicts. Errors come out as `KeitaroError` with the HTTP status; `app/main.py` turns them into responses.
- Keitaro is the source of truth. A fetch overwrites local data, except for offers deleted in Keitaro: those stay as `removed` so the user can bring them back.
- Shares are whole percents that add up to 100. Change them only through `editor/weights.py`.
- Every schema change needs an Alembic migration: `uv run alembic revision --autogenerate -m "..."`, then read the generated file before committing it.
- Tests use `FakeKeitaro` from `tests/conftest.py` and SQLite in memory. When the client gets a new method, add it to the fake as well. Tests never call the real Keitaro.
- Settings are only the three keys in `.env.example`. Domains, groups and traffic sources come from Keitaro, not from config.

## Frontend

- UI is built from shadcn/ui components in `src/components/ui`. Add new ones with `pnpm dlx shadcn@latest add <name>` and do not edit the generated files unless needed. Use semantic colors (`bg-warning`, `text-muted-foreground`), not raw Tailwind colors.
- Server state lives in TanStack Query. Editor mutations return the whole stream, so patch the `["campaign", id]` cache with the response instead of refetching.
- Forms use react-hook-form with a zod schema.
- Every action that waits for Keitaro shows a spinner and disables its control. Errors go to a `sonner` toast.
- Pages are lazy-loaded. Keep each chunk under 500 kB; vendor code is split in `vite.config.ts`.

## Keitaro test instance

- It logs every request, and the reviewer sees the same log. Do not send probe or junk requests, and delete what you create for testing.
- Campaign names must start with `test_kerimov_`.
- `PUT /streams/{id}` with `offers` replaces the whole list. Keitaro does not check that shares add up to 100.

## Git

- Conventional Commits (`feat:`, `fix:`, `chore:`...). The commit-msg hook checks this.
- Pre-commit hooks run ruff, pytest, tsc, oxlint and oxfmt. Fix the cause instead of skipping hooks.
- Never commit `backend/.env`.
