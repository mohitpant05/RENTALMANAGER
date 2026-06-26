import Link from "next/link";
import { Button } from "@/components/ui/button";
import { DemoRequestModal } from "./demo-request-modal";

const NAV_LINKS = [
  { label: "Features", href: "#features" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Contact", href: "#contact" },
];

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-background to-primary/10" />

      <header className="relative border-b border-border/50">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <Link href="/" className="text-xl font-bold">
            RentManager
          </Link>
          <nav className="hidden items-center gap-6 md:flex">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                {link.label}
              </a>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <Link href="/register">
              <Button size="sm">Start Free</Button>
            </Link>
            <DemoRequestModal
              trigger={
                <Button variant="outline" size="sm">
                  Book a Demo
                </Button>
              }
            />
          </div>
        </div>
      </header>

      <div className="relative mx-auto max-w-6xl px-4 py-20 text-center sm:py-32">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
          Manage Any Rental Business.
          <br />
          <span className="text-muted-foreground">One Platform.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground sm:text-xl">
          Properties, vehicles, equipment, spaces, and services — configure
          once, manage everything from a single dashboard.
        </p>
        <div className="mt-10 flex items-center justify-center gap-4">
          <Link href="/register">
            <Button size="lg">Start Free</Button>
          </Link>
          <DemoRequestModal
            trigger={
              <Button variant="outline" size="lg">
                Book a Demo
              </Button>
            }
          />
        </div>
      </div>
    </section>
  );
}
