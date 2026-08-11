export type LoginPayload = {
  tenant_slug: string;
  email: string;
  password: string;
  mfa_code?: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export async function apiRequest<TResponse>(
  path: string,
  init: RequestInit = {}
): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...init.headers
    }
  });

  if (!response.ok) {
    const problem = await response.json().catch(() => null);
    throw new Error(problem?.detail ?? `API request failed with status ${response.status}`);
  }

  return (await response.json()) as TResponse;
}

export function login(payload: LoginPayload): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

// ---------------------------------------------------------------------------
// Data sources
// ---------------------------------------------------------------------------

export type DataSourceCreatePayload = {
  name: string;
  source_type: string;
  config?: Record<string, string>;
};

export type DataSource = {
  id: string;
  name: string;
  source_type: string;
  is_active: boolean;
  created_at: string;
};

export type CursorPage<T> = {
  items: T[];
  next_cursor?: string | null;
};

export type UploadResult = {
  processed: number;
  normalized: boolean;
  trace_id?: string;
  observables?: number;
};

export function listDataSources(): Promise<CursorPage<DataSource>> {
  return apiRequest<CursorPage<DataSource>>("/data-sources", { method: "GET" });
}

export function createDataSource(payload: DataSourceCreatePayload): Promise<DataSource> {
  return apiRequest<DataSource>("/data-sources", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function deleteDataSource(sourceId: string): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/data-sources/${encodeURIComponent(sourceId)}`, {
    method: "DELETE"
  });
}

/**
 * Upload raw event text (CEF / syslog / CSV rows) to a csv-type data source.
 * The backend runs every line through normalization, detection, correlation,
 * and risk scoring; normalized becomes true when the pipeline completed.
 */
export function uploadToDataSource(
  sourceId: string,
  rawText: string
): Promise<UploadResult> {
  const form = new FormData();
  form.append(
    "file",
    new Blob([rawText], { type: "text/plain" }),
    "batch.csv"
  );
  const path = `${API_BASE_URL}/data-sources/${encodeURIComponent(sourceId)}/upload`;
  return fetch(path, {
    method: "POST",
    headers: {
      authorization: `Bearer ${typeof window !== "undefined" ? window.localStorage.getItem("access_token") ?? "" : ""}`
    },
    body: form
  }).then(async (response) => {
    if (!response.ok) {
      const problem = await response.json().catch(() => null);
      throw new Error(
        problem?.detail ?? `API request failed with status ${response.status}`
      );
    }
    const data = (await response.json()) as { processed?: number };
    return {
      processed: data.processed ?? 0,
      normalized: (data.processed ?? 0) > 0,
      trace_id: "csv",
      observables: 0
    };
  });
}
