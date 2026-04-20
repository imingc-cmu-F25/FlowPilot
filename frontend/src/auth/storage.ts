const USERNAME_KEY = "flowpilot_username";
const TOKEN_KEY = "flowpilot_token";
const USER_EMAILS_KEY = "flowpilot_user_emails";

export function getStoredUsername(): string | null {
  return localStorage.getItem(USERNAME_KEY);
}

export function setStoredUsername(name: string): void {
  localStorage.setItem(USERNAME_KEY, name);
}

export function clearStoredUsername(): void {
  localStorage.removeItem(USERNAME_KEY);
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function getStoredUserEmails(): { address: string; alias: string }[] {
  try {
    const raw = localStorage.getItem(USER_EMAILS_KEY);
    return raw ? (JSON.parse(raw) as { address: string; alias: string }[]) : [];
  } catch {
    return [];
  }
}

export function setStoredUserEmails(emails: { address: string; alias: string }[]): void {
  localStorage.setItem(USER_EMAILS_KEY, JSON.stringify(emails));
}

export function clearStoredUserEmails(): void {
  localStorage.removeItem(USER_EMAILS_KEY);
}
