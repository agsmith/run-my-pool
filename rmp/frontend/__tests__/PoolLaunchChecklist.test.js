import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PoolLaunchChecklist from '../components/PoolLaunchChecklist';

describe('PoolLaunchChecklist', () => {
  test('copies a secure private-pool invitation and routes each setup action', async () => {
    const user = userEvent.setup();
    const onNavigate = jest.fn();
    const onInviteCopied = jest.fn();
    const writeText = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });

    render(<PoolLaunchChecklist
      pool={{ id: 'pool-1', name: 'Office Pool', is_private: true, pool_type: 'survivor' }}
      onClose={jest.fn()}
      onNavigate={onNavigate}
      onInviteCopied={onInviteCopied}
    />);

    expect(screen.getByText(/1 of 4 launch steps complete/i)).toBeInTheDocument();
    expect(screen.getByText(/both this link and your pool join code/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /copy invite link/i }));
    expect(writeText).toHaveBeenCalledWith('http://localhost/leagues?invite=pool-1');
    expect(await screen.findByText(/send the pool join code separately/i)).toBeInTheDocument();
    expect(onInviteCopied).toHaveBeenCalledTimes(1);

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
    />);

    await user.click(screen.getByRole('button', { name: /open Pick ’Em board/i }));
    expect(onNavigate).toHaveBeenCalledWith('/pool/pickem-1/pickem');
  });
});
