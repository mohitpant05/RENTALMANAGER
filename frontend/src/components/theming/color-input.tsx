"use client";

import { useRef } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ColorInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
}

export function ColorInput({ label, value, onChange }: ColorInputProps) {
  const pickerRef = useRef<HTMLInputElement>(null);

  return (
    <div className="space-y-1.5">
      <Label className="text-xs">{label}</Label>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="h-9 w-9 shrink-0 rounded-md border shadow-sm"
          style={{ backgroundColor: value || "#000000" }}
          onClick={() => pickerRef.current?.click()}
        />
        <input
          ref={pickerRef}
          type="color"
          value={value || "#000000"}
          onChange={(e) => onChange(e.target.value)}
          className="sr-only"
        />
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="#000000"
          className="font-mono text-xs"
        />
      </div>
    </div>
  );
}
