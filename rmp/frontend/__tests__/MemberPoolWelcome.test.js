import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MemberPoolWelcome from '../components/MemberPoolWelcome';

describe('MemberPoolWelcome', () => {
  test('explains Survivor onboarding and opens first-entry creation', async () => {
    const user = userEvent.setup();
    const onCreateEntry = jest.fn();
    const onDismiss = jest.fn();
    render(<MemberPoolWelcome
      pool={{ name: 'Office Survivor', pool_type: 'survivor' }}
      onCreateEntry={onCreateEntry}
      onDismiss={onDismiss}
    />);

    expect(screen.getByText(/choose one eligible team each week/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /create your first entry/i }));
    expect(onCreateEntry).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole('button', { name: /explore pool first/i }));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  test('explains Pick Em scoring to a new member', () => {
    render(<MemberPoolWelcome
      pool={{ name: 'Office Pick Em', pool_type: 'pickem' }}
      onCreateEntry={jest.fn()}
      onDismiss={jest.fn()}
    />);

    expect(screen.getByText(/every correct pick earns one point/i)).toBeInTheDocument();
  });
});
