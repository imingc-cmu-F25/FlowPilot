import { Zap } from "lucide-react";

interface AuthCardProps {
  tagline: string;
  children: React.ReactNode;
}

export function AuthCard({ tagline, children }: AuthCardProps) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="rounded-lg border border-gray-200 bg-white p-8 shadow-sm">
          <div className="mb-8 text-center">
            <div className="mb-4 flex justify-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-600">
                <Zap className="h-7 w-7 text-white" />
              </div>
            </div>
            <h1 className="text-2xl font-semibold text-gray-900">FlowPilot</h1>
            <p className="mt-2 text-sm text-gray-600">{tagline}</p>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
