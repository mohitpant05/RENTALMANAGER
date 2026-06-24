import { Hero } from "./components/hero";
import { Verticals } from "./components/verticals";
import { Features } from "./components/features";
import { HowItWorks } from "./components/how-it-works";
import { PlatformHighlights } from "./components/platform-highlights";
import { CtaBanner } from "./components/cta-banner";
import { Footer } from "./components/footer";

export default function MarketingPage() {
  return (
    <main>
      <Hero />
      <Verticals />
      <Features />
      <HowItWorks />
      <PlatformHighlights />
      <CtaBanner />
      <Footer />
    </main>
  );
}
