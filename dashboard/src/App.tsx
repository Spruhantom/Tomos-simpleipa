import { useState } from "react";

type User = { id: string; username: string; given_name: string; family_name: string; email?: string | null };
type Group = { id: string; name: string; description?: string | null };

const API = import.meta.env.VITE_SIMPLEIPA_API_URL ?? "";

export default function App() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [tab, setTab] = useState<"users" | "groups">("users");
  const [notice, setNotice] = useState("Sign in with your SimpleIPA administrator account.");
  const [busy, setBusy] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${API}/api/v1/${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...init.headers },
    });
    if (!response.ok) throw new Error(`Request failed (${response.status}): ${await response.text()}`);
    return response.json() as Promise<T>;
  }

  async function refresh(activeToken = token) {
    if (!activeToken) return;
    setBusy(true);
    try {
      const [nextUsers, nextGroups] = await Promise.all([
        request<User[]>("users", { headers: { Authorization: `Bearer ${activeToken}` } }),
        request<Group[]>("groups", { headers: { Authorization: `Bearer ${activeToken}` } }),
      ]);
      setUsers(nextUsers); setGroups(nextGroups); setNotice("Signed in. Directory data loaded.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not connect to the API.");
    } finally { setBusy(false); }
  }

  async function signIn(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true);
    try {
      const response = await fetch(`${API}/api/v1/auth/login`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!response.ok) throw new Error(`Sign-in failed (${response.status}). Check your credentials and server configuration.`);
      const data = await response.json() as { access_token: string };
      setToken(data.access_token); setPassword(""); setNotice("Signed in. Loading directory…");
      await refresh(data.access_token);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Sign-in failed.");
    } finally { setBusy(false); }
  }

  async function createUser(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    try {
      await request<User>("users", { method: "POST", body: JSON.stringify({
        username: form.get("username"), given_name: form.get("given_name"),
        family_name: form.get("family_name"), email: form.get("email") || null,
      }) });
      setNotice("User created."); setShowCreate(false); await refresh();
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not create user."); }
    finally { setBusy(false); }
  }

  async function createGroup(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    try {
      await request<Group>("groups", { method: "POST", body: JSON.stringify({
        name: form.get("name"), description: form.get("description") || null,
      }) });
      setNotice("Group created."); setShowCreate(false); await refresh();
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not create group."); }
    finally { setBusy(false); }
  }

  function signOut() {
    setToken(""); setUsers([]); setGroups([]); setShowCreate(false);
    setNotice("Signed out. Your short-lived session token was cleared from this page.");
  }

  return <main className="shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">S</span><span>SimpleIPA<small>IDENTITY ADMIN</small></span></div>
      {token && <nav>
        <button className={tab === "users" ? "active" : ""} onClick={() => setTab("users")}>Users</button>
        <button className={tab === "groups" ? "active" : ""} onClick={() => setTab("groups")}>Groups</button>
      </nav>}
      <div className="sidebar-foot">FreeIPA-powered identity management</div>
    </aside>
    <section className="content">
      <header><div><p className="eyebrow">DIRECTORY</p><h1>{token ? (tab === "users" ? "Users" : "Groups") : "Administrator sign in"}</h1></div>
        {token && <div className="header-actions"><button className="secondary" onClick={() => refresh()} disabled={busy}>Refresh</button><button className="secondary" onClick={signOut}>Sign out</button></div>}
      </header>
      {!token ? <form className="panel auth-panel" onSubmit={signIn}>
        <h2>Sign in to SimpleIPA</h2><p>Use the administrator account configured on your SimpleIPA server.</p>
        <label>Username<input autoComplete="username" required value={username} onChange={e => setUsername(e.target.value)} /></label>
        <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} /></label>
        <button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        <p className="notice" role="status">{notice}</p>
      </form> : <>
        <section className="panel connect">
          <div><strong>Directory connection</strong><p>Authenticated administrator session. Sessions expire after 15 minutes.</p></div>
          <div className="connect-row"><button className="secondary" onClick={() => setShowCreate(!showCreate)}>{showCreate ? "Cancel" : tab === "users" ? "Add user" : "Add group"}</button></div>
          <p className="notice" role="status">{notice}</p>
        </section>
        {showCreate && <form className="panel create-form" onSubmit={tab === "users" ? createUser : createGroup}>
          <h2>{tab === "users" ? "Create directory user" : "Create directory group"}</h2>
          {tab === "users" ? <>
            <label>Username<input name="username" required pattern="[a-zA-Z0-9._-]+" maxLength={64} /></label>
            <label>Given name<input name="given_name" required maxLength={128} /></label>
            <label>Family name<input name="family_name" required maxLength={128} /></label>
            <label>Email<input name="email" type="email" maxLength={254} /></label>
          </> : <>
            <label>Group name<input name="name" required pattern="[a-zA-Z0-9._-]+" maxLength={64} /></label>
            <label>Description<input name="description" maxLength={512} /></label>
          </>}
          <button disabled={busy}>{busy ? "Saving…" : "Create"}</button>
        </form>}
        <section className="panel table-panel">
          <div className="table-heading"><h2>{tab === "users" ? "Directory users" : "Directory groups"}</h2><span>{tab === "users" ? users.length : groups.length} loaded</span></div>
          {tab === "users" ? <table><thead><tr><th>Username</th><th>Name</th><th>Email</th></tr></thead>
            <tbody>{users.map(user => <tr key={user.id}><td>{user.username}</td><td>{user.given_name} {user.family_name}</td><td>{user.email || "—"}</td></tr>)}
              {users.length === 0 && <tr><td colSpan={3} className="empty">No users loaded.</td></tr>}</tbody></table>
          : <table><thead><tr><th>Group</th><th>Description</th></tr></thead>
            <tbody>{groups.map(group => <tr key={group.id}><td>{group.name}</td><td>{group.description || "—"}</td></tr>)}
              {groups.length === 0 && <tr><td colSpan={2} className="empty">No groups loaded.</td></tr>}</tbody></table>}
        </section>
      </>}
      <p className="disclaimer">Directory changes are sent to the authenticated API. The FreeIPA adapter requires Kerberos mutual authentication over verified HTTPS.</p>
    </section>
  </main>;
}
