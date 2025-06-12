import React, { useState } from 'react';
import type { FormEvent } from 'react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';

interface ThemeInputProps {
  onSubmit: (text: string) => void;
  loading: boolean;
}

export default function ThemeInput({ onSubmit, loading }: ThemeInputProps) {
  const [themeText, setThemeText] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = themeText.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
    setThemeText('');
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <label htmlFor="themeText" className="block font-medium">
        Provide document text to identify themes
      </label>
      <Textarea
        id="themeText"
        placeholder="Paste or enter document text here..."
        value={themeText}
        onChange={e => setThemeText(e.target.value)}
        className="h-24"
      />
      <Button type="submit" disabled={loading || !themeText.trim()}>
        {loading ? 'Processing...' : 'Generate Themes'}
      </Button>
    </form>
  );
}
