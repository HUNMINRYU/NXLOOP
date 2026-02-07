import type { Metadata } from 'next';
import './globals.css';
import Providers from '@/components/Providers';

export const metadata: Metadata = {
    title: 'NEXLOOP - AI Automated Video Pipeline',
    description: 'Automated video pipeline powered by Gemini 3.0 and VEO 3.1',
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className="scroll-smooth">
            <body className="antialiased">
                <Providers>{children}</Providers>
            </body>
        </html>
    );
}
