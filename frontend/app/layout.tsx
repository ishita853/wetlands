import type { Metadata } from "next";
import { Geist_Mono, Noto_Sans, Noto_Serif } from "next/font/google";
import "./globals.css";

import { Header } from "@/components/layout/header";
import { SiteFooter } from "@/components/layout/site-footer";
import { siteConfig } from "@/config/site";

import { Providers } from "./providers";

// Noto Sans: highly legible, institutional, and has sister families for
// Indian scripts should the portal add regional-language support.
const notoSans = Noto_Sans({
  variable: "--font-noto-sans",
  subsets: ["latin"],
});

// Noto Serif: display face for the footer identity, matching Noto Sans.
const notoSerif = Noto_Serif({
  variable: "--font-noto-serif",
  subsets: ["latin"],
  weight: ["700"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: siteConfig.name,
  description: siteConfig.description,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${notoSans.variable} ${notoSerif.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <Providers>
          <Header />
          <main id="main-content" tabIndex={-1} className="flex-1 outline-none">
            {children}
          </main>
          <SiteFooter />
        </Providers>
      </body>
    </html>
  );
}
