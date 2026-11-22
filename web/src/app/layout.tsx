import type { Metadata, Viewport } from "next";
import { Geist_Mono, Manrope } from "next/font/google";
import "./globals.css";
import { SITE } from "@/lib/site";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE.url),
  title: { default: SITE.title, template: `%s · ${SITE.name}` },
  description: SITE.description,
  applicationName: SITE.name,
  keywords: [
    "AI hallucination detection",
    "multi-agent systems",
    "agent swarm monitoring",
    "LLM fabrication",
    "AI safety",
    "real-time monitoring",
  ],
  authors: [{ name: "Platanus Hack 26 · Team 6", url: SITE.repo }],
  creator: "Platanus Hack 26 · Team 6",
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    url: "/",
    siteName: SITE.name,
    title: SITE.title,
    description: SITE.description,
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: SITE.title,
    description: SITE.description,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large" },
  },
  category: "technology",
};

export const viewport: Viewport = {
  themeColor: "#000000",
  colorScheme: "dark",
};

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      name: SITE.name,
      url: SITE.url,
      description: SITE.description,
    },
    {
      "@type": "SoftwareApplication",
      name: SITE.name,
      url: SITE.url,
      description: SITE.description,
      applicationCategory: "DeveloperApplication",
      operatingSystem: "Web",
      image: `${SITE.url}/opengraph-image.png`,
      sameAs: [SITE.repo],
      offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
    },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${manrope.variable} ${geistMono.variable} h-full bg-black antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        {children}
      </body>
    </html>
  );
}
