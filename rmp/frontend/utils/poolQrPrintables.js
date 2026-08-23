export const PRINT_FORMATS = {
  letter: {
    label: '8.5 x 11 flyer',
    description: 'Full-page flyer for bulletin boards, check-in tables, and common areas.',
  },
  businessCard: {
    label: 'Business card (3.5 x 2)',
    description: 'Pocket-size card. Print at 100% or Actual Size.',
  },
  tableTent: {
    label: 'Restaurant table tent (5 x 7)',
    description: 'Two-sided 5 x 7 tent with a center fold line.',
  },
};

const NAVY = [4, 18, 24];
const CYAN = [74, 218, 245];
const LIME = [198, 255, 55];
const WHITE = [247, 251, 250];
const MUTED = [112, 133, 138];

const safeFilePart = (value) => (
  String(value || 'pool')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '') || 'pool'
);

const setFill = (doc, color) => doc.setFillColor(...color);
const setText = (doc, color) => doc.setTextColor(...color);

function addImageContained(doc, logo, x, y, maxWidth, maxHeight) {
  if (!logo?.dataUrl || !logo.width || !logo.height) return;
  const scale = Math.min(maxWidth / logo.width, maxHeight / logo.height);
  const width = logo.width * scale;
  const height = logo.height * scale;
  doc.addImage(logo.dataUrl, 'PNG', x + (maxWidth - width) / 2, y + (maxHeight - height) / 2, width, height);
}

function drawQr(doc, qrDataUrl, x, y, size) {
  setFill(doc, WHITE);
  doc.roundedRect(x - 8, y - 8, size + 16, size + 16, 8, 8, 'F');
  doc.addImage(qrDataUrl, 'PNG', x, y, size, size);
}

function addCenteredText(doc, text, x, y, maxWidth, options = {}) {
  const lines = doc.splitTextToSize(text, maxWidth);
  doc.text(lines, x, y, { align: 'center', ...options });
  return lines;
}

function drawLetter(doc, details) {
  const { poolName, inviteUrl, qrDataUrl, logo, isPrivate, joinCode } = details;
  setFill(doc, NAVY);
  doc.rect(0, 0, 612, 792, 'F');
  setFill(doc, CYAN);
  doc.rect(0, 0, 612, 13, 'F');
  setFill(doc, LIME);
  doc.rect(0, 779, 612, 13, 'F');

  addImageContained(doc, logo, 206, 42, 200, 88);
  setText(doc, logo ? CYAN : LIME);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(logo ? 16 : 24);
  doc.text(logo ? 'RUN MY POOL' : 'RUN MY POOL', 306, logo ? 155 : 76, { align: 'center' });

  setText(doc, WHITE);
  doc.setFontSize(36);
  addCenteredText(doc, poolName, 306, logo ? 205 : 136, 500);
  setText(doc, CYAN);
  doc.setFontSize(20);
  doc.text('SCAN TO JOIN', 306, logo ? 274 : 216, { align: 'center' });

  drawQr(doc, qrDataUrl, 176, logo ? 307 : 252, 260);

  setText(doc, WHITE);
  doc.setFontSize(15);
  doc.text('Open your camera and point it at the QR code.', 306, logo ? 622 : 570, { align: 'center' });
  doc.setFontSize(11);
  setText(doc, MUTED);
  addCenteredText(doc, inviteUrl, 306, logo ? 652 : 600, 510);
  if (isPrivate) {
    setText(doc, LIME);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(13);
    addCenteredText(doc, `JOIN CODE: ${joinCode || '________________'}`, 306, logo ? 698 : 646, 500);
  }
  setText(doc, WHITE);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(10);
  doc.text('Create your free account, join the pool, and make your picks.', 306, 746, { align: 'center' });
}

function drawBusinessCard(doc, details) {
  const { poolName, qrDataUrl, logo, isPrivate, joinCode } = details;
  setFill(doc, NAVY);
  doc.rect(0, 0, 252, 144, 'F');
  setFill(doc, CYAN);
  doc.rect(0, 0, 6, 144, 'F');
  setFill(doc, LIME);
  doc.rect(246, 0, 6, 144, 'F');

  addImageContained(doc, logo, 17, 12, 108, 28);
  setText(doc, logo ? CYAN : LIME);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.text('RUN MY POOL', 17, logo ? 50 : 20);
  setText(doc, WHITE);
  doc.setFontSize(14);
  const titleLines = doc.splitTextToSize(poolName, 112).slice(0, 3);
  doc.text(titleLines, 17, logo ? 68 : 42);
  setText(doc, CYAN);
  doc.setFontSize(9);
  doc.text('SCAN TO JOIN', 17, 116);
  if (isPrivate) {
    setText(doc, LIME);
    doc.setFontSize(6.5);
    doc.text(doc.splitTextToSize(`CODE: ${joinCode || '____________'}`, 112).slice(0, 2), 17, 128);
  }
  drawQr(doc, qrDataUrl, 145, 16, 82);
  setText(doc, MUTED);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(5.5);
  doc.text('runmypool.net', 186, 120, { align: 'center' });
}

function drawTentPanel(doc, details, x) {
  const { poolName, inviteUrl, qrDataUrl, logo, isPrivate, joinCode } = details;
  const centerX = x + 180;
  setFill(doc, NAVY);
  doc.rect(x, 0, 360, 504, 'F');
  setFill(doc, CYAN);
  doc.rect(x, 0, 360, 10, 'F');
  setFill(doc, LIME);
  doc.rect(x, 494, 360, 10, 'F');
  addImageContained(doc, logo, x + 90, 35, 180, 65);
  setText(doc, logo ? CYAN : LIME);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(15);
  doc.text('RUN MY POOL', centerX, logo ? 125 : 55, { align: 'center' });
  setText(doc, WHITE);
  doc.setFontSize(25);
  doc.text(doc.splitTextToSize(poolName, 300).slice(0, 3), centerX, logo ? 165 : 100, { align: 'center' });
  setText(doc, CYAN);
  doc.setFontSize(15);
  doc.text('SCAN TO JOIN', centerX, logo ? 236 : 178, { align: 'center' });
  const qrSize = logo ? 160 : 180;
  drawQr(doc, qrDataUrl, x + (360 - qrSize) / 2, logo ? 250 : 202, qrSize);
  setText(doc, MUTED);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  doc.text(doc.splitTextToSize(inviteUrl, 300), centerX, logo ? 462 : 435, { align: 'center' });
  if (isPrivate) {
    setText(doc, LIME);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8);
    doc.text(doc.splitTextToSize(`JOIN CODE: ${joinCode || '________________'}`, 300), centerX, logo ? 438 : 410, { align: 'center' });
  }
}

function drawTableTent(doc, details) {
  drawTentPanel(doc, details, 0);
  drawTentPanel(doc, details, 360);
  doc.setDrawColor(255, 255, 255);
  doc.setLineDashPattern([5, 4], 0);
  doc.line(360, 0, 360, 504);
  doc.setLineDashPattern([], 0);
}

export async function createPoolPrintable({ format, poolName, poolId, isPrivate, joinCode, logo, origin }) {
  if (!PRINT_FORMATS[format]) throw new Error('Choose a supported print size.');
  const inviteUrl = `${origin.replace(/\/$/, '')}/leagues?invite=${encodeURIComponent(poolId)}`;
  const [pdfModule, qrModule] = await Promise.all([import('jspdf'), import('qrcode')]);
  const { jsPDF } = pdfModule;
  const QRCode = qrModule.default || qrModule;
  const qrDataUrl = await QRCode.toDataURL(inviteUrl, {
    errorCorrectionLevel: 'H',
    margin: 2,
    width: 1024,
    color: { dark: '#041218', light: '#f7fbfa' },
  });

  const options = format === 'letter'
    ? { orientation: 'portrait', unit: 'pt', format: 'letter' }
    : format === 'businessCard'
      ? { orientation: 'landscape', unit: 'pt', format: [252, 144] }
      : { orientation: 'landscape', unit: 'pt', format: [720, 504] };
  const doc = new jsPDF(options);
  const details = { poolName, poolId, isPrivate, joinCode, logo, inviteUrl, qrDataUrl };

  if (format === 'letter') drawLetter(doc, details);
  if (format === 'businessCard') drawBusinessCard(doc, details);
  if (format === 'tableTent') drawTableTent(doc, details);

  doc.setProperties({
    title: `${poolName} QR join printable`,
    subject: `Join ${poolName} on Run My Pool`,
    author: 'Run My Pool',
    creator: 'Run My Pool Commissioner Portal',
  });
  return {
    doc,
    filename: `${safeFilePart(poolName)}-qr-${format === 'businessCard' ? 'business-card' : format === 'tableTent' ? 'table-tent' : 'letter'}.pdf`,
    inviteUrl,
  };
}

export async function loadPrintableLogo(file) {
  if (!file) return null;
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
    throw new Error('Upload a PNG, JPG, or WebP logo.');
  }
  if (file.size > 5 * 1024 * 1024) throw new Error('Logo must be 5 MB or smaller.');

  const source = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('Unable to read that logo.'));
    reader.readAsDataURL(file);
  });
  const image = await new Promise((resolve, reject) => {
    const element = new Image();
    element.onload = () => resolve(element);
    element.onerror = () => reject(new Error('Unable to decode that logo.'));
    element.src = source;
  });
  const scale = Math.min(1, 800 / Math.max(image.naturalWidth, image.naturalHeight));
  const width = Math.max(1, Math.round(image.naturalWidth * scale));
  const height = Math.max(1, Math.round(image.naturalHeight * scale));
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  canvas.getContext('2d').drawImage(image, 0, 0, width, height);
  return { dataUrl: canvas.toDataURL('image/png'), width, height, name: file.name };
}
