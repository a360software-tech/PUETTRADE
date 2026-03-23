import { redirect } from "next/navigation";

import { getServerSession } from "@/lib/session";

export default async function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await getServerSession();

  if (!session) {
    redirect("/login");
  }

  return <div className="min-h-screen">{children}</div>;
}
