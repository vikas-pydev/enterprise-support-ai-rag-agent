import type { Metadata } from 'next';
import { Inter, JetBrains_Mono, Newsreader } from 'next/font/google';
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

const newsreader = Newsreader({
  subsets: ['latin'],
  variable: '--font-serif',
  display: 'swap',
  style: ['normal', 'italic'],
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
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} ${newsreader.variable} dark antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-[#F5F3EF] dark:bg-[#16181D] text-[#263142] dark:text-[#EBEFF5] font-sans flex flex-col selection:bg-[#A9DED5]/40 selection:text-[#263142] dark:selection:bg-[#368F88]/30 dark:selection:text-[#EBEFF5]">
        {children}
      </body>
    </html>
  );
}
