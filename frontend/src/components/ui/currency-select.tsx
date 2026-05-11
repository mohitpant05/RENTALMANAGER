"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CURRENCY_SYMBOLS, useSupportedCurrencies } from "@/hooks/use-currency";

interface CurrencySelectProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export function CurrencySelect({ value, onChange, className }: CurrencySelectProps) {
  const { data: currencies } = useSupportedCurrencies();
  const list = currencies ?? Object.keys(CURRENCY_SYMBOLS);

  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className={className}>
        <SelectValue placeholder="Currency" />
      </SelectTrigger>
      <SelectContent className="max-h-60">
        {list.map((code) => (
          <SelectItem key={code} value={code}>
            {CURRENCY_SYMBOLS[code] || ""} {code}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
