# Context for AI Assistant (ShotMemory Project)

You are acting as a Senior Full-Stack Engineer working on the "ShotMemory" (aka Earth Diary) project.
Please adhere to the following technical constraints, coding style, and architecture guidelines.

## 1. Tech Stack & Versions
- **Frontend**: React 19, TypeScript 5.x, Vite, Tailwind CSS v4, HeroUI, Redux Toolkit, React Router v7.
- **Backend**: Python 3.13, FastAPI, SQLAlchemy (Async), Pydantic v2, PostgreSQL, `uv` package manager.

## 2. Architecture & Design Patterns

### Backend (FastAPI)
- **Structure**: Follow `Router -> Service -> Repo -> Database` pattern.
  - **Routers**: Handle HTTP request/response, dependency injection (`SessionDep`).
  - **Services**: Business logic only. No raw SQL here.
  - **Repos**: CRUD operations using SQLAlchemy models.
- **Authentication**:
  - Strict Dual-Token (Access/Refresh) rotation system.
  - Tokens must be stored in `HTTPOnly Cookies`.
  - Use `upsert` logic for device-bound refresh tokens.
- **Typing**: Use strict Python type hints (`str | None` instead of `Optional[str]`).
- **Response**: Always wrap return data in `UnifyResponse` class structure.

### Frontend (React)
- **Component Style**: Functional components with Hooks.
- **State Management**:
  - Global server state: Redux Toolkit Query (RTK Query).
  - Global UI state: Redux Slices.
  - Local state: `useState` / `useReducer`.
- **Styling**: Tailwind CSS v4 utility classes. Avoid `.css` files unless for global resets.
- **Strict Mode**: No `any` types. Define interfaces for all Props and API responses.

## 3. Coding Standards

### General
- **Language**: Comments in Chinese/English mixed is okay, but commit messages and documentation should be clear.
- **Error Handling**:
  - Backend: Raise `BusinessException(code=APIStatus.X, ...)` instead of generic HTTP exceptions.
  - Frontend: Handle errors in `useEffect` or RTK Query `isError` states visually.

### Backend Specifics
- **Async/Await**: All DB I/O must be asynchronous (`await db.execute(...)`).
- **Pydantic**: Use `ConfigDict` for configuration.

### Frontend Specifics
- **Folder Structure**: Feature-based (e.g., `src/features/auth/`).
- **Path Aliases**: Use absolute imports (if configured) or consistent relative paths.

## 4. Current Project State (Context)
- **Auth Module**: Fully implemented (Login, Register, Refresh, Logout, Account Deletion).
- **Database**: `users` and `refresh_tokens` tables are set up.
- **Config**: Environment variables management via `pydantic-settings` is active.

## 5. Your Task Guidelines
- When asked to write code, provide the **full file content** if the file is small, or strictly scoped diffs.
- Always check for **Type Safety** before outputting code.
- If modifying an API, update both the Backend Router and the Frontend Type Definition/Service.
