"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  connectToIg,
  disconnectFromIg,
  getIgSessionStatus,
  type IgAccountType,
  type IgSessionStatus,
} from "@/lib/api/ig-auth";

const defaultEpic = "/markets/CS.D.EURUSD.CFD.IP";

export function IgConnectForm() {
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [accountType, setAccountType] = useState<IgAccountType>("demo");
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<IgSessionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadStatus() {
      try {
        const nextStatus = await getIgSessionStatus();
        if (!cancelled) {
          setStatus(nextStatus);
        }
      } catch {
        if (!cancelled) {
          setStatus(null);
        }
      }
    }

    void loadStatus();

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (isLoading) {
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      await connectToIg({
        identifier,
        password,
        account_type: accountType,
      });

      const nextStatus = await getIgSessionStatus();
      setStatus(nextStatus);
      router.push(defaultEpic);
      router.refresh();
    } catch (submissionError) {
      setError(
        submissionError instanceof Error
          ? submissionError.message
          : "No se pudo conectar la cuenta de IG",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDisconnect() {
    if (isLoading) {
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      await disconnectFromIg();
      setStatus({ authenticated: false, account_id: null, account_type: null, lightstreamer_endpoint: null });
      router.refresh();
    } catch (disconnectError) {
      setError(
        disconnectError instanceof Error
          ? disconnectError.message
          : "No se pudo desconectar la cuenta de IG",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-6xl items-center justify-center p-4">
      <div className="grid w-full gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="rounded-2xl border border-border bg-surface p-8 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-gray-500">
            Broker Connection
          </p>
          <h1 className="mt-4 max-w-xl font-sans text-4xl font-semibold text-white">
            Conecta IG solo despues de iniciar sesion en la app.
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-gray-400">
            Better Auth ahora protege la aplicacion. Esta pantalla conserva el flujo anterior de IG,
            pero ya no se usa como login principal de PUETTRADE.
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-3">
            <InfoCard label="App auth" value="Better Auth" />
            <InfoCard label="ORM" value="Drizzle + Postgres" />
            <InfoCard label="Broker" value={status?.authenticated ? "IG connected" : "IG pending"} />
          </div>

          <div className="mt-8 rounded-xl border border-border bg-surface-strong p-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-gray-500">
                  Estado actual
                </p>
                <p className="mt-2 font-sans text-lg font-medium text-white">
                  {status?.authenticated ? "Cuenta IG conectada" : "Sin conexion broker"}
                </p>
                <p className="mt-1 font-mono text-xs text-gray-500">
                  {status?.authenticated
                    ? `${status.account_type ?? "unknown"} · ${status.account_id ?? "No account"}`
                    : "La app puede entrar al dashboard sin sesion activa en IG."}
                </p>
              </div>
              <Link
                href={defaultEpic}
                className="rounded-sm border border-border px-4 py-2 font-mono text-xs uppercase tracking-wider text-gray-200 transition hover:border-white/35 hover:text-white"
              >
                Ir al mercado
              </Link>
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-surface p-6 shadow-soft">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-gray-500">
                Login IG
              </p>
              <h2 className="mt-3 font-sans text-2xl font-semibold text-white">
                {status?.authenticated ? "Actualiza o cambia la cuenta conectada" : "Conecta tu cuenta broker"}
              </h2>
            </div>

            <div>
              <label htmlFor="identifier" className="mb-2 block font-mono text-xs uppercase tracking-wider text-gray-400">
                Usuario / ID de cliente
              </label>
              <input
                id="identifier"
                type="text"
                value={identifier}
                onChange={(event) => setIdentifier(event.target.value)}
                className="w-full rounded-sm border border-border bg-surface-strong px-4 py-3 font-mono text-sm text-white placeholder-gray-600 focus:border-accent focus:outline-none"
                placeholder="Ingresa tu usuario de IG"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="mb-2 block font-mono text-xs uppercase tracking-wider text-gray-400">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full rounded-sm border border-border bg-surface-strong px-4 py-3 font-mono text-sm text-white placeholder-gray-600 focus:border-accent focus:outline-none"
                placeholder="Ingresa tu password de IG"
                required
              />
            </div>

            <div>
              <label className="mb-2 block font-mono text-xs uppercase tracking-wider text-gray-400">
                Tipo de cuenta
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setAccountType("demo")}
                  className={`flex-1 rounded-sm border py-3 font-sans text-sm font-semibold transition ${
                    accountType === "demo"
                      ? "border-accent bg-accent text-black"
                      : "border-border text-gray-400 hover:border-gray-500"
                  }`}
                >
                  Demo
                </button>
                <button
                  type="button"
                  onClick={() => setAccountType("live")}
                  className={`flex-1 rounded-sm border py-3 font-sans text-sm font-semibold transition ${
                    accountType === "live"
                      ? "border-accent bg-accent text-black"
                      : "border-border text-gray-400 hover:border-gray-500"
                  }`}
                >
                  Live
                </button>
              </div>
            </div>

            {error ? (
              <div className="rounded-sm border border-danger/30 bg-danger/10 p-3">
                <p className="font-mono text-xs text-danger">{error}</p>
              </div>
            ) : null}

            <div className="flex flex-col gap-3 sm:flex-row">
              <button
                type="submit"
                disabled={isLoading}
                className="flex-1 rounded-sm bg-white py-3 font-sans text-sm font-bold uppercase tracking-wider text-black transition hover:bg-gray-200 disabled:opacity-50"
              >
                {isLoading ? "Conectando..." : "Conectar con IG"}
              </button>

              <button
                type="button"
                onClick={handleDisconnect}
                disabled={isLoading || !status?.authenticated}
                className="rounded-sm border border-border px-4 py-3 font-mono text-xs font-semibold uppercase tracking-wider text-gray-200 transition hover:border-white/35 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                Desconectar
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface-strong p-4">
      <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-gray-500">{label}</p>
      <p className="mt-2 font-sans text-sm font-semibold text-white">{value}</p>
    </div>
  );
}
