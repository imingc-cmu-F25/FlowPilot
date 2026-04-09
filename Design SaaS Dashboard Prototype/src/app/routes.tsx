import { createBrowserRouter } from "react-router";
import { Home } from "./components/Home";
import { Layout } from "./components/Layout";
import { Dashboard } from "./components/Dashboard";
import { WorkflowBuilder } from "./components/WorkflowBuilder";
import { WorkflowList } from "./components/WorkflowList";
import { ExecutionLogs } from "./components/ExecutionLogs";
import { MonthlyReport } from "./components/MonthlyReport";
import { Settings } from "./components/Settings";
import { Login } from "./components/Login";
import { SignUp } from "./components/SignUp";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Home,
  },
  {
    path: "/login",
    Component: Login,
  },
  {
    path: "/signup",
    Component: SignUp,
  },
  {
    path: "/dashboard",
    Component: Layout,
    children: [
      { index: true, Component: Dashboard },
      { path: "workflows", Component: WorkflowList },
      { path: "workflow/builder/:id?", Component: WorkflowBuilder },
      { path: "logs", Component: ExecutionLogs },
      { path: "reports", Component: MonthlyReport },
      { path: "settings", Component: Settings },
    ],
  },
]);
