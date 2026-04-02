import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/providers/query-provider";
import { AppSidebar } from "@/components/layout/AppSidebar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Legal AI Frontend",
  description: "Legal AI compliance review console",
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
      <body className="h-screen overflow-hidden bg-slate-50 text-slate-900">
        <QueryProvider>
          <div className="flex h-full min-h-0">
            <AppSidebar />
            <main className="min-h-0 min-w-0 flex-1 overflow-y-auto">{children}</main>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
