export type IgAccountType = "demo" | "live";

type IgLoginRequest = {
  identifier: string;
  password: string;
  account_type: IgAccountType;
};

type IgLoginResponse = {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  account_id: string;
  account_type: string;
  lightstreamer_endpoint: string;
};

export type IgSessionStatus = {
  authenticated: boolean;
  account_id: string | null;
  account_type: string | null;
  lightstreamer_endpoint: string | null;
};

function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const json = (await response.json()) as { detail?: string };
    if (json.detail) {
      return json.detail;
    }
  } catch {
    // Ignore parse errors and use status text fallback.
  }

  return response.statusText || "Request failed";
}

export async function connectToIg(payload: IgLoginRequest): Promise<IgLoginResponse> {
  const response = await fetch(`${apiBaseUrl()}/api/v1/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as IgLoginResponse;
}

export async function disconnectFromIg(): Promise<void> {
  const response = await fetch(`${apiBaseUrl()}/api/v1/auth/logout`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
}

export async function getIgSessionStatus(): Promise<IgSessionStatus> {
  const response = await fetch(`${apiBaseUrl()}/api/v1/auth/status`, {
    headers: {
      Accept: "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as IgSessionStatus;
}
