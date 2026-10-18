/** In-memory session token. Not written to localStorage. */

let accessToken: string | null = null;

export function setSessionToken(token: string | null): void {
  accessToken = token;
}

export function getSessionToken(): string | null {
  return accessToken;
}
