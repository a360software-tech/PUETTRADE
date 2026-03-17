"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { login, type AccountType } from "@/lib/api/auth";

export default function LoginPage() {
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [accountType, setAccountType] = useState<AccountType>("demo");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await login({
        identifier,
        password,
        account_type: accountType,
      });
      router.push("/markets/CS.D.EURUSD.CFD.IP");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesión");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md">
      <div className="mb-8 text-center">
        <div className="mb-4 flex items-center justify-center gap-2">
          <div className="h-5 w-5 rounded-sm bg-accent shadow-[0_0_15px_rgba(255,255,255,0.4)]" />
          <span className="font-sans text-2xl font-bold tracking-widest text-white">
            PUET<span className="text-gray-400">TRADE</span>
          </span>
        </div>
        <p className="font-mono text-xs uppercase tracking-widest text-gray-500">
          IG Labs Terminal
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 rounded-lg border border-border bg-surface p-6">
        <div>
          <label htmlFor="identifier" className="mb-2 block font-mono text-xs uppercase tracking-wider text-gray-400">
            Usuario / ID de cliente
          </label>
          <input
            id="identifier"
            type="text"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            className="w-full rounded-sm border border-border bg-surface-strong px-4 py-3 font-mono text-sm text-white placeholder-gray-600 focus:border-accent focus:outline-none"
            placeholder="Ingresa tu usuario de IG"
            required
          />
        </div>

        <div>
          <label htmlFor="password" className="mb-2 block font-mono text-xs uppercase tracking-wider text-gray-400">
            Contraseña
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-sm border border-border bg-surface-strong px-4 py-3 font-mono text-sm text-white placeholder-gray-600 focus:border-accent focus:outline-none"
            placeholder="Ingresa tu contraseña"
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

        {error && (
          <div className="rounded-sm border border-danger/30 bg-danger/10 p-3">
            <p className="font-mono text-xs text-danger">{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className="w-full rounded-sm bg-white py-3 font-sans text-sm font-bold uppercase tracking-wider text-black transition hover:bg-gray-200 disabled:opacity-50"
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Conectando...
            </span>
          ) : (
            "Conectar con IG"
          )}
        </button>
      </form>

      <p className="mt-6 text-center font-mono text-[10px] uppercase tracking-wider text-gray-600">
        Conexión segura con IG Labs API
      </p>
    </div>
  );
}
