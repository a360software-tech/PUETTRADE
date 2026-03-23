# PUETTRADE Frontend

Frontend en Next.js 16 para explorar mercados y renderizar velas consumiendo el backend FastAPI.

Ahora la app usa Better Auth para la autenticacion principal y Drizzle ORM con PostgreSQL para persistir usuarios y sesiones.

## Estructura

- `app/` rutas App Router
- `components/ui/` componentes visuales compartidos
- `lib/` clientes y librerias
- `hooks/` hooks compartidos
- `types/` tipos compartidos
- `utils/` utilidades compartidas

## Vista inicial

La app abre en `/markets/CS.D.EURUSD.CFD.IP` y renderiza una vista de velas pensada para trading.

- si el backend tiene sesion activa, consume `GET /api/v1/market-data/{epic}/candles`
- si el backend responde con error o no hay sesion, entra en modo preview con velas simuladas

## Variables de entorno

Crea `frontend/.env.local` a partir de `frontend/.env.example`.

```bash
DATABASE_URL=postgres://postgres:postgres@localhost:5432/puettrade
BETTER_AUTH_SECRET=replace-with-a-random-32-char-secret
BETTER_AUTH_URL=http://localhost:3000
NEXT_PUBLIC_BETTER_AUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Variables clave:

- `DATABASE_URL`: base de datos PostgreSQL para Better Auth y Drizzle
- `BETTER_AUTH_SECRET`: secreto de Better Auth
- `BETTER_AUTH_URL`: URL base de la app para callbacks y cookies
- `NEXT_PUBLIC_BETTER_AUTH_URL`: URL publica usada por el cliente de Better Auth
- `NEXT_PUBLIC_API_BASE_URL`: URL del backend FastAPI / IG bridge

## Autenticacion

- `/login`: acceso principal a la app con Better Auth
- `/sign-up`: creacion de cuenta con email y password
- `/connect-ig`: conexion separada de la cuenta broker de IG ya dentro del dashboard

La sesion de app y la sesion de IG son flujos distintos.

- Better Auth protege la UI del dashboard
- FastAPI sigue gestionando la sesion broker de IG
- si el backend no tiene sesion activa de IG, la UI entra en modo preview

## Base de datos

Schema y ORM:

- `lib/db/schema.ts`
- `lib/db/index.ts`
- `drizzle.config.ts`

Migraciones:

```bash
pnpm db:generate
pnpm db:migrate
```

## Desarrollo

```bash
pnpm dev
```

## Dependencias relevantes

- `next`
- `react`
- `tailwindcss`
- `lightweight-charts`
- `better-auth`
- `drizzle-orm`
- `postgres`
