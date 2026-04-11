import type { FormEvent } from "react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { setStoredUsername } from "../auth/storage";
import { loginUser } from "../lib/api";
import { AuthCard } from "../components/AuthCard";
import { FormField } from "../components/FormField";

export function LoginPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSignIn = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await loginUser(name.trim(), password);
      setStoredUsername(name.trim());
      navigate("/profile");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthCard tagline="Automate your workflow in minutes">
      {error ? (
        <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
          {error}
        </p>
      ) : null}

      <form onSubmit={handleSignIn} className="space-y-4">
        <FormField
          id="username"
          label="Username"
          value={name}
          onChange={setName}
          placeholder="Enter your username"
          autoComplete="username"
          required
        />
        <FormField
          id="password"
          label="Password"
          type="password"
          value={password}
          onChange={setPassword}
          placeholder="Enter your password"
          autoComplete="current-password"
          required
        />
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? "Signing in…" : "Sign In"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-gray-600">
        Don&apos;t have an account?{" "}
        <Link
          to="/signup"
          className="font-medium text-blue-600 hover:text-blue-700"
        >
          Sign Up
        </Link>
      </p>
    </AuthCard>
  );
}
