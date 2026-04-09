import { createBrowserRouter } from "react-router";
import { HomePage } from "../pages/HomePage";
import { LoginPage } from "../pages/LoginPage";
import { ProfilePage } from "../pages/ProfilePage";
import { SignUpPage } from "../pages/SignUpPage";

export const router = createBrowserRouter([
  { path: "/", Component: HomePage },
  { path: "/profile", Component: ProfilePage },
  { path: "/login", Component: LoginPage },
  { path: "/signup", Component: SignUpPage },
]);
