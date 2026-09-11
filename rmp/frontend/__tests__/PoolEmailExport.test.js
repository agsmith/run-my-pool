import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import AdminUserOverview from '../components/AdminUserOverview';
import PoolEmailExport from '../components/PoolEmailExport';

const users = [{id:'1',email:'Owner@example.com'}, {id:'2',email:'member@example.com'}, {id:'3',email:' MEMBER@example.com '}, {id:'4',email:''}];
test('copies the complete deduplicated list even when the directory is filtered', async () => {
  const writeText = jest.fn().mockResolvedValue();
  Object.defineProperty(navigator, 'clipboard', {configurable:true,value:{writeText}});
  render(<AdminUserOverview overview={{users}} />);
  fireEvent.change(screen.getByLabelText('Search users'),{target:{value:'Owner'}});
  fireEvent.click(screen.getByText('Copy all emails'));
  await waitFor(()=>expect(writeText).toHaveBeenCalledWith('member@example.com, owner@example.com'));
  expect(await screen.findByText('Copied 2 email addresses.')).toBeVisible();
});
test('downloads a named text file containing every unique email', () => {
  URL.createObjectURL = jest.fn().mockReturnValue('blob:emails');
  URL.revokeObjectURL = jest.fn();
  const click = jest.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(function () {
    expect(this.download).toBe('Sweeney-2026-emails.txt');
    expect(this.href).toBe('blob:emails');
  });
  render(<PoolEmailExport users={users} poolName="Sweeney 2026" />);
  fireEvent.click(screen.getByText('Download email list (.txt)'));
  expect(click).toHaveBeenCalled();
  expect(URL.createObjectURL.mock.calls[0][0].type).toBe('text/plain;charset=utf-8');
  click.mockRestore();
});
test('offers selectable addresses when clipboard access fails', async () => {
  Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:jest.fn().mockRejectedValue(new Error('denied'))}});
  render(<PoolEmailExport users={users} />);
  fireEvent.click(screen.getByText('Copy all emails'));
  expect(await screen.findByText(/Copy was unavailable/)).toBeVisible();
  expect(screen.getByLabelText('All pool email addresses')).toHaveValue('member@example.com, owner@example.com');
});
test.each([{users:[]},{users,disabled:true}])('disables export for missing or unavailable data', (props) => {
  render(<PoolEmailExport {...props} />);
  expect(screen.getByText('Copy all emails')).toBeDisabled();
  expect(screen.getByText('Download email list (.txt)')).toBeDisabled();
});
