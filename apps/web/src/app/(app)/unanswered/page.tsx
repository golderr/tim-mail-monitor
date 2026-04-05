import { redirect } from "next/navigation";

export default function UnansweredPage() {
  redirect("/needs-attention");
}
