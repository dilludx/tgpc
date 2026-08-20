/**
 * Internal TGPC endpoint reference, for the admin console.
 *
 * Server-only: this list is a reconnaissance map of a government system's
 * internal endpoints and two of the URLs carry live credentials, so it must
 * never reach the browser bundle. It is served only to an authenticated
 * session, via `routes/admin/+page.server.ts`.
 *
 * SECURITY — the `viewpharmacist` and `getemailverify` URLs below embed live
 * TGPC reference IDs and verification tokens. They were previously public (see
 * CODE_REVIEW.md, finding C1), so they should be treated as compromised and
 * rotated. Once rotated, set ADMIN_LINK_PHARMACIST_URL and
 * ADMIN_LINK_EMAIL_VERIFY_URL as Cloudflare Pages environment variables and
 * delete the inline fallbacks, so no token lives in version control.
 */

import type { LinkGroup } from '$lib/types';

const base = 'https://www.pharmacycouncil.telangana.gov.in';

export function adminLinkGroups(platform: App.Platform | undefined): LinkGroup[] {
  const env = platform?.env;

  const pharmacistUrl =
    env?.['ADMIN_LINK_PHARMACIST_URL'] ||
    `${base}/pharmacy/viewpharmacist?referenceid=5428UN062011&random_no1=MMD6XSDJ8LL9`;

  const emailVerifyUrl =
    env?.['ADMIN_LINK_EMAIL_VERIFY_URL'] ||
    `${base}/pharmacy/getemailverify?rid1=661JCM272512&rid2=ACPYI0K3KLQJ&rid3=f7b3fdc6-e2f0-4983-a281-d89a26569e02`;

  return [
    {
      name: 'Search & Profile',
      items: [
        { heading: 'Pharmacist Detail View', url: pharmacistUrl, desc: 'View individual pharmacist profile with full details' },
        { heading: 'Pharmacist Search (POST)', url: `${base}/pharmacy/getsearchpharmacist`, desc: 'Search endpoint — POST registration_no to get results' },
        { heading: 'Admin Dashboard', url: `${base}/pharmacy/dashboard`, desc: 'TGPC admin dashboard' },
      ],
    },
    {
      name: 'Document Management',
      items: [
        { heading: 'Upload Rejected Docs', url: `${base}/pharmacy/editupload_rejected_docs`, desc: 'Form to upload documents that were rejected' },
        { heading: 'Rejected Docs API (POST)', url: `${base}/pharmacy/getrejecteddocsupload`, desc: 'API endpoint for rejected document uploads' },
        { heading: 'BillDesk TID Excel Upload', url: `${base}/site/billdesk_tid_excelreport_upload`, desc: 'Upload BillDesk TID Excel reports' },
      ],
    },
    {
      name: 'Workflow & Tracking',
      items: [
        { heading: 'Workflow Status', url: `${base}/pharmacy/workflowstatus`, desc: 'Detailed workflow tracking for applications' },
        { heading: 'Workflow Info API (POST)', url: `${base}/pharmacy/workflowstatusinfo.action`, desc: 'API endpoint for workflow status information' },
      ],
    },
    {
      name: 'Payments & Verification',
      items: [
        { heading: 'Payment Status Check', url: `${base}/pharmacy/getpmentstatusmeseva`, desc: 'Check payment status via Meseva' },
        { heading: 'Email Verify', url: emailVerifyUrl, desc: 'Verify pharmacist email with verification tokens' },
      ],
    },
    {
      name: 'Reports & Admin',
      items: [
        { heading: 'Dispatch List Report', url: `${base}/pharmacy/dispatchlistreprt`, desc: 'View dispatch list report' },
        { heading: 'Admin Console', url: `${base}/aconsole/adminconsole`, desc: 'TGPC admin console panel' },
      ],
    },
  ];
}
