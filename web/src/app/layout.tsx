import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Splitpoint", template: "%s · Splitpoint" },
  description: "Where a failing coding-agent run went wrong, shown next to a run that passed the same task.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col font-sans">
        <header className="border-b border-line bg-surface">
          <nav className="mx-auto flex max-w-6xl items-center gap-6 px-5 py-3 text-sm">
            <Link href="/" className="font-medium tracking-tight text-ink">
              Splitpoint
            </Link>
            <Link href="/" className="text-muted hover:text-ink">
              Pairs
            </Link>
            <Link href="/findings/" className="text-muted hover:text-ink">
              Findings
            </Link>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-5 py-8">{children}</main>
        <footer className="border-t border-line text-xs text-muted">
          <div className="mx-auto max-w-6xl px-5 py-4">
            Runs from{" "}
            <a className="underline" href="https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories">
              SWE-smith trajectories
            </a>{" "}
            (MIT). Verdicts by Claude Haiku 4.5, checked against human labels.
          </div>
        </footer>
      </body>
    </html>
  );
}
