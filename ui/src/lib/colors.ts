import type { Category } from './types';

export const CATEGORY_COLORS: Record<Category, string> = {
  BPharm: '#9C27B0',
  DPharm: '#4285F4',
  MPharm: '#34A853',
  PharmD: '#EA4335',
  QC: '#FBBC05',
  QP: '#757575'
};

export const CATEGORY_BG: Record<Category, string> = {
  BPharm: '#f3e5f5',
  DPharm: '#e3f2fd',
  MPharm: '#e8f5e9',
  PharmD: '#ffebee',
  QC: '#fffde7',
  QP: '#f5f5f5'
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
