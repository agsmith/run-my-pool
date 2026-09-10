import '@testing-library/jest-dom';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import PoolPickBreakdown from '../components/PoolPickBreakdown';
const rows = [{team:'SEA',team_name:'Seattle Seahawks',count:2,entries:[{entry_id:'a',entry_name:'Seattle One'},{entry_id:'b',entry_name:'Seattle Two'}]}];
afterEach(() => jest.restoreAllMocks());
test('shows team counts and named entries, changes weeks, and refreshes at focus', async () => {
  global.fetch = jest.fn().mockResolvedValue({ok:true,json:async()=>rows});
  render(<PoolPickBreakdown poolId="pool" currentWeek={1} />);
  expect(await screen.findByText('Seattle Seahawks')).toBeInTheDocument();
  expect(screen.getByText('2 entries')).toBeInTheDocument();
  fireEvent.click(screen.getByText('Seattle Seahawks'));
  expect(screen.getByText('Seattle One')).toBeInTheDocument();
  fetch.mockResolvedValue({ok:true,json:async()=>[]});
  fireEvent.change(screen.getByLabelText('Pick breakdown week'),{target:{value:'2'}});
  expect(await screen.findByText('No active entries have revealed picks yet.')).toBeInTheDocument();
  expect(fetch).toHaveBeenLastCalledWith(expect.stringContaining('/week/2/breakdown'),expect.any(Object));
  fetch.mockResolvedValue({ok:true,json:async()=>rows});
  fireEvent(window,new Event('focus'));
  expect(await screen.findByText('Seattle Seahawks')).toBeInTheDocument();
});
test('distinguishes failed requests from no revealed picks and supports retry', async () => {
  global.fetch = jest.fn().mockResolvedValue({ok:false});
  render(<PoolPickBreakdown poolId="pool" currentWeek={1} />);
  expect(await screen.findByRole('alert')).toHaveTextContent('Couldn’t load picks');
  fetch.mockResolvedValue({ok:true,json:async()=>rows});
  fireEvent.click(screen.getByRole('button',{name:'Refresh'}));
  await waitFor(()=>expect(screen.getByText('Seattle Seahawks')).toBeInTheDocument());
});
