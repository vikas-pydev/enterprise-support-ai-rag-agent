import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Enterprise Support AI Agent',
  description: 'Grounded enterprise AI assistant powered by RAG, PostgreSQL, tool calling, and LangGraph',
  keywords: ['RAG', 'LangGraph', 'FastAPI', 'Next.js', 'Enterprise AI', 'PostgreSQL', 'Hybrid Search'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable} dark antialiased`} suppressHydrationWarning>
      <body className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans flex flex-col selection:bg-cyan-500/30 selection:text-cyan-800 dark:selection:text-cyan-200">
        {children}
      </body>
    </html>
  );
}

