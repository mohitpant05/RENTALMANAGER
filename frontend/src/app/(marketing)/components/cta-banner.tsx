import Link from "next/link";
import { Button } from "@/components/ui/button";

export function CtaBanner() {
  return (
    <section id="contact" className="border-t bg-primary py-16 sm:py-24">
      <div className="mx-auto max-w-6xl px-4 text-center">
        <h2 className="text-3xl font-bold tracking-tight text-primary-foreground sm:text-4xl">
          Ready to launch your rental business?
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-primary-foreground/80">
          Join businesses across 5 industries already using RentManager
        </p>
        <div className="mt-10 flex items-center justify-center gap-4">
          <Link href="/register">
            <Button
              size="lg"
              variant="secondary"
            >
              Start Free
            </Button>
          </Link>
          <a href="mailto:contact@rentmanager.com">
            <Button
              size="lg"
              variant="outline"
              className="border-primary-foreground/30 text-primary-foreground hover:bg-primary-foreground/10"
            >
              Book a Demo
            </Button>
          </a>
        </div>
      </div>
    </section>
  );
}
