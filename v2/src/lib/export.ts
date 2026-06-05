import type { PharmacistRecord } from './types';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function fileDateFormat(): string {
  const n = new Date();
  return String(n.getDate()).padStart(2, '0') + String(n.getMonth() + 1).padStart(2, '0') + n.getFullYear();
}

function formattedNow(): string {
  const n = new Date();
  return `${DAYS[n.getDay()]}, ${String(n.getDate()).padStart(2, '0')} ${MONTHS[n.getMonth()]} ${n.getFullYear()} ${String(n.getHours()).padStart(2, '0')}:${String(n.getMinutes()).padStart(2, '0')}`;
}

export async function generatePDF(records: PharmacistRecord[], keyword: string) {
  if (records.length === 0) return;
  const k = keyword.trim() || '(empty)';
  const title = `TGPC Rx Registry - Search Keyword: ${k} - ${formattedNow()}`;
  const tableData = records.map(r => [r.registration_number, r.name, r.father_name || 'N/A', r.category]);

  const { default: jsPDF } = await import('jspdf');
  await import('jspdf-autotable');

  const doc = new jsPDF({ format: 'a4', unit: 'mm' });
  (doc as any).autoTable({
    startY: 15,
    head: [['Registration Number', 'Name', "Father's Name", 'Category']],
    body: tableData,
    theme: 'striped',
    headStyles: { fillColor: [0, 204, 102], textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 9 },
    bodyStyles: { fontSize: 8, cellPadding: 2 },
    alternateRowStyles: { fillColor: [250, 250, 250] },
    margin: { top: 12, left: 10, right: 10, bottom: 12 },
    tableWidth: 'auto',
    didDrawPage: function (data: any) {
      doc.setFontSize(14);
      doc.setTextColor(0, 204, 102);
      doc.text(title, 10, 10);
      doc.setFontSize(8);
      doc.setTextColor(150, 150, 150);
      doc.text(`Page ${data.pageNumber} / ${data.pageCount}`, doc.internal.pageSize.width / 2, doc.internal.pageSize.height - 10, { align: 'center' });
    }
  });
  doc.save(`TGPC-RX-SEARCH-${k}-${fileDateFormat()}.pdf`);
}

export function generateCSV(records: PharmacistRecord[], keyword: string) {
  if (records.length === 0) return;
  const k = keyword.trim() || '(empty)';
  const meta = `# TGPC Rx Registry - Search Keyword: ${k} - ${formattedNow()}`;
  const headers = ['Registration Number', 'Name', 'Father Name', 'Category'];
  const rows = [meta, headers.join(',')];

  records.forEach(r => {
    rows.push(`"${r.registration_number || ''}","${(r.name || '').replace(/"/g, '""')}","${(r.father_name || '').replace(/"/g, '""')}","${r.category || ''}"`);
  });

  const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `TGPC-RX-SEARCH-${k}-${fileDateFormat()}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}
