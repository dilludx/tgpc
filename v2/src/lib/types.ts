export interface PharmacistRecord {
  registration_number: string;
  name: string;
  father_name: string;
  category: string;
  serial_number?: number | null;
}

export interface Notice {
  id: number;
  date: string;
  source: string;
  title: string;
  links?: { label: string; url: string }[];
}
