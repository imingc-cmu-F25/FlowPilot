const USERNAME_KEY = "flowpilot_username";

export function getStoredUsername(): string | null {
  return localStorage.getItem(USERNAME_KEY);
}

export function setStoredUsername(name: string): void {
  localStorage.setItem(USERNAME_KEY, name);
}

export function clearStoredUsername(): void {
  localStorage.removeItem(USERNAME_KEY);
}
