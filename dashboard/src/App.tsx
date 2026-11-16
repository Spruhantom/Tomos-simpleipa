import { useEffect, useState } from "react";

type User = { id: string; username: string; given_name: string; family_name: string; email?: string | null };
type Group = { id: string; name: string; description?: string | null };

const API = import.meta.env.VITE_SIMPLEIPA_API_URL ?? "";

export default function App() {
  const [token, setToken] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [tab, setTab] = useState<"users" | "groups">("users");
  const [notice, setNotice] = useState("Connect to your SimpleIPA management API.");
  const [busy, setBusy] = useState(false);

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${API}/api/v1/${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...init.headers },
    });
    if (!response.ok) throw new Error(`API returned ${response.status}: ${await response.text()}`);
    return response.json() as Promise<T>;
  }

  async function refresh() {
    if (!token) { setNotice("Enter the API bearer token to connect."); return; }
    setBusy(true);
    try {
      const [nextUsers, nextGroups] = await Promise.all([
        request<User[]>("users"), request<Group[]>("groups"),
      ]);
      setUsers(nextUsers); setGroups(nextGroups); setNotice("Connected. Directory data loaded.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not connect to the API.");
    } finally { setBusy(false); }
  }

  useEffect(() => { setUsers([]); setGroups([]); }, [token]);

  return <main className="shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">S</span><span>SimpleIPA<small>IDENTITY ADMIN</small></span></div>
      <nav>
        <button className={tab === "users" ? "active" : ""} onClick={() => setTab("users")}>Users</button>
        <button className={tab === "groups" ? "active" : ""} onClick={() => setTab("groups")}>Groups</button>
      </nav>
      <div className="sidebar-foot">FreeIPA-powered identity management</div>
    </aside>
    <section className="content">
      <header><div><p className="eyebrow">DIRECTORY</p><h1>{tab === "users" ? "Users" : "Groups"}</h1></div>
        <button className="secondary" onClick={refresh} disabled={busy}>{busy ? "Loading…" : "Refresh"}</button>
      </header>
      <section className="connect panel">
        <div><strong>API connection</strong><p>Use an administrator API token supplied by your server administrator.</p></div>
        <div className="connect-row">
          <input aria-label="API bearer token" type="password" autoComplete="off" placeholder="Bearer token" value={token} onChange={e => setToken(e.target.value)} />
          <button onClick={refresh} disabled={busy || !token}>{busy ? "Connecting…" : "Connect"}</button>
        </div>
        <p className="notice" role="status">{notice}</p>
      </section>
      <section className="panel table-panel">
        <div className="table-heading"><h2>{tab === "users" ? "Directory users" : "Directory groups"}</h2><span>{tab === "users" ? users.length : groups.length} loaded</span></div>
        {tab === "users" ? <table><thead><tr><th>Username</th><th>Name</th><th>Email</th></tr></thead>
          <tbody>{users.map(user => <tr key={user.id}><td>{user.username}</td><td>{user.given_name} {user.family_name}</td><td>{user.email || "—"}</td></tr>)}
            {users.length === 0 && <tr><td colSpan={3} className="empty">No users loaded. Connect to the API to view directory users.</td></tr>}</tbody></table>
          : <table><thead><tr><th>Group</th><th>Description</th></tr></thead>
            <tbody>{groups.map(group => <tr key={group.id}><td>{group.name}</td><td>{group.description || "—"}</td></tr>)}
              {groups.length === 0 && <tr><td colSpan={2} className="empty">No groups loaded. Connect to the API to view directory groups.</td></tr>}</tbody></table>}
      </section>
      <p className="disclaimer">Foundation UI only: directory writes are not enabled in this dashboard build. All directory operations must pass through the authenticated API and a configured FreeIPA adapter.</p>
    </section>
  </main>;
}
