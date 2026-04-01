import { redirect } from "next/navigation";

import { hasSession } from "@/lib/auth";

export default async function Home() {
  redirect((await hasSession()) ? "/dashboard" : "/login");
}
