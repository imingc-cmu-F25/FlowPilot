import { Outlet } from "react-router";
import { DashboardTopBar } from "./DashboardTopBar";

export function DashboardLayout() {
  return (
    <div className="min-h-screen bg-white">
      <DashboardTopBar />
      <main>
        <Outlet />
      </main>
    </div>
  );
}
