export default function HomePage() {
  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center px-4">
      <div className="text-center max-w-3xl">
        <h1 className="text-5xl font-bold tracking-tight sm:text-6xl">
          <span className="text-primary-400">Smart</span> Trading Platform
        </h1>
        <p className="mt-6 text-lg text-gray-400 leading-8">
          Connect your IG Trading account, monitor markets in real-time, and
          manage your portfolio — all in one place.
        </p>
        <div className="mt-10 flex items-center justify-center gap-4">
          <a
            href="/register"
            className="rounded-lg bg-primary-600 px-6 py-3 text-sm font-semibold text-white shadow-lg hover:bg-primary-500 transition-all hover:shadow-primary-500/25"
          >
            Get Started
          </a>
          <a
            href="/login"
            className="rounded-lg border border-gray-600 px-6 py-3 text-sm font-semibold text-gray-300 hover:border-gray-400 hover:text-white transition-all"
          >
            Sign In
          </a>
        </div>
      </div>
    </div>
  );
}
