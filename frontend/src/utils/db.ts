import Dexie from 'dexie';
import type { Table } from 'dexie';

export interface LocalDoc {
  doc_id: string;      
  filename: string;
  blob: Blob;
  upload_date: string;  
}

export class AppDB extends Dexie {
  docs!: Table<LocalDoc, string>;

  constructor() {
    super('MyDocumentDB');
    this.version(1).stores({
      docs: '&doc_id, filename, upload_date'
    });
  }
}

export const db = new AppDB();
