import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mexico Limited CRM Demo",
  description: "Plataforma de onboarding, diagnóstico y vinculación para emprendedores de Mexico Limited.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>
        {children}
      </body>
    </html>
  );
}
