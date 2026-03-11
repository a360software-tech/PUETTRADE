import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trading Platform",
  description: "Trading platform connected with IG Trading API",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-trading-dark text-white antialiased">
        <nav className="border-b border-gray-800 bg-trading-card/50 backdrop-blur-sm">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex h-16 items-center justify-between">
              <div className="flex items-center gap-8">
                <a href="/" className="text-xl font-bold text-primary-400">
                  📈 Trading Platform
                </a>
                <div className="hidden md:flex items-center gap-4">
                  <a
                    href="/dashboard"
                    className="text-sm text-gray-300 hover:text-white transition-colors"
                  >
                    Dashboard
                  </a>
                  <a
                    href="/trading"
                    className="text-sm text-gray-300 hover:text-white transition-colors"
                  >
                    Trading
                  </a>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <a
                  href="/login"
                  className="text-sm text-gray-300 hover:text-white transition-colors"
                >
                  Login
                </a>
                <a
                  href="/register"
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-500 transition-colors"
                >
                  Register
                </a>
              </div>
            </div>
          </div>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
