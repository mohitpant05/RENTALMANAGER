import { useQuery } from "@tanstack/react-query";
import { create } from "zustand";
import api from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";

interface CurrencyState {
  displayCurrency: string;
  setDisplayCurrency: (code: string) => void;
}

const DISPLAY_CURRENCY_KEY = "rm_display_currency";

export const useCurrencyStore = create<CurrencyState>((set) => ({
  displayCurrency:
    typeof window !== "undefined"
      ? localStorage.getItem(DISPLAY_CURRENCY_KEY) || "USD"
      : "USD",
  setDisplayCurrency: (code: string) => {
    if (typeof window !== "undefined") {
      localStorage.setItem(DISPLAY_CURRENCY_KEY, code);
    }
    set({ displayCurrency: code });
  },
}));

export const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: "$", EUR: "€", GBP: "£", INR: "₹", JPY: "¥", CNY: "¥",
  AUD: "A$", CAD: "C$", CHF: "Fr", SGD: "S$", AED: "د.إ",
  SAR: "﷼", BRL: "R$", MXN: "$", ZAR: "R", THB: "฿",
  KRW: "₩", TRY: "₺", RUB: "₽", NZD: "NZ$", SEK: "kr",
  NOK: "kr", DKK: "kr", HKD: "HK$", MYR: "RM", PHP: "₱",
  IDR: "Rp", VND: "₫", EGP: "E£", NGN: "₦", KES: "KSh", PKR: "₨",
};

export function useRates(base: string = "USD") {
  return useQuery({
    queryKey: ["currency-rates", base],
    queryFn: async () => {
      const { data } = await api.get<{ base: string; rates: Record<string, number> }>(
        `/currency/rates?base=${base}`
      );
      return data.rates;
    },
    staleTime: 60 * 60 * 1000,
    gcTime: 2 * 60 * 60 * 1000,
  });
}

export function useSupportedCurrencies() {
  return useQuery({
    queryKey: ["supported-currencies"],
    queryFn: async () => {
      const { data } = await api.get<{ currencies: string[] }>("/currency/supported");
      return data.currencies;
    },
    staleTime: 24 * 60 * 60 * 1000,
  });
}

export function useUserCurrency(): string {
  const user = useAuthStore((s) => s.user);
  const storeCurrency = useCurrencyStore((s) => s.displayCurrency);
  return user?.preferred_currency ?? storeCurrency ?? "USD";
}

export function convertPrice(
  amount: number,
  fromCurrency: string,
  toCurrency: string,
  rates: Record<string, number> | undefined
): number {
  if (!rates || fromCurrency === toCurrency) return amount;
  const fromRate = rates[fromCurrency] ?? 1;
  const toRate = rates[toCurrency] ?? 1;
  if (fromRate === 0) return 0;
  return Math.round((amount / fromRate) * toRate * 100) / 100;
}

export function formatPrice(amount: number, currency: string): string {
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    const symbol = CURRENCY_SYMBOLS[currency] || currency;
    return `${symbol}${amount.toFixed(2)}`;
  }
}

export function useFormatPrice() {
  const { data: rates } = useRates();
  const currency = useUserCurrency();

  return (amount: number, fromCurrency: string = "USD"): string => {
    const converted = convertPrice(amount, fromCurrency, currency, rates);
    return formatPrice(converted, currency);
  };
}
