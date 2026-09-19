const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

export type TicketCategory = 'billing' | 'technical' | 'security'

export interface HandoffRecord {
  from_category: TicketCategory
  to_category: TicketCategory
  reason: string
}

export interface ResolutionResponse {
  ticket_id: string
  handled_by: TicketCategory
  answer: string
  handoffs: HandoffRecord[]
}

export interface ProblemDetail {
  type: string
  title: string
  status: number
  detail: string
}

export class ApiError extends Error {
  problem: ProblemDetail

  constructor(problem: ProblemDetail) {
    super(problem.detail)
    this.problem = problem
  }
}

async function request<T>(
  path: string,
  token: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  })

  if (!response.ok) {
    throw new ApiError((await response.json()) as ProblemDetail)
  }
  return (await response.json()) as T
}

export interface TicketSubmission {
  ticket_id: string
  customer_id: string
  category: TicketCategory
  subject: string
  body: string
}

export function submitTicket(
  token: string,
  ticket: TicketSubmission,
): Promise<ResolutionResponse> {
  return request<ResolutionResponse>('/v1/tickets', token, {
    method: 'POST',
    body: JSON.stringify(ticket),
  })
}

export function lookUpTicket(
  token: string,
  ticketId: string,
): Promise<ResolutionResponse | null> {
  return request<ResolutionResponse | null>(`/v1/tickets/${ticketId}`, token)
}
