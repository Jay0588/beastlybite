import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "J.A.Y. — Just Assists You",
  description: "Personal AI Operating System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="h-screen overflow-hidden bg-jay-bg text-jay-text antialiased">
        {children}
      </body>
    </html>
  );
}
