import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FileCheck2,
  ShieldCheck,
  TrendingDown,
  TrendingUp
} from "lucide-react";

import { AppShell } from "@/components/app-shell";

const executiveMetrics = [
  {
    label: "Enterprise risk",
    value: "71",
    detail: "High, down 6 pts",
    tone: "text-amber-300",
    icon: ShieldCheck
  },
  {
    label: "Critical incidents",
    value: "3",
    detail: "1 containment pending",
    tone: "text-red-300",
    icon: AlertTriangle
  },
  {
    label: "Compliance coverage",
    value: "88%",
    detail: "NIST CSF mapped",
    tone: "text-emerald-300",
    icon: FileCheck2
  },
  {
    label: "Mean time to respond",
    value: "42m",
    detail: "18% faster this week",
    tone: "text-cyan-300",
    icon: Clock3
  }
];

const riskTrend = [
  { label: "Mon", value: 78 },
  { label: "Tue", value: 76 },
  { label: "Wed", value: 75 },
  { label: "Thu", value: 71 },
  { label: "Fri", value: 69 },
  { label: "Sat", value: 68 },
  { label: "Sun", value: 71 }
];

const incidentPortfolio = [
  {
    name: "Identity attack campaign",
    owner: "SOC Lead",
    severity: "Critical",
    status: "Containment",
    exposure: "12 accounts"
  },
  {
    name: "Suspicious PowerShell activity",
    owner: "IR Analyst",
    severity: "High",
    status: "Investigation",
    exposure: "4 endpoints"
  },
  {
    name: "Internet-facing CVE signal",
    owner: "Vuln Mgmt",
    severity: "High",
    status: "Mitigation",
    exposure: "2 services"
  }
];

const complianceRows = [
  { framework: "NIST CSF Detect", coverage: 92, gap: "Cloud audit correlation" },
  { framework: "NIST CSF Respond", coverage: 84, gap: "Response approval evidence" },
  { framework: "MITRE ATT&CK mapping", coverage: 79, gap: "Collection coverage for scripts" }
];

const agentDecisions = [
  "Risk scoring raised identity campaign to critical.",
  "Threat hunting found 9 similar RDP events.",
  "Response agent is waiting for account-disable approval."
];

export default function ExecutiveDashboardPage() {
  return (
    <AppShell>
      <main className="min-h-screen">
        <section className="border-b border-slate-800 bg-slate-950">
          <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-5 md:flex-row md:items-center md:justify-between md:px-6">
            <div>
              <p className="text-sm text-cyan-300">Enterprise AI SOC</p>
              <h1 className="mt-1 text-2xl font-semibold text-white">Executive Dashboard</h1>
              <p className="mt-1 max-w-2xl text-sm text-slate-400">
                Risk posture, active incidents, compliance coverage, and agent decisions for
                leadership review.
              </p>
            </div>
            <div className="inline-flex w-fit items-center gap-2 rounded-md border border-emerald-700 bg-emerald-950 px-3 py-2 text-sm text-emerald-200">
              <CheckCircle2 className="h-4 w-4" />
              Monitoring active
            </div>
          </div>
        </section>

        <section className="mx-auto grid max-w-7xl gap-4 px-5 py-5 sm:grid-cols-2 lg:grid-cols-4 lg:px-6">
          {executiveMetrics.map((metric) => {
            const Icon = metric.icon;
            return (
              <div
                key={metric.label}
                className="rounded-md border border-slate-800 bg-slate-900 p-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm text-slate-400">{metric.label}</p>
                  <Icon className={`h-5 w-5 ${metric.tone}`} />
                </div>
                <p className="mt-3 text-3xl font-semibold text-white">{metric.value}</p>
                <p className="mt-1 text-sm text-slate-400">{metric.detail}</p>
              </div>
            );
          })}
        </section>

        <section className="mx-auto grid max-w-7xl gap-4 px-5 pb-6 lg:grid-cols-[1.35fr_0.65fr] lg:px-6">
          <div className="rounded-md border border-slate-800 bg-slate-900 p-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-white">Risk Movement</h2>
                <p className="mt-1 text-sm text-slate-400">Seven-day enterprise risk score</p>
              </div>
              <div className="inline-flex items-center gap-2 text-sm text-emerald-300">
                <TrendingDown className="h-4 w-4" />
                Improving
              </div>
            </div>
            <div className="mt-6 grid h-56 grid-cols-7 items-end gap-3 border-b border-slate-800 pb-3">
              {riskTrend.map((point) => (
                <div key={point.label} className="flex h-full flex-col justify-end gap-2">
                  <div
                    className="rounded-t bg-cyan-400"
                    style={{ height: `${point.value}%` }}
                    aria-label={`${point.label} risk ${point.value}`}
                  />
                  <span className="text-center text-xs text-slate-500">{point.label}</span>
                </div>
              ))}
            </div>
          </div>

          <aside className="rounded-md border border-slate-800 bg-slate-900 p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">Agent Decisions</h2>
              <Activity className="h-5 w-5 text-cyan-300" />
            </div>
            <div className="mt-4 space-y-3">
              {agentDecisions.map((decision) => (
                <div key={decision} className="border-l-2 border-cyan-400 pl-3 text-sm text-slate-300">
                  {decision}
                </div>
              ))}
            </div>
          </aside>
        </section>

        <section className="mx-auto grid max-w-7xl gap-4 px-5 pb-8 lg:grid-cols-[1.1fr_0.9fr] lg:px-6">
          <div className="rounded-md border border-slate-800 bg-slate-900 p-5">
            <h2 className="text-lg font-semibold text-white">Incident Portfolio</h2>
            <div className="mt-4 overflow-hidden rounded-md border border-slate-800">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-950 text-slate-400">
                  <tr>
                    <th className="px-3 py-2">Incident</th>
                    <th className="px-3 py-2">Owner</th>
                    <th className="px-3 py-2">Severity</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Exposure</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {incidentPortfolio.map((incident) => (
                    <tr key={incident.name}>
                      <td className="px-3 py-3 text-slate-100">{incident.name}</td>
                      <td className="px-3 py-3 text-slate-400">{incident.owner}</td>
                      <td className="px-3 py-3 text-amber-300">{incident.severity}</td>
                      <td className="px-3 py-3 text-slate-300">{incident.status}</td>
                      <td className="px-3 py-3 text-slate-400">{incident.exposure}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-md border border-slate-800 bg-slate-900 p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">Compliance Coverage</h2>
              <TrendingUp className="h-5 w-5 text-emerald-300" />
            </div>
            <div className="mt-4 space-y-4">
              {complianceRows.map((row) => (
                <div key={row.framework}>
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span className="text-slate-200">{row.framework}</span>
                    <span className="text-slate-400">{row.coverage}%</span>
                  </div>
                  <div className="mt-2 h-2 rounded bg-slate-800">
                    <div
                      className="h-2 rounded bg-emerald-400"
                      style={{ width: `${row.coverage}%` }}
                    />
                  </div>
                  <p className="mt-1 text-xs text-slate-500">Gap: {row.gap}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </AppShell>
  );
}
