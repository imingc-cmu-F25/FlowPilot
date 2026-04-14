const envBase = (
  import.meta.env.VITE_API_BASE_URL as string | undefined
)?.replace(/\/$/, "");

export const API_BASE = import.meta.env.PROD
  ? (envBase ?? "")
  : envBase || "http://127.0.0.1:8000/api";

export type EmailAddress = { address: string; alias: string };

export type UserPublic = { name: string; emails: EmailAddress[] };

export type AuthResponse = {
  ok: boolean;
  message: string;
  user: UserPublic | null;
  token: string | null;
};

function extractDetail(data: unknown): string | undefined {
  if (data && typeof data === "object" && "detail" in data) {
    const d = (data as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (d && typeof d === "object" && "message" in d) {
      return String((d as { message: unknown }).message);
    }
    if (Array.isArray(d) && d[0] && typeof d[0] === "object" && "msg" in d[0]) {
      return String((d[0] as { msg: unknown }).msg);
    }
  }
  return undefined;
}

async function parseBody(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (e) {
    if (e instanceof TypeError) {
      const hint = import.meta.env.DEV
        ? " Start the API on port 8000 (uvicorn) or set VITE_API_BASE_URL."
        : " Set VITE_API_BASE_URL for this build and ensure the API is reachable.";
      throw new Error(`Could not reach the API.${hint}`);
    }
    throw e;
  }
}

export async function fetchAllUsers(): Promise<UserPublic[]> {
  const res = await apiFetch(`${API_BASE}/users/users`);
  const data = await parseBody(res);
  if (!res.ok) {
    throw new Error(extractDetail(data) ?? res.statusText);
  }
  return data as UserPublic[];
}

export async function appendUserEmail(
  name: string,
  address: string,
  alias: string,
): Promise<UserPublic> {
  const res = await apiFetch(`${API_BASE}/users/users/emails`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, address, alias }),
  });
  const data = await parseBody(res);
  if (!res.ok) {
    throw new Error(extractDetail(data) ?? res.statusText);
  }
  return data as UserPublic;
}

export async function deleteUserEmail(
  name: string,
  address: string,
): Promise<UserPublic> {
  const res = await apiFetch(`${API_BASE}/users/users/emails`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, address }),
  });
  const data = await parseBody(res);
  if (!res.ok) {
    throw new Error(extractDetail(data) ?? res.statusText);
  }
  return data as UserPublic;
}

export async function editUserEmail(
  name: string,
  old_address: string,
  new_address: string,
  new_alias: string,
): Promise<UserPublic> {
  const res = await apiFetch(`${API_BASE}/users/users/emails`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, old_address, new_address, new_alias }),
  });
  const data = await parseBody(res);
  if (!res.ok) {
    throw new Error(extractDetail(data) ?? res.statusText);
  }
  return data as UserPublic;
}

export type WorkflowStatus = "draft" | "active" | "paused" | "archived";

export type WorkflowDefinition = {
  workflow_id: string;
  owner_name: string;
  name: string;
  description: string;
  enabled: boolean;
  status: WorkflowStatus;
  trigger: { type: string; [key: string]: unknown };
  steps: {
    action_type: string;
    name: string;
    step_order: number;
    [key: string]: unknown;
  }[];
  created_at: string;
  updated_at: string;
};

export type CreateWorkflowPayload = {
  owner_name: string;
  name: string;
  description?: string;
  enabled: boolean;
  trigger: { type: string; parameters: Record<string, unknown> };
  steps: {
    action_type: string;
    name: string;
    step_order: number;
    parameters: Record<string, unknown>;
  }[];
};

export async function createWorkflow(
  payload: CreateWorkflowPayload,
): Promise<WorkflowDefinition> {
  const res = await apiFetch(`${API_BASE}/workflows`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await parseBody(res);
  if (!res.ok) throw new Error(extractDetail(data) ?? res.statusText);
  return data as WorkflowDefinition;
}

export async function fetchWorkflows(): Promise<WorkflowDefinition[]> {
  const res = await apiFetch(`${API_BASE}/workflows`);
  const data = await parseBody(res);
  if (!res.ok) throw new Error(extractDetail(data) ?? res.statusText);
  return data as WorkflowDefinition[];
}

export async function fetchWorkflow(
  workflowId: string,
): Promise<WorkflowDefinition> {
  const res = await apiFetch(`${API_BASE}/workflows/${workflowId}`);
  const data = await parseBody(res);
  if (!res.ok) throw new Error(extractDetail(data) ?? res.statusText);
  return data as WorkflowDefinition;
}

export type UpdateWorkflowPayload = {
  name?: string;
  description?: string;
  enabled?: boolean;
  trigger?: { type: string; parameters: Record<string, unknown> };
  steps?: {
    action_type: string;
    name: string;
    step_order: number;
    parameters: Record<string, unknown>;
  }[];
};

export async function updateWorkflow(
  workflowId: string,
  payload: UpdateWorkflowPayload,
): Promise<WorkflowDefinition> {
  const res = await apiFetch(`${API_BASE}/workflows/${workflowId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await parseBody(res);
  if (!res.ok) throw new Error(extractDetail(data) ?? res.statusText);
  return data as WorkflowDefinition;
}

export async function deleteWorkflow(workflowId: string): Promise<void> {
  const res = await apiFetch(`${API_BASE}/workflows/${workflowId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const data = await parseBody(res);
    throw new Error(extractDetail(data) ?? res.statusText);
  }
}

export async function registerUser(body: {
  name: string;
  password: string;
  email?: string | null;
}): Promise<AuthResponse> {
  const res = await apiFetch(`${API_BASE}/users/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await parseBody(res);
  if (!res.ok) {
    throw new Error(extractDetail(data) ?? res.statusText);
  }
  return data as AuthResponse;
}

export async function loginUser(
  name: string,
  password: string,
): Promise<{ auth: AuthResponse; token?: string }> {
  const res = await apiFetch(`${API_BASE}/users/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, password }),
  });
  const data = await parseBody(res);
  if (!res.ok) {
    throw new Error(extractDetail(data) ?? res.statusText);
  }
  if (Array.isArray(data) && data.length >= 1) {
    return {
      auth: data[0] as AuthResponse,
      token: typeof data[1] === "string" ? data[1] : undefined,
    };
  }
  return { auth: data as AuthResponse };
}

// Reports

export type ReportStatus = "pending" | "generating" | "completed" | "failed";

export type AggregatedMetrics = {
  total_runs: number;
  success_count: number;
  failure_count: number;
  success_rate: number;
  avg_duration_seconds: number;
  runs_per_workflow: Record<string, number>;
  top_error_messages: string[];
};

export type MonthlyReport = {
  report_id: string;
  owner_name: string;
  period_start: string;
  period_end: string;
  status: ReportStatus;
  metrics: AggregatedMetrics;
  ai_summary: string;
  created_at: string;
  updated_at: string;
};

export async function fetchReportsForOwner(
  ownerName: string,
): Promise<MonthlyReport[]> {
  const res = await apiFetch(
    `${API_BASE}/reports?owner_name=${encodeURIComponent(ownerName)}`,
  );
  const data = await parseBody(res);
  if (!res.ok) throw new Error(extractDetail(data) ?? res.statusText);
  return data as MonthlyReport[];
}

export async function fetchReport(reportId: string): Promise<MonthlyReport> {
  const res = await apiFetch(`${API_BASE}/reports/${reportId}`);
  const data = await parseBody(res);
  if (!res.ok) throw new Error(extractDetail(data) ?? res.statusText);
  return data as MonthlyReport;
}

export async function generateReport(payload: {
  owner_name: string;
  period_start: string;
  period_end: string;
}): Promise<MonthlyReport> {
  const res = await apiFetch(`${API_BASE}/reports/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await parseBody(res);
  if (!res.ok) throw new Error(extractDetail(data) ?? res.statusText);
  return data as MonthlyReport;
}
