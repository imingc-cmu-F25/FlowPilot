import { useState } from "react";
import { Outlet, Link, useLocation } from "react-router";
import { Zap, User } from "lucide-react";
import { NavDropdownLink } from "./NavDropdownLink";

const navLinks = [
  { path: "/dashboard", label: "Dashboard" },
  { path: "/dashboard/workflows", label: "Workflows" },
  { path: "/dashboard/reports", label: "Reports" },
  { path: "/dashboard/settings", label: "Settings" },
];

export function DashboardLayout() {
  const location = useLocation();
  const [showUserMenu, setShowUserMenu] = useState(false);

  return (
    <div className="min-h-screen bg-white">
      <nav className="border-b border-gray-200 bg-white">
        <div className="mx-auto px-6">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-8">
              <Link to="/dashboard" className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
                  <Zap className="h-5 w-5 text-white" />
                </div>
                <span className="text-xl font-semibold text-gray-900">
                  FlowPilot
                </span>
              </Link>
              <div className="flex gap-6">
                {navLinks.map((link) => (
                  <Link
                    key={link.path}
                    to={link.path}
                    className={`text-sm font-medium transition-colors ${
                      location.pathname === link.path
                        ? "text-blue-600"
                        : "text-gray-600 hover:text-gray-900"
                    }`}
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            </div>
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-100 transition-colors hover:bg-gray-200"
              >
                <User className="h-5 w-5 text-gray-600" />
              </button>
              {showUserMenu && (
                <div className="absolute right-0 top-12 w-48 rounded-lg border border-gray-200 bg-white shadow-lg">
                  <div className="p-2">
                    <NavDropdownLink
                      to="/profile"
                      onClick={() => setShowUserMenu(false)}
                    >
                      Profile
                    </NavDropdownLink>
                    <NavDropdownLink
                      to="/"
                      onClick={() => setShowUserMenu(false)}
                    >
                      Sign Out
                    </NavDropdownLink>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
