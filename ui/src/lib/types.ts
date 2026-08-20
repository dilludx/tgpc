export interface PharmacistRecord {
  registration_number: string;
  name: string;
  father_name: string | null;
  category: Category;
  serial_number?: number;
  gender?: string | null;
  validity_date?: string | null;
  status?: string | null;
  photo_url?: string | null;
  score?: number;
}

export type Category = 'BPharm' | 'DPharm' | 'MPharm' | 'PharmD' | 'QC' | 'QP';

export interface Notice {
  date: string;
  title: string;
  links: NoticeLink[];
}

export interface NoticeLink {
  url: string;
  label: string;
}

export interface DispatchFile {
  name: string;
  size?: number;
  parsed?: {
    d: string;
    mo: string;
    y: string;
    date: Date;
  } | null;
}

export interface Stats {
  total: number;
  active: number;
  inactive: number;
  BPharm: number;
  DPharm: number;
  MPharm: number;
  PharmD: number;
  QC: number;
  QP: number;
}

export type ConnectionStatus = 'Live' | 'Busy' | 'Offline';

export interface BadgeColor {
  bg: string;
  text: string;
}

export type CategoryFilter = 'all' | Category;

export interface ServiceUsageItem {
  label: string;
  used: string | null;
  limit: string | null;
  pct: string;
}

export interface ServiceUsage {
  name: string;
  items: ServiceUsageItem[];
  error?: string;
}

export interface UsageReport {
  generated_at: string;
  services: ServiceUsage[];
  missing_vars: string[];
}
