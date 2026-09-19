import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import App from './App'
import * as api from './api'

vi.mock('@auth0/auth0-react', () => ({
  useAuth0: () => ({
    isAuthenticated: true,
    isLoading: false,
    user: { email: 'agent@triage-app.dev' },
    loginWithRedirect: vi.fn(),
    logout: vi.fn(),
    getAccessTokenSilently: vi.fn().mockResolvedValue('fake-token'),
  }),
}))

describe('Dashboard', () => {
  it('submits a ticket and shows the real routing result, including a handoff', async () => {
    vi.spyOn(api, 'submitTicket').mockResolvedValue({
      ticket_id: 'TCK-1',
      handled_by: 'billing',
      answer: 'Found the duplicate charge, refund issued.',
      handoffs: [
        {
          from_category: 'technical',
          to_category: 'billing',
          reason: 'billing charge dispute, not technical',
        },
      ],
    })

    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByLabelText(/customer id/i), 'cust-88')
    await user.selectOptions(screen.getByLabelText(/category/i), 'technical')
    await user.type(screen.getByLabelText(/subject/i), 'Two charges for one subscription')
    await user.type(screen.getByLabelText(/^body$/i), 'I was charged twice this month.')
    await user.click(screen.getByRole('button', { name: /submit ticket/i }))

    expect(await screen.findByText(/refund issued/i)).toBeInTheDocument()
    expect(screen.getByText(/billing charge dispute, not technical/i)).toBeInTheDocument()
    expect(api.submitTicket).toHaveBeenCalledWith(
      'fake-token',
      expect.objectContaining({ customer_id: 'cust-88', category: 'technical' }),
    )
  })

  it('looks up an existing ticket by id and shows its stored resolution', async () => {
    vi.spyOn(api, 'lookUpTicket').mockResolvedValue({
      ticket_id: 'TCK-2',
      handled_by: 'security',
      answer: 'Escalated to on-call.',
      handoffs: [],
    })

    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByLabelText(/look up a ticket/i), 'TCK-2')
    await user.click(screen.getByRole('button', { name: /^look up$/i }))

    await waitFor(() => expect(screen.getByText(/escalated to on-call/i)).toBeInTheDocument())
    expect(api.lookUpTicket).toHaveBeenCalledWith('fake-token', 'TCK-2')
  })

  it('shows a plain empty message when a looked-up ticket does not exist', async () => {
    vi.spyOn(api, 'lookUpTicket').mockResolvedValue(null)

    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByLabelText(/look up a ticket/i), 'no-such-ticket')
    await user.click(screen.getByRole('button', { name: /^look up$/i }))

    expect(await screen.findByText(/no ticket found/i)).toBeInTheDocument()
  })
})
