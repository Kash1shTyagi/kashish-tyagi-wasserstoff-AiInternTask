import React from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

export interface AnswerSnippet {
  text: string;
  citation: string;
}

export interface DocumentAnswer {
  doc_id: string;
  answers: AnswerSnippet[];
}

interface AnswerTableProps {
  data: DocumentAnswer[];
}

export default function AnswerTable({ data }: AnswerTableProps) {
  return (
    <div className="overflow-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-1/4">Doc ID</TableHead>
            <TableHead className="w-3/4">Answer & Citation</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map(doc => (
            <TableRow key={doc.doc_id}>
              <TableCell>{doc.doc_id}</TableCell>
              <TableCell>
                {doc.answers.map((a, idx) => (
                  <div key={idx} className="mb-2">
                    <p className="italic">"{a.text}"</p>
                    <p className="text-xs text-gray-500">{a.citation}</p>
                  </div>
                ))}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
