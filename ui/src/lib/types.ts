export interface PharmacistRecord {
  registration_number: string;
  name: string;
  father_name: string | null;
  category: Category;
  serial_number?: number;
  gender?: string | null;
  validity_date?: string | null;
  status?: string | null;
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
