import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JakeGPT | Jakerton's Garden Planning Tool",
  description: "Plan a garden on your actual property."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
