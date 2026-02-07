import type { Metadata } from 'next';
import { DM_Sans, Space_Grotesk } from 'next/font/google';
import './globals.css';
import Providers from '@/components/Providers';

const dmSans = DM_Sans({
    subsets: ['latin'],
    variable: '--font-body',
    weight: ['400', '500', '700'],
});

const spaceGrotesk = Space_Grotesk({
    subsets: ['latin'],
    variable: '--font-display',
    weight: ['500', '600', '700'],
});

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
        <html lang="en" className={`scroll-smooth ${dmSans.variable} ${spaceGrotesk.variable}`}>
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
                <link
                    href="https://fonts.googleapis.com/css2?family=Outfit:wght@100..900&display=swap"
                    rel="stylesheet"
                />
            </head>
            <body className={`antialiased ${dmSans.className}`}>
                <Providers>{children}</Providers>
            </body>
        </html>
    );
}
