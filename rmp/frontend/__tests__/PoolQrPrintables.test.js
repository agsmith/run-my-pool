import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PoolQrPrintables from '../components/PoolQrPrintables';
import { createPoolPrintable, loadPrintableLogo } from '../utils/poolQrPrintables';

process.env.NEXT_PUBLIC_API_URL = '';

jest.mock('../utils/poolQrPrintables', () => ({
  PRINT_FORMATS: {
    letter: { label: '8.5 x 11 flyer', description: 'Full page' },
    businessCard: { label: 'Business card (3.5 x 2)', description: 'Pocket size' },
    tableTent: { label: 'Restaurant table tent (5 x 7)', description: 'Two sided' },
  },
  createPoolPrintable: jest.fn(),
  loadPrintableLogo: jest.fn(),
}));

const pool = { id: 'pool-1', name: 'Office Survivor', is_private: true };

describe('PoolQrPrintables', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ available: true, password: 'huddle42' }),
    });
    window.history.replaceState({}, '', '/admin/league/pool-1');
    createPoolPrintable.mockResolvedValue({
      doc: { save: jest.fn(), output: jest.fn(() => new Blob(['pdf'])) },
      filename: 'office-survivor-qr-letter.pdf',
    });
  });

  test('shows the pool invite destination, current join code, and all print sizes', async () => {
    render(<PoolQrPrintables pool={pool} />);

    expect(screen.getByText('http://localhost/join/pool-1')).toBeInTheDocument();
    expect(screen.getByText(/not embedded in the QR itself/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText(/join code on printable/i)).toHaveValue('huddle42'));
    expect(fetch).toHaveBeenCalledWith('/pools/pool-1/join-password', expect.objectContaining({
      headers: { Authorization: 'Bearer null' },
      cache: 'no-store',
    }));
    expect(screen.getByRole('radio', { name: /8.5 x 11 flyer/i })).toBeChecked();
    expect(screen.getByRole('radio', { name: /business card/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /restaurant table tent/i })).toBeInTheDocument();
  });

  test('downloads the selected PDF using a browser-local uploaded logo', async () => {
    const user = userEvent.setup();
    const logo = { dataUrl: 'data:image/png;base64,logo', width: 400, height: 200, name: 'league.png' };
    loadPrintableLogo.mockResolvedValue(logo);
    render(<PoolQrPrintables pool={pool} />);

    const file = new File(['logo'], 'league.png', { type: 'image/png' });
    await user.upload(screen.getByLabelText(/add a logo/i), file);
    expect(await screen.findByAltText('Uploaded printable logo preview')).toBeInTheDocument();
    await user.click(screen.getByRole('radio', { name: /business card/i }));
    await user.click(screen.getByRole('button', { name: 'Download PDF' }));

    await waitFor(() => expect(createPoolPrintable).toHaveBeenCalledWith(expect.objectContaining({
      format: 'businessCard',
      poolName: 'Office Survivor',
      poolId: 'pool-1',
      isPrivate: true,
      joinCode: 'huddle42',
      logo,
      origin: 'http://localhost',
    })));
    const result = await createPoolPrintable.mock.results[0].value;
    expect(result.doc.save).toHaveBeenCalledWith('office-survivor-qr-letter.pdf');
  });

  test('rejects an unsupported logo without attempting PDF generation', async () => {
    loadPrintableLogo.mockRejectedValue(new Error('Upload a PNG, JPG, or WebP logo.'));
    render(<PoolQrPrintables pool={pool} />);

    fireEvent.change(screen.getByLabelText(/add a logo/i), {
      target: { files: [new File(['bad'], 'logo.svg', { type: 'image/svg+xml' })] },
    });

    expect(await screen.findByRole('status')).toHaveTextContent('Upload a PNG, JPG, or WebP logo.');
    expect(createPoolPrintable).not.toHaveBeenCalled();
  });

  test('opens the generated PDF for printing', async () => {
    const user = userEvent.setup();
    const replace = jest.fn();
    const printWindow = { document: { write: jest.fn() }, location: { replace }, close: jest.fn() };
    jest.spyOn(window, 'open').mockReturnValue(printWindow);
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: jest.fn(() => 'blob:printable') });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: jest.fn() });
    render(<PoolQrPrintables pool={pool} />);

    await user.click(screen.getByRole('button', { name: 'Open to print' }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith('blob:printable'));
    expect(screen.getByRole('status')).toHaveTextContent(/print at 100% or Actual Size/i);
  });
});
