import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "RentManager — Manage Any Rental Business",
  description:
    "All-in-one rental management platform for properties, vehicles, equipment, spaces, and services. Dynamic pricing, multiple payment gateways, staff management, and more.",
  openGraph: {
    title: "RentManager — Manage Any Rental Business",
    description:
      "All-in-one rental management platform for properties, vehicles, equipment, spaces, and services.",
    type: "website",
  },
};

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <div className="min-h-screen bg-background">{children}</div>;
}
