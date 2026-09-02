import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PoolLaunchChecklist from '../components/PoolLaunchChecklist';

describe('PoolLaunchChecklist', () => {
  test('copies a secure private-pool invitation and routes each setup action', async () => {
    const user = userEvent.setup();
    const onNavigate = jest.fn();
    const onInviteCopied = jest.fn();
    const onSendInvite = jest.fn().mockResolvedValue(undefined);
    const writeText = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });

    render(<PoolLaunchChecklist
      pool={{ id: 'pool-1', name: 'Office Pool', is_private: true, pool_type: 'survivor' }}
      onClose={jest.fn()}
      onNavigate={onNavigate}
      onInviteCopied={onInviteCopied}
      onSendInvite={onSendInvite}
    />);

    expect(screen.getByText(/1 of 4 launch steps complete/i)).toBeInTheDocument();
    expect(screen.getByText(/both this link and your pool join code/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /copy invite link/i }));
    expect(writeText).toHaveBeenCalledWith('http://localhost/join/pool-1');
    expect(await screen.findByText(/send the pool join code separately/i)).toBeInTheDocument();
    expect(onInviteCopied).toHaveBeenCalledTimes(1);

    await user.type(screen.getByLabelText(/or send by email/i), 'player@example.com');
    await user.click(screen.getByRole('button', { name: /send invite/i }));
    expect(onSendInvite).toHaveBeenCalledWith('player@example.com');
    expect(await screen.findByText(/invitation sent.*join code separately/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /review settings/i }));
    expect(onNavigate).toHaveBeenCalledWith('/admin/league/pool-1');
    await user.click(screen.getByRole('button', { name: /open my entries/i }));
    expect(onNavigate).toHaveBeenCalledWith('/pool/pool-1/entries');
  });

  test('uses the Pick Em board as the first-use destination', async () => {
    const user = userEvent.setup();
    const onNavigate = jest.fn();
    render(<PoolLaunchChecklist
      pool={{ id: 'pickem-1', name: 'Pick Em', is_private: false, pool_type: 'pickem' }}
      onClose={jest.fn()}
      onNavigate={onNavigate}
      onSendInvite={jest.fn()}
    />);

    await user.click(screen.getByRole('button', { name: /open Pick ’Em board/i }));
    expect(onNavigate).toHaveBeenCalledWith('/pool/pickem-1/pickem');
  });

  test('explains the owner-managed free Squares workflow instead of showing invitations', async () => {
    const user = userEvent.setup();
    const onNavigate = jest.fn();
    render(<PoolLaunchChecklist
      pool={{ id: 'squares-1', name: 'Squares', is_private: false, pool_type: 'squares', plan: 'free' }}
      onClose={jest.fn()}
      onNavigate={onNavigate}
      onSendInvite={jest.fn()}
    />);

    expect(screen.getByText(/free board is private to you/i)).toBeInTheDocument();
    expect(screen.getByText(/players cannot join online/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /copy invite/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /send invite/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Enter received selections' }));
    expect(onNavigate).toHaveBeenCalledWith('/pool/squares-1/squares');
  });
});
