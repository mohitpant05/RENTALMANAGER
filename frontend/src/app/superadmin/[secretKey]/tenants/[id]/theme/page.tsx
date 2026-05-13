"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTenantTheme } from "@/hooks/use-platform";
import { usePlatformStore } from "@/lib/platform-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import axios from "axios";

export default function ThemeEditorPage() {
  const params = useParams<{ secretKey: string; id: string }>();
  const { data: theme, isLoading, refetch } = useTenantTheme(params.id);
  const { token } = usePlatformStore();
  const [colors, setColors] = useState<Record<string, string>>({});
  const [brandName, setBrandName] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (theme) {
      setColors((theme.colors as Record<string, string>) || {});
      setBrandName((theme.brand as Record<string, string>)?.name || "");
    }
  }, [theme]);

  async function handleSave() {
    setSaving(true);
    try {
      await axios.put(
        `/api/platform/tenants/${params.id}/theme`,
        {
          brand: { ...theme?.brand, name: brandName },
          colors,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success("Theme saved");
      refetch();
    } catch {
      toast.error("Failed to save theme");
    } finally {
      setSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Theme Editor</h1>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save Theme"}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Brand</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-2">
            <Label>Brand Name</Label>
            <Input value={brandName} onChange={(e) => setBrandName(e.target.value)} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Colors</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
            {Object.entries(colors).map(([key, value]) => (
              <div key={key} className="flex flex-col gap-1">
                <Label className="text-xs">{key}</Label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={value}
                    onChange={(e) => setColors({ ...colors, [key]: e.target.value })}
                    className="h-8 w-8 cursor-pointer rounded border"
                  />
                  <Input
                    value={value}
                    onChange={(e) => setColors({ ...colors, [key]: e.target.value })}
                    className="h-8 font-mono text-xs"
                  />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Raw JSON</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="max-h-64 overflow-auto rounded bg-muted p-3 text-xs">
            {JSON.stringify(theme, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
