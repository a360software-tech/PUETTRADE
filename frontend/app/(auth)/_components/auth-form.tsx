"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { signIn, signUp } from "@/lib/auth-client";

type AuthFormMode = "login" | "sign-up";

type AuthFormProps = {
  mode: AuthFormMode;
};

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isSignUp = mode === "sign-up";

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (isLoading) {
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      if (isSignUp) {
        const { error: signUpError } = await signUp.email({
          name,
          email,
          password,
          callbackURL: "/markets/CS.D.EURUSD.CFD.IP",
        });

        if (signUpError) {
          throw new Error(signUpError.message || "No se pudo crear la cuenta");
        }
      } else {
        const { error: signInError } = await signIn.email({
          email,
          password,
          callbackURL: "/markets/CS.D.EURUSD.CFD.IP",
          rememberMe: true,
        });

        if (signInError) {
          throw new Error(signInError.message || "No se pudo iniciar sesión");
        }
      }

      router.push("/markets/CS.D.EURUSD.CFD.IP");
      router.refresh();
    } catch (submissionError) {
      setError(
        submissionError instanceof Error
          ? submissionError.message
          : isSignUp
            ? "No se pudo crear la cuenta"
            : "No se pudo iniciar sesión",
      );
    } finally {
      setIsLoading(false);
    }
  }

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
          {isSignUp ? "Create Your Trading Workspace" : "Secure App Access"}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 rounded-lg border border-border bg-surface p-6">
        {isSignUp ? (
          <div>
            <label htmlFor="name" className="mb-2 block font-mono text-xs uppercase tracking-wider text-gray-400">
              Nombre
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="w-full rounded-sm border border-border bg-surface-strong px-4 py-3 font-mono text-sm text-white placeholder-gray-600 focus:border-accent focus:outline-none"
              placeholder="Tu nombre"
              required
            />
          </div>
        ) : null}

        <div>
          <label htmlFor="email" className="mb-2 block font-mono text-xs uppercase tracking-wider text-gray-400">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-sm border border-border bg-surface-strong px-4 py-3 font-mono text-sm text-white placeholder-gray-600 focus:border-accent focus:outline-none"
            placeholder="trader@puettrade.com"
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
            placeholder={isSignUp ? "Minimo 8 caracteres" : "Ingresa tu password"}
            minLength={8}
            required
          />
        </div>

        {error ? (
          <div className="rounded-sm border border-danger/30 bg-danger/10 p-3">
            <p className="font-mono text-xs text-danger">{error}</p>
          </div>
        ) : null}

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
              {isSignUp ? "Creando cuenta..." : "Ingresando..."}
            </span>
          ) : isSignUp ? (
            "Crear cuenta"
          ) : (
            "Entrar a PUETTRADE"
          )}
        </button>
      </form>

      <p className="mt-4 text-center font-mono text-xs text-gray-500">
        {isSignUp ? "Ya tienes cuenta?" : "Aun no tienes cuenta?"}{" "}
        <Link
          href={isSignUp ? "/login" : "/sign-up"}
          className="text-white transition hover:text-gray-300"
        >
          {isSignUp ? "Inicia sesion" : "Crea una cuenta"}
        </Link>
      </p>

      <p className="mt-6 text-center font-mono text-[10px] uppercase tracking-wider text-gray-600">
        Primero entras a la app. Luego conectas tu cuenta de IG dentro del dashboard.
      </p>
    </div>
  );
}
