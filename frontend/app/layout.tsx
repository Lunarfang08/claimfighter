import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { Providers } from "@/components/Providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "ClaimFighter — Medical Bill & Insurance Appeal AI",
    template: "%s · ClaimFighter",
  },
  description:
    "AI-powered medical bill analysis and insurance denial appeal assistant. Upload your EOB or denial letter and get a detailed risk report with legal citations, an editable appeal letter, and automated deadline tracking.",
  keywords: [
    "medical bill", "insurance denial", "appeal letter", "EOB analysis",
    "No Surprises Act", "medical billing errors",
  ],
  openGraph: {
    title: "ClaimFighter — Medical Bill & Insurance Appeal AI",
    description:
      "Upload a denial letter and get a risk report with legal citations, an AI-drafted appeal letter, and automated follow-up tracking.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        <Providers>
          <Navbar />
          <main className="flex-1">{children}</main>
          <footer className="border-t bg-muted/30">
            <div className="container max-w-6xl mx-auto px-4 py-8 flex flex-col sm:flex-row items-center justify-between gap-3">
              <p className="text-sm font-semibold tracking-tight">
                Claim<span className="text-primary">Fighter</span>
              </p>
              <p className="text-xs text-muted-foreground text-center">
                AI-assisted analysis — not legal or medical advice. Review all documents before submission.
              </p>
              <p className="text-xs text-muted-foreground">
                © {new Date().getFullYear()} ClaimFighter
              </p>
            </div>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
