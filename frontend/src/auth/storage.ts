const USERNAME_KEY = "flowpilot_username";
const TOKEN_KEY = "flowpilot_token";

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
