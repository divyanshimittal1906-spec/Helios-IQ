import './globals.css';
import type { Metadata } from 'next';
import { AppShell } from '@/components/layout/app-shell';

export const metadata: Metadata = {
  title: 'Helios IQ',
  description: 'AI Workforce Operating System for businesses.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
