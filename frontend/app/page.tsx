import { redirect } from "next/navigation";

import { getServerSession } from "@/lib/session";

export default async function HomePage() {
  const session = await getServerSession();

  redirect(session ? "/markets/CS.D.EURUSD.CFD.IP" : "/login");
}
