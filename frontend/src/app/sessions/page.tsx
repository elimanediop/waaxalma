"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Globe2, History, LayoutDashboard, Languages, LogOut, Mic2, RefreshCw, ShieldCheck, UserRound } from "lucide-react";
import { api, authenticatedMutation, ApiError, isAuthenticationError } from "@/lib/auth";
import { useRequiredSession } from "@/lib/use-session";

type TranslationSession = {
  session_id: string;
  agent_name: string;
  execution_mode: string;
  source_language: string;
  target_language: string;
  status: string;
  created_at: string;
  updated_at: string;
};
type SessionsResponse = {
  items: TranslationSession[];
  limit: number;
  offset: number;
  has_more: boolean;
};
const PAGE_SIZE = 20;
function displayDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unknown" : date.toLocaleString();
}

export default function SessionsPage() {
  const router = useRouter();
  const { auth, status, message, retry } = useRequiredSession();
  const [items, setItems] = useState<TranslationSession[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loadedKey, setLoadedKey] = useState("");
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [editor, setEditor] = useState<"create" | "edit" | null>(null);
  const [selected, setSelected] = useState<TranslationSession | null>(null);
  const [source, setSource] = useState("auto");
  const [target, setTarget] = useState("English");
  const [mode, setMode] = useState("standard");
  const [saving, setSaving] = useState(false);
  const [details, setDetails] = useState<Record<string, unknown> | null>(null);
  const [actionError, setActionError] = useState("");
  const [detailBusy, setDetailBusy] = useState(false);
  const [confirmClose, setConfirmClose] = useState(false);

  function openCreate() {
    setSelected(null); setSource("auto"); setTarget("English"); setMode("standard");
    setDetails(null); setActionError(""); setEditor("create"); setConfirmClose(false);
  }

  async function openDetails(item: TranslationSession) {
    setSelected(item); setDetails(null); setActionError(""); setEditor(null);
    setConfirmClose(false); setDetailBusy(true);
    try {
      setDetails(await api<Record<string, unknown>>(`/user/sessions/${encodeURIComponent(item.session_id)}`));
    } catch (err) {
      if (isAuthenticationError(err)) { router.replace("/login"); return; }
      setActionError(err instanceof Error ? err.message : "Unable to load session details.");
    } finally { setDetailBusy(false); }
  }

  function openEdit() {
    if (!selected || selected.status !== "active") return;
    setSource(selected.source_language); setTarget(selected.target_language);
    setMode(selected.execution_mode); setActionError(""); setEditor("edit");
  }

  async function saveSession(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!auth || !editor || saving) return;
    setSaving(true); setActionError("");
    try {
      const payload = { source_language: source.trim(), target_language: target.trim(), execution_mode: mode.trim() };
      if (!payload.source_language || !payload.target_language || !payload.execution_mode) {
        throw new Error("All fields are required.");
      }
      if (editor === "create") {
        await authenticatedMutation("/user/sessions", auth, {
          method: "POST", body: JSON.stringify({ agent_type: "interpreter", ...payload }),
        });
      } else {
        if (!selected) return;
        await authenticatedMutation(`/user/sessions/${encodeURIComponent(selected.session_id)}`, auth, {
          method: "PATCH", body: JSON.stringify(payload),
        });
      }
      setEditor(null); setSelected(null); setDetails(null); load();
    } catch (err) {
      if (isAuthenticationError(err)) { router.replace("/login"); return; }
      setActionError(err instanceof Error ? err.message : "Unable to save session.");
    } finally { setSaving(false); }
  }

  async function closeSession() {
    if (!auth || !selected || saving || selected.status !== "active") return;
    setSaving(true); setActionError("");
    try {
      await authenticatedMutation(`/user/sessions/${encodeURIComponent(selected.session_id)}/close`, auth, {
        method: "POST",
      });
      setSelected(null); setDetails(null); setConfirmClose(false); load();
    } catch (err) {
      if (isAuthenticationError(err)) { router.replace("/login"); return; }
      setActionError(err instanceof Error ? err.message : "Unable to close session.");
    } finally { setSaving(false); }
  }
  const requestKey = `${auth?.user.email ?? "anonymous"}:${offset}:${refresh}`;
  const busy = Boolean(auth) && loadedKey !== requestKey;

  const load = useCallback(() => {
    setOffset(0);
    setRefresh(n => n + 1);
  }, []);

  useEffect(() => {
    if (!auth) return;
    let active = true;
    api<SessionsResponse>(`/user/sessions?limit=${PAGE_SIZE}&offset=${offset}`)
      .then(data => {
        if (!active) return;
        setItems(data.items);
        setHasMore(data.has_more);
        setError("");
      })
      .catch((err: unknown) => {
        if (!active) return;
        if (isAuthenticationError(err)) { router.replace("/login"); return; }
        setError(err instanceof ApiError && err.status === 403
          ? "Access denied to sessions."
          : err instanceof Error ? err.message : "Unable to load sessions.");
      })
      .finally(() => { if (active) setLoadedKey(requestKey); });
    return () => { active = false; };
  }, [auth, offset, refresh, router, requestKey]);

  async function logout() {
    if (!auth) return;
    try {
      await authenticatedMutation("/auth/logout", auth, { method: "POST" });
      router.replace("/login");
    } catch (err) {
      if (isAuthenticationError(err)) { router.replace("/login"); return; }
      setError(err instanceof Error ? err.message : "Unable to sign out.");
    }
  }

  if (status === "error") return <main className="loading" role="alert"><div><p>Unable to verify your session: {message}</p><button className="primary" onClick={retry}>Try again</button></div></main>;
  if (!auth) return <main className="loading">Verifying your session…</main>;

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand dark-brand"><span className="brand-mark"><Globe2 size={23}/></span> WAAXALMA</div>
      <div className="sidebar-label">WORKSPACE</div>
      <nav aria-label="Main navigation">
        <Link href="/dashboard"><LayoutDashboard size={18}/> Dashboard</Link>
        <span className="nav-disabled"><Languages size={18}/> Translate <small>Soon</small></span>
        <span className="nav-disabled"><Mic2 size={18}/> Interpreter <small>Soon</small></span>
        <Link className="nav-active" href="/sessions" aria-current="page"><History size={18}/> My Sessions</Link>
      </nav>
      <div className="sidebar-bottom">
        <div className="sidebar-note"><ShieldCheck size={18}/><strong>Private sessions</strong><span>Only your sessions are visible.</span></div>
        <button className="logout" onClick={logout}><LogOut size={17}/> Sign out</button>
      </div>
    </aside>
    <main className="main-panel">
      <header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <strong>My Sessions</strong></div><div className="profile"><span className="avatar"><UserRound size={17}/></span><span>{auth.user.email}</span></div></header>
      <div className="dashboard-content">
        <div className="welcome"><div><span className="eyebrow">TRANSLATION WORKSPACE</span><h1>My Sessions<span className="period">.</span></h1><p>Browse your private translation sessions.</p></div><button className="sessions-refresh" onClick={load} disabled={busy}><RefreshCw size={16}/> Refresh</button><button className="primary" onClick={openCreate}>New Session</button></div>
        {error && <div className="sessions-notice" role="alert"><p>{error}</p><button className="primary" onClick={load}>Try again</button></div>}
        {!error && busy && <p role="status" className="muted">Loading sessions…</p>}
        {!error && !busy && items.length === 0 && <section className="sessions-empty"><History size={34}/><h2>No sessions found</h2><p>Sessions created from your account will appear here.</p></section>}
        {!error && items.length > 0 && <section className="sessions-grid" aria-label="Your sessions">
          {items.map(item => <article className="session-card" key={item.session_id}>
            <div className="session-card-top"><strong>{item.agent_name}</strong><span className={`session-status ${item.status === "active" ? "is-active" : ""}`}>{item.status}</span></div>
            <p className="session-languages">{item.source_language} → {item.target_language}</p>
            <p className="muted">Mode: {item.execution_mode}</p>
            <p className="muted">Created: {displayDate(item.created_at)}</p>
            <p className="session-id">ID: {item.session_id}</p>
            <button className="sessions-refresh" onClick={() => void openDetails(item)}>View details</button>
          </article>)}
        </section>}
        {(editor || selected) && <section className="session-management-panel" aria-label="Session management">
          <div className="session-management-head">
            <h2>{editor === "create" ? "New Session" : editor === "edit" ? "Edit Session" : "Session Details"}</h2>
            <button type="button" className="sessions-refresh" onClick={() => { setEditor(null); setSelected(null); setDetails(null); setActionError(""); setConfirmClose(false); }}>Dismiss</button>
          </div>
          {actionError && <p className="error" role="alert">{actionError}</p>}
          {editor ? <form onSubmit={saveSession} className="session-management-form">
            <label>Source language<input value={source} onChange={e => setSource(e.target.value)} required minLength={2} maxLength={64}/></label>
            <label>Target language<input value={target} onChange={e => setTarget(e.target.value)} required minLength={2} maxLength={64}/></label>
            <label>Execution mode<input value={mode} onChange={e => setMode(e.target.value)} required minLength={2} maxLength={64}/></label>
            <button className="primary" type="submit" disabled={saving}>{saving ? "Saving…" : editor === "create" ? "Create Session" : "Save Changes"}</button>
          </form> : <>
            {detailBusy && <p role="status">Loading details…</p>}
            {selected && <div className="session-management-details">
              <p><strong>Session ID:</strong> {selected.session_id}</p>
              <p><strong>Status:</strong> {selected.status}</p>
              <p><strong>Agent:</strong> {selected.agent_name}</p>
              <p><strong>Languages:</strong> {selected.source_language} → {selected.target_language}</p>
              <p><strong>Mode:</strong> {selected.execution_mode}</p>
              <p><strong>Created:</strong> {displayDate(selected.created_at)}</p>
              <p><strong>Updated:</strong> {displayDate(selected.updated_at)}</p>
              {details && <p><strong>History entries:</strong> {Array.isArray(details.history) ? details.history.length : 0}</p>}
              {selected.status === "active" && <div className="session-management-actions">
                <button className="sessions-refresh" onClick={openEdit}>Edit Session</button>
                {!confirmClose ? <button className="sessions-danger" onClick={() => setConfirmClose(true)}>Close Session</button> :
                <div role="group" aria-label="Confirm close session"><p>Close this session? This action cannot be undone.</p><button className="sessions-danger" disabled={saving} onClick={() => void closeSession()}>Confirm close</button><button className="sessions-refresh" onClick={() => setConfirmClose(false)}>Cancel</button></div>}
              </div>}
            </div>}
          </>}
        </section>}
        {!error && (offset > 0 || hasMore) && <div className="sessions-pagination">
          <button disabled={busy || offset === 0} onClick={() => setOffset(n => Math.max(0, n - PAGE_SIZE))}>Previous</button>
          <span>Page {Math.floor(offset / PAGE_SIZE) + 1}</span>
          <button disabled={busy || !hasMore} onClick={() => setOffset(n => n + PAGE_SIZE)}>Next</button>
        </div>}
      </div>
    </main>
  </div>;
}
