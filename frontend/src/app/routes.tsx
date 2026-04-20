import { createBrowserRouter } from "react-router";
import { HomePage } from "../pages/HomePage";
import { LoginPage } from "../pages/LoginPage";
import { ProfilePage } from "../pages/ProfilePage";
import { SignUpPage } from "../pages/SignUpPage";
import { DashboardLayout } from "../components/DashboardLayout";
import { DashboardPage } from "../pages/DashboardPage";
import { WorkflowListPage } from "../pages/WorkflowListPage";
import { WorkflowBuilderPage } from "../pages/WorkflowBuilderPage";
import { ReportsPage } from "../pages/ReportsPage";
import { IntegrationsPage } from "../pages/IntegrationsPage";
import { WorkflowRunDetailPage } from "../pages/WorkflowRunDetailPage";

export const router = createBrowserRouter([
  { path: "/", Component: HomePage },
  { path: "/profile", Component: ProfilePage },
  { path: "/login", Component: LoginPage },
  { path: "/signup", Component: SignUpPage },
  {
    path: "/dashboard",
    Component: DashboardLayout,
    children: [
      { index: true, Component: DashboardPage },
      { path: "workflows", Component: WorkflowListPage },
      { path: "workflow/builder/:id?", Component: WorkflowBuilderPage },
      {
        path: "workflow/:wfId/runs/:runId",
        Component: WorkflowRunDetailPage,
      },
      { path: "reports", Component: ReportsPage },
      { path: "integrations", Component: IntegrationsPage },
    ],
  },
]);
