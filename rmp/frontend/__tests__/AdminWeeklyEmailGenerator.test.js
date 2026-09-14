import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import AdminWeeklyEmailGenerator from '../components/AdminWeeklyEmailGenerator';

describe('AdminWeeklyEmailGenerator', () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ text: 'Subject: Survivor update\nThe race continues.' }),
    });
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: jest.fn().mockResolvedValue(undefined) },
    });
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: { getItem: jest.fn().mockReturnValue('token') },
    });
  });

  it('uses Survivor language and returns a copyable draft', async () => {
    render(<AdminWeeklyEmailGenerator poolId="pool-1" poolType="survivor" />);
    expect(screen.getByText('Generate Survivor Email')).toBeInTheDocument();
    expect(screen.getByText(/surviving entries, eliminated entries/i)).toBeInTheDocument();
    expect(screen.getByText('Survivor rules and payout notes')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Generate email draft' }));
    await waitFor(() => expect(screen.getByDisplayValue(/Subject: Survivor update/)).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: 'Copy email' }));
    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledWith('Subject: Survivor update\nThe race continues.'));
  });
});
