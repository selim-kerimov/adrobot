import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";

export default function App() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const response = await fetch("/api/health");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return (await response.json()) as { status: string };
    },
  });

  return (
    <main className="mx-auto max-w-5xl p-8">
      <h1 className="text-2xl font-semibold">Adrobot</h1>
      <Badge className="mt-4" variant={health.isError ? "destructive" : "secondary"}>
        API: {health.isSuccess ? health.data.status : health.isError ? "down" : "…"}
      </Badge>
    </main>
  );
}
