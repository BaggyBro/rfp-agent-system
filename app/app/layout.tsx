import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "EY RFP Intelligence Workbench",
  description:
    "Upload an RFP PDF and watch the LangGraph multi-agent pipeline work end-to-end.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-slate-950 text-slate-100`}
      >
        <div className="min-h-screen flex flex-col">
          <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-amber-300 via-amber-400 to-amber-500 text-sm font-semibold text-slate-950 shadow-lg">
                  EY
                </div>
                <div>
                  <p className="text-sm font-semibold tracking-tight">
                    RFP Intelligence Workbench
                  </p>
                  <p className="text-xs text-slate-400">
                    Multi-agent AI pipeline · FastAPI · LangGraph · Pinecone
                  </p>
                </div>
              </div>
            </div>
          </header>

          <main className="flex-1">
            <div className="mx-auto max-w-6xl px-4 py-8">{children}</div>
          </main>

          <footer className="border-t border-slate-800 py-3 text-center text-xs text-slate-500">
            Prototype environment – not for production use.
          </footer>
        </div>
      </body>
    </html>
  );
}
