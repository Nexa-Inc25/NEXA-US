import { appSchema, tableSchema } from '@nozbe/watermelondb';

export const mySchema = appSchema({
  version: 1,
  tables: [
    tableSchema({
      name: 'jobs',
      columns: [
        { name: 'title', type: 'string' },
        { name: 'status', type: 'string' },
        { name: 'updated_at', type: 'number' },
      ],
    }),
    tableSchema({
      name: 'photo_qas',
      columns: [
        { name: 'job_id', type: 'string', isIndexed: true },
        { name: 'photo_uri', type: 'string' },
        { name: 'analysis', type: 'string' }, // JSON string
        { name: 'created_at', type: 'number' },
        { name: 'synced', type: 'boolean', isOptional: true },
      ],
    }),
    tableSchema({
      name: 'closeouts',
      columns: [
        { name: 'job_id', type: 'string', isIndexed: true },
        { name: 'pdf_uri', type: 'string' },
        { name: 'generated_at', type: 'number' },
        { name: 'synced', type: 'boolean', isOptional: true },
      ],
    }),
  ],
});
