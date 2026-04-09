import { HomeTopBar } from "../components/HomeTopBar";

export function HomePage() {
  return (
    <div className="min-h-screen bg-white">
      <HomeTopBar />
      <main className="flex min-h-[calc(100svh-4rem)] items-center justify-center px-6">
        <h1 className="text-5xl font-medium tracking-tight text-gray-900">FlowPilot</h1>
      </main>
    </div>
  );
}
