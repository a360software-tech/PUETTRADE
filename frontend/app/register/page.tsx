export default function RegisterPage() {
  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl bg-trading-card p-8 shadow-xl border border-gray-800">
        <h2 className="text-2xl font-bold text-center mb-8">Create Account</h2>
        {/* TODO: Implement registration form */}
        <form className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Full Name
            </label>
            <input
              type="text"
              className="w-full rounded-lg border border-gray-700 bg-trading-dark px-4 py-3 text-white placeholder-gray-500 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              placeholder="John Doe"
              disabled
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Email
            </label>
            <input
              type="email"
              className="w-full rounded-lg border border-gray-700 bg-trading-dark px-4 py-3 text-white placeholder-gray-500 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              placeholder="you@example.com"
              disabled
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Password
            </label>
            <input
              type="password"
              className="w-full rounded-lg border border-gray-700 bg-trading-dark px-4 py-3 text-white placeholder-gray-500 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              placeholder="••••••••"
              disabled
            />
          </div>
          <button
            type="submit"
            className="w-full rounded-lg bg-primary-600 py-3 text-sm font-semibold text-white hover:bg-primary-500 transition-colors disabled:opacity-50"
            disabled
          >
            Create Account (Coming Soon)
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-gray-400">
          Already have an account?{" "}
          <a href="/login" className="text-primary-400 hover:text-primary-300">
            Sign In
          </a>
        </p>
      </div>
    </div>
  );
}
