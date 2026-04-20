import type { FormEvent } from "react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { setStoredUsername, setStoredUserEmails } from "../auth/storage";
import { registerUser } from "../lib/api";
import { AuthCard } from "../components/AuthCard";
import { FormField } from "../components/FormField";

export function SignUpPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSignUp = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    setSubmitting(true);
    try {
      const result = await registerUser({
        name: name.trim(),
        password,
        email: email.trim() || null,
      });
      setStoredUsername(name.trim());
      if (result.user?.emails) setStoredUserEmails(result.user.emails);
      navigate("/profile");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthCard tagline="Create your account to get started">
      {error ? (
        <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
          {error}
        </p>
      ) : null}

      <form onSubmit={handleSignUp} className="space-y-4">
        <FormField
          id="username"
          label="Username"
          value={name}
          onChange={setName}
          placeholder="Choose a username"
          autoComplete="username"
          required
        />
        <FormField
          id="email"
          label="Email"
          type="email"
          value={email}
          onChange={setEmail}
          placeholder="Enter your email (optional)"
          autoComplete="email"
        />
        <FormField
          id="password"
          label="Password"
          type="password"
          value={password}
          onChange={setPassword}
          placeholder="Create a password"
          autoComplete="new-password"
          required
        />
        <FormField
          id="confirmPassword"
          label="Confirm Password"
          type="password"
          value={confirmPassword}
          onChange={setConfirmPassword}
          placeholder="Confirm your password"
          autoComplete="new-password"
          required
        />
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? "Creating account…" : "Create Account"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-gray-600">
        Already have an account?{" "}
        <Link
          to="/login"
          className="font-medium text-blue-600 hover:text-blue-700"
        >
          Sign In
        </Link>
      </p>
    </AuthCard>
  );
}
