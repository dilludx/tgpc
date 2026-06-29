import type { Category } from './types';

export const CATEGORY_COLORS: Record<Category, string> = {
  BPharm: '#00cc66',
  DPharm: '#ea580c',
  MPharm: '#7c3aed',
  PharmD: '#f59e0b',
  QC: '#0891b2',
  QP: '#78716c'
};

export const CATEGORY_BG: Record<Category, string> = {
  BPharm: '#d9f7eb',
  DPharm: '#fff7ed',
  MPharm: '#ede9fe',
  PharmD: '#fef3c7',
  QC: '#cffafe',
  QP: '#f5f5f4'
};

export const CATEGORY_LABELS: Record<Category, string> = {
  BPharm: 'BPharm',
  DPharm: 'DPharm',
  MPharm: 'MPharm',
  PharmD: 'PharmD',
  QC: 'QC',
  QP: 'QP'
};

export const CATEGORIES: Category[] = ['BPharm', 'DPharm', 'MPharm', 'PharmD', 'QC', 'QP'];

export const CATEGORY_KEYS = ['BPharm', 'DPharm', 'MPharm', 'PharmD', 'QC', 'QP'] as const;
