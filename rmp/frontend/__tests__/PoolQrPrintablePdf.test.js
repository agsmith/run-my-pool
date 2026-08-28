/** @jest-environment node */

import fs from 'fs';
import path from 'path';
import { createPoolPrintable } from '../utils/poolQrPrintables';

// jsPDF and QR generation are CPU-intensive under GitHub's shared runners.
// Keep the assertion coverage while allowing enough time for slower CI hosts.
jest.setTimeout(30000);

describe('pool QR PDF generation', () => {
  test.each([
    ['letter', 612, 792],
    ['businessCard', 252, 144],
    ['tableTent', 720, 504],
  ])('creates a valid %s PDF at its intended physical size', async (format, width, height) => {
    const logoPath = path.resolve('public/brand/run-my-pool-wordmark.png');
    const logo = process.env.WRITE_QR_SAMPLES === '1' && format === 'letter'
      ? { dataUrl: `data:image/png;base64,${fs.readFileSync(logoPath).toString('base64')}`, width: 720, height: 180 }
      : null;
    const { doc, filename, inviteUrl } = await createPoolPrintable({
      format,
      poolName: 'Office Survivor',
      poolId: 'pool-1',
      isPrivate: true,
      joinCode: 'huddle42',
      logo,
      origin: 'https://runmypool.net',
    });

    expect(doc.internal.pageSize.getWidth()).toBeCloseTo(width, 1);
    expect(doc.internal.pageSize.getHeight()).toBeCloseTo(height, 1);
    const pdfOutput = doc.output();
    expect(new Uint8Array(doc.output('arraybuffer')).byteLength).toBeGreaterThan(5000);
    expect(filename).toMatch(/office-survivor-qr-.+\.pdf$/);
    expect(inviteUrl).toBe('https://runmypool.net/join/pool-1');
    expect(pdfOutput).toContain('huddle42');
    if (format === 'tableTent') {
      expect(pdfOutput.match(/\(RUN MY POOL\) Tj/g)).toHaveLength(2);
      expect(pdfOutput).not.toMatch(/-1\.?\s+0\.?\s+0\.?\s+-1\.?/);
    }
    if (process.env.WRITE_QR_SAMPLES === '1') {
      const outputDirectory = path.resolve('tmp/pdfs');
      fs.mkdirSync(outputDirectory, { recursive: true });
      fs.writeFileSync(path.join(outputDirectory, filename), Buffer.from(doc.output('arraybuffer')));
    }
  });
});
