"use client";

import { useState } from "react";
import { usePlatformSettings, useUpsertSetting } from "@/hooks/use-platform";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";

export default function SettingsPage() {
  const { data: settings, isLoading } = usePlatformSettings();
  const upsert = useUpsertSetting();
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");
  const [newDesc, setNewDesc] = useState("");

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!newKey.trim() || !newValue.trim()) return;
    upsert.mutate(
      { key: newKey, value: newValue, description: newDesc || undefined },
      {
        onSuccess: () => {
          toast.success(`Setting "${newKey}" saved`);
          setNewKey("");
          setNewValue("");
          setNewDesc("");
        },
        onError: () => toast.error("Failed to save setting"),
      }
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Platform Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Add / Update Setting</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleAdd} className="flex items-end gap-3">
            <div className="flex flex-col gap-1">
              <Label className="text-xs">Key</Label>
              <Input value={newKey} onChange={(e) => setNewKey(e.target.value)} className="w-40" />
            </div>
            <div className="flex flex-1 flex-col gap-1">
              <Label className="text-xs">Value</Label>
              <Input value={newValue} onChange={(e) => setNewValue(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs">Description</Label>
              <Input value={newDesc} onChange={(e) => setNewDesc(e.target.value)} className="w-48" />
            </div>
            <Button type="submit" disabled={upsert.isPending}>
              Save
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Current Settings</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex h-16 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Key</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {settings?.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell className="font-mono text-sm">{s.key}</TableCell>
                    <TableCell>{s.value}</TableCell>
                    <TableCell className="text-muted-foreground">{s.description || "—"}</TableCell>
                    <TableCell>{new Date(s.updated_at).toLocaleString()}</TableCell>
                  </TableRow>
                ))}
                {settings?.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground">
                      No settings configured
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
