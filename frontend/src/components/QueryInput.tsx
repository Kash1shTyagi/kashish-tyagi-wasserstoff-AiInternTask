import React, { useState } from 'react';
import type { FormEvent } from 'react';
import { Button } from './ui/button';
import { Textarea } from '@/components/ui/textarea';
import api from '../utils/api';

interface QueryInputProps {
  onResponse: (data: any) => void;
  loading: boolean;
  setLoading: (val: boolean) => void;
}

export default function QueryInput({ onResponse, loading, setLoading }: QueryInputProps) {
  const [question, setQuestion] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;

    setLoading(true);
    try {
      const res = await api.post('/query', {
        question: trimmed,
        top_k_per_doc: 2,
      });
      onResponse(res.data);
    } catch (err) {
      console.error('[handleSubmit] Query failed:', err);
      onResponse({ error: 'Failed to process query.' });
    } finally {
      setLoading(false);
    }

    setQuestion('');
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <label htmlFor="question" className="block font-medium">
        Ask a question
      </label>
      <Textarea
        id="question"
        placeholder="Enter your question here..."
        value={question}
        onChange={e => setQuestion(e.target.value)}
        className="h-24"
      />
      <Button type="submit" disabled={loading || !question.trim()}>
        {loading ? 'Processing...' : 'Submit'}
      </Button>
    </form>
  );
}
