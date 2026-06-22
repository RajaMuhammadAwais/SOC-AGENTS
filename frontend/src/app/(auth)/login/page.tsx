"use client";

import { useMutation } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { login } from "@/lib/api/client";

const inputClassName =
  "mt-2 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 outline-none focus:border-cyan-400";

export default function LoginPage() {
  const [tenantSlug, setTenantSlug] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const mutation = useMutation({
    mutationFn: login,
    onSuccess: (tokens) => {
      sessionStorage.setItem("access_token", tokens.access_token);
      sessionStorage.setItem("refresh_token", tokens.refresh_token);
      window.location.assign("/");
    }
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate({
      tenant_slug: tenantSlug,
      email,
      password
    });
  }

  return (
    <main className="grid min-h-screen bg-slate-950 text-slate-100 lg:grid-cols-[1fr_460px]">
      <section className="hidden border-r border-slate-800 bg-slate-900 px-10 py-12 lg:block">
        <div className="flex items-center gap-3">
          <ShieldCheck className="h-7 w-7 text-cyan-300" />
          <div>
            <p className="text-sm text-cyan-300">Enterprise AI SOC</p>
            <h1 className="text-2xl font-semibold">Security Operations Console</h1>
          </div>
        </div>
        <div className="mt-16 max-w-2xl">
          <p className="text-sm uppercase tracking-[0.2em] text-slate-500">Analyst workspace</p>
          <p className="mt-4 text-4xl font-semibold leading-tight">
            Triage, investigate, and respond with controlled AI assistance.
          </p>
        </div>
      </section>

      <section className="flex items-center justify-center px-6 py-10">
        <form className="w-full max-w-sm space-y-5" onSubmit={submit}>
          <div>
            <p className="text-sm text-cyan-300">Sign in</p>
            <h2 className="mt-1 text-2xl font-semibold">Access your tenant</h2>
          </div>

          <label className="block text-sm">
            <span className="text-slate-300">Tenant slug</span>
            <input
              className={inputClassName}
              value={tenantSlug}
              onChange={(event) => setTenantSlug(event.target.value)}
              required
            />
          </label>

          <label className="block text-sm">
            <span className="text-slate-300">Email</span>
            <input
              className={inputClassName}
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>

          <label className="block text-sm">
            <span className="text-slate-300">Password</span>
            <input
              className={inputClassName}
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>

          {mutation.isError ? (
            <p className="rounded-md border border-red-900 bg-red-950 px-3 py-2 text-sm text-red-200">
              {mutation.error.message}
            </p>
          ) : null}

          <Button className="w-full" type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Signing in" : "Sign in"}
          </Button>
        </form>
      </section>
    </main>
  );
}
