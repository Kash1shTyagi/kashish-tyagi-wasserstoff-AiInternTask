import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export interface ThemeItem {
  theme_name: string;
  summary: string;
  citations: string[];
}

interface ThemeSummaryProps {
  themes: ThemeItem[];
}

export default function ThemeSummary({ themes }: ThemeSummaryProps) {
  return (
    <div className="space-y-4">
      {themes.map((t, idx) => (
        <Card key={idx} className="bg-white">
          <CardHeader>
            <CardTitle>{t.theme_name}</CardTitle>
          </CardHeader>
          <CardContent>
            <p>{t.summary}</p>
            <p className="mt-2 text-xs text-gray-500">
              Citations: {t.citations.join(', ')}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
