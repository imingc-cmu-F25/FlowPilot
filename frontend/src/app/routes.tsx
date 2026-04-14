import { createBrowserRouter } from "react-router";
import { HomePage } from "../pages/HomePage";
import { LoginPage } from "../pages/LoginPage";
import { ProfilePage } from "../pages/ProfilePage";
import { SignUpPage } from "../pages/SignUpPage";
import { DashboardLayout } from "../components/DashboardLayout";
import { WorkflowListPage } from "../pages/WorkflowListPage";
import { WorkflowBuilderPage } from "../pages/WorkflowBuilderPage";
import { ReportsPage } from "../pages/ReportsPage";

export const router = createBrowserRouter([
  { path: "/", Component: HomePage },
  { path: "/profile", Component: ProfilePage },
  { path: "/login", Component: LoginPage },
  { path: "/signup", Component: SignUpPage },
  {
    path: "/dashboard",
    Component: DashboardLayout,
    children: [
      { path: "workflows", Component: WorkflowListPage },
      { path: "workflow/builder/:id?", Component: WorkflowBuilderPage },
      { path: "reports", Component: ReportsPage },
    ],
  },
]);
