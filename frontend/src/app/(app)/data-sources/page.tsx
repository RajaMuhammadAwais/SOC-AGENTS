// Style contract: dark slate console, cyan accents (see globals.css).
// Data Sources console: register connectors, upload raw events, run the pipeline.
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, Loader2, Plus, Trash2, Upload } from "lucide-react";
import { useState } from "react";
import {
  EmptyState,
  PageHeader,
  StatusBadge,
  formatRelativeTime
} from "@/components/soc/elements";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  DataSourceCreatePayload,
  createDataSource,
  deleteDataSource,
  listDataSources,
  uploadToDataSource
} from "@/lib/api/client";

const SOURCE_TYPES = ["api_json", "cef", "syslog", "csv"] as const;

const CONFIG_HINTS: Record<string, string[]> = {
  api_json: ["api_token (required)"],
  cef: ["listen_port (optional, default 514)"],
  syslog: ["listen_port (optional, default 514)", "protocol (tcp|udp)"],
  csv: ["delimiter (optional, default ',')", "has_header (bool, default true)"]
};

export default function DataSourcesPage() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [uploadTarget, setUploadTarget] = useState<string | null>(null);

  const sourcesQuery = useQuery({
    queryKey: ["data-sources"],
    queryFn: listDataSources
  });

  const createMutation = useMutation({
    mutationFn: createDataSource,
    onSuccess: () => {
      setCreateOpen(false);
      queryClient.invalidateQueries({ queryKey: ["data-sources"] });
    }
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDataSource,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["data-sources"] })
  });

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        title="Data Sources"
        description="Ingestion connectors. Upload raw events (CEF, syslog, CSV, JSON) and the pipeline normalizes, detects, and scores them automatically."
        actions={
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="mr-1 h-4 w-4" />
                Register connector
              </Button>
            </DialogTrigger>
            <CreateSourceDialog
              pending={createMutation.isPending}
              error={createMutation.error?.message ?? null}
              onSubmit={(payload) => createMutation.mutate(payload)}
            />
          </Dialog>
        }
      />

      {sourcesQuery.isPending ? (
        <div className="flex items-center justify-center py-16 text-slate-400">
          <Loader2 className="mr-3 h-5 w-5 animate-spin text-cyan-400" />
          Loading data sources
        </div>
      ) : (sourcesQuery.data?.items ?? []).length === 0 ? (
        <EmptyState message="No data sources registered yet. Register a connector to begin ingesting events." />
      ) : (
        <div className="overflow-hidden rounded-md border border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-950 text-slate-400">
              <tr>
                <th className="px-3 py-2">Connector</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Created</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {(sourcesQuery.data?.items ?? []).map((source) => (
                <tr key={source.id} className="hover:bg-slate-900/60">
                  <td className="px-3 py-3 text-slate-100">{source.name}</td>
                  <td className="px-3 py-3 text-slate-400">{source.source_type}</td>
                  <td className="px-3 py-3">
                    <StatusBadge status={source.is_active ? "open" : "closed"} />
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-slate-400">
                    {formatRelativeTime(source.created_at)}
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setUploadTarget(source.id)}
                        className="inline-flex items-center gap-1 rounded border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:border-cyan-500 hover:text-cyan-300"
                      >
                        <Upload className="h-3 w-3" />
                        Upload
                      </button>
                      <button
                        type="button"
                        disabled={deleteMutation.isPending}
                        onClick={() => deleteMutation.mutate(source.id)}
                        className="inline-flex items-center rounded border border-slate-700 px-2 py-1 text-xs text-slate-400 hover:border-red-500 hover:text-red-300 disabled:opacity-50"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {uploadTarget ? (
        <UploadDialog
          sourceId={uploadTarget}
          onClose={() => setUploadTarget(null)}
        />
      ) : null}
    </div>
  );
}

function CreateSourceDialog({
  pending,
  error,
  onSubmit
}: {
  pending: boolean;
  error: string | null;
  onSubmit: (payload: DataSourceCreatePayload) => void;
}) {
  const [name, setName] = useState("");
  const [sourceType, setSourceType] = useState<(typeof SOURCE_TYPES)[number]>("csv");
  const [configText, setConfigText] = useState("");

  const config = Object.fromEntries(
    configText
      .split("\n")
      .map((line) => line.split("=").map((part) => part.trim()))
      .filter((pair) => pair.length === 2 && pair[0])
  );

  return (
    <DialogContent className="bg-slate-900 text-slate-100">
      <DialogHeader>
        <DialogTitle>Register connector</DialogTitle>
        <DialogDescription>
          Add an ingestion source. Raw events uploaded to it flow through the
          normalization, detection, and risk-scoring pipeline.
        </DialogDescription>
      </DialogHeader>
      <div className="grid gap-4">
        <div className="grid gap-2">
          <Label htmlFor="source-name">Connector name</Label>
          <Input
            id="source-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Production CEF feed"
            required
          />
        </div>
        <div className="grid gap-2">
          <Label>Connector type</Label>
          <Select
            value={sourceType}
            onValueChange={(value) => setSourceType(value as (typeof SOURCE_TYPES)[number])}
          >
            <SelectTrigger className="bg-slate-800">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SOURCE_TYPES.map((type) => (
                <SelectItem key={type} value={type}>
                  {type}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="source-config">
            Configuration (key=value, one per line)
          </Label>
          <Textarea
            id="source-config"
            value={configText}
            onChange={(event) => setConfigText(event.target.value)}
            placeholder={CONFIG_HINTS[sourceType].join("\n")}
            rows={3}
          />
        </div>
        {error ? (
          <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {error}
          </p>
        ) : null}
      </div>
      <DialogFooter>
        <Button
          onClick={() => {
            if (!name.trim()) return;
            onSubmit({
              name: name.trim(),
              source_type: sourceType,
              config: sourceType === "api_json" && !config.api_token
                ? { ...config, api_token: "" }
                : config
            });
          }}
          disabled={pending || !name.trim()}
        >
          {pending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
          Register
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}

function UploadDialog({
  sourceId,
  onClose
}: {
  sourceId: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [rawText, setRawText] = useState("");
  const [result, setResult] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: () => uploadToDataSource(sourceId, rawText),
    onSuccess: (response) => {
      setResult(
        response.normalized
          ? `Ingested. Trace ${response.trace_id} — normalized and risk-scored (${response.observables} observables).`
          : `Stored raw (trace ${response.trace_id}), but validation or enrichment could not complete.`
      );
      setRawText("");
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    }
  });

  return (
    <Dialog open onOpenChange={(open) => (open ? null : onClose())}>
      <DialogContent className="bg-slate-900 text-slate-100">
        <DialogHeader>
          <DialogTitle>Upload raw events</DialogTitle>
          <DialogDescription>
            Paste CEF, syslog, or CSV rows. Each line becomes an event that runs
            through normalization, detection rules, and risk scoring.
          </DialogDescription>
        </DialogHeader>
        <Textarea
          value={rawText}
          onChange={(event) => setRawText(event.target.value)}
          placeholder={`CEF example: Jan 12 09:00:00 fw01 CEF:0|Vendor|Product|1.0|SIG-100|Suspicious login|7|src=10.0.0.5 dst=192.168.1.10 suser=svc_backup`}
          rows={8}
          className="font-mono text-xs"
        />
        {result ? (
          <p className="rounded border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
            {result}
          </p>
        ) : null}
        {uploadMutation.error ? (
          <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {uploadMutation.error.message}
          </p>
        ) : null}
        <DialogFooter>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={() => uploadMutation.mutate()}
            disabled={uploadMutation.isPending || !rawText.trim()}
          >
            {uploadMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Database className="mr-1 h-4 w-4" />
            )}
            Ingest
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
