# PUETTRADE Frontend

Frontend en Next.js 16 para explorar mercados y renderizar velas consumiendo el backend FastAPI.

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

Crea `frontend/.env.local` si quieres cambiar la URL del backend:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
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
