import { useState } from "react";
import type { FormEvent } from "react";
type User = { id: string; username: string; given_name: string; family_name: string; email?: string | null };
type Group = { id: string; name: string; description?: string | null };
type DNSZone = { name: string };
type DNSRecord = { name: string; record_type: string; value: string };
type Certificate = { serial_number: string; subject?: string | null; principal?: string | null; status?: string | null; issued_on?: string | null; expires_on?: string | null };
const API = import.meta.env.VITE_SIMPLEIPA_API_URL ?? "";
export default function App() {
  const [username,setUsername]=useState(""); const [password,setPassword]=useState(""); const [token,setToken]=useState("");
  const [users,setUsers]=useState<User[]>([]); const [groups,setGroups]=useState<Group[]>([]);
  const [zones,setZones]=useState<DNSZone[]>([]); const [records,setRecords]=useState<DNSRecord[]>([]); const [certificates,setCertificates]=useState<Certificate[]>([]);
  const [selectedZone,setSelectedZone]=useState(""); const [tab,setTab]=useState<"users"|"groups"|"dns"|"certificates">("users");
  const [notice,setNotice]=useState("Sign in with your SimpleIPA administrator account."); const [busy,setBusy]=useState(false); const [showCreate,setShowCreate]=useState(false);
  async function request<T>(path:string,init:RequestInit={},activeToken=token):Promise<T>{
    const response=await fetch(`${API}/api/v1/${path}`,{...init,headers:{"Content-Type":"application/json",...(activeToken?{Authorization:`Bearer ${activeToken}`}:{}),...init.headers}});
    if(!response.ok) throw new Error(`Request failed (${response.status}): ${await response.text()}`);
    return response.json() as Promise<T>;
  }
  async function loadRecords(zone=selectedZone){if(!zone){setRecords([]);return;}try{setRecords(await request<DNSRecord[]>(`dns/zones/${encodeURIComponent(zone)}/records`));}catch(e){setNotice(e instanceof Error?e.message:"Could not load DNS records.");}}
  async function refresh(activeToken=token){if(!activeToken)return;setBusy(true);try{
    const [u,g,z,c]=await Promise.all([request<User[]>("users",{},activeToken),request<Group[]>("groups",{},activeToken),request<DNSZone[]>("dns/zones",{},activeToken),request<Certificate[]>("certificates",{},activeToken)]);
    setUsers(u);setGroups(g);setZones(z);setCertificates(c);const zone=selectedZone||z[0]?.name||"";setSelectedZone(zone);
    setRecords(zone?await request<DNSRecord[]>(`dns/zones/${encodeURIComponent(zone)}/records`,{},activeToken):[]);
    setNotice("Signed in. Directory data loaded.");
  }catch(e){setNotice(e instanceof Error?e.message:"Could not connect to the API.");}finally{setBusy(false);}}
  async function signIn(event:FormEvent<HTMLFormElement>){event.preventDefault();setBusy(true);try{
    const response=await fetch(`${API}/api/v1/auth/login`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username,password})});
    if(!response.ok)throw new Error(`Sign-in failed (${response.status}). Check your credentials and server configuration.`);
    const data=await response.json() as {access_token:string};setToken(data.access_token);setPassword("");setNotice("Signed in. Loading directory…");await refresh(data.access_token);
  }catch(e){setNotice(e instanceof Error?e.message:"Sign-in failed.");}finally{setBusy(false);}}
  async function submitCreate(event:FormEvent<HTMLFormElement>){event.preventDefault();const form=new FormData(event.currentTarget);setBusy(true);try{
    if(tab==="users")await request("users",{method:"POST",body:JSON.stringify({username:form.get("username"),given_name:form.get("given_name"),family_name:form.get("family_name"),email:form.get("email")||null})});
    else if(tab==="groups")await request("groups",{method:"POST",body:JSON.stringify({name:form.get("name"),description:form.get("description")||null})});
    else if(!zones.length) {const zone=await request<DNSZone>("dns/zones",{method:"POST",body:JSON.stringify({name:form.get("zone")})});setSelectedZone(zone.name);}
    else await request("dns/zones/"+encodeURIComponent(selectedZone)+"/records",{method:"POST",body:JSON.stringify({name:form.get("record_name"),record_type:form.get("record_type"),value:form.get("value")})});
    setNotice(tab==="certificates"?"Certificate request submitted to FreeIPA.":tab==="dns"?(zones.length?"DNS record created.":"DNS zone created."):"Directory entry created.");setShowCreate(false);await refresh();
  }catch(e){setNotice(e instanceof Error?e.message:"Could not save directory entry.");}finally{setBusy(false);}}
  function signOut(){setToken("");setUsers([]);setGroups([]);setZones([]);setRecords([]);setSelectedZone("");setShowCreate(false);setNotice("Signed out. Your short-lived session token was cleared from this page.");}
  const createLabel=tab==="users"?"Add user":tab==="groups"?"Add group":tab==="certificates"?"Request certificate":zones.length?"Add record":"Add zone";
  return <main className="shell"><aside className="sidebar"><div className="brand"><span className="brand-mark">S</span><span>SimpleIPA<small>IDENTITY ADMIN</small></span></div>
    {token&&<nav><button className={tab==="users"?"active":""} onClick={()=>{setTab("users");setShowCreate(false);}}>Users</button><button className={tab==="groups"?"active":""} onClick={()=>{setTab("groups");setShowCreate(false);}}>Groups</button><button className={tab==="dns"?"active":""} onClick={()=>{setTab("dns");setShowCreate(false);}}>DNS</button><button className={tab==="certificates"?"active":""} onClick={()=>{setTab("certificates");setShowCreate(false);}}>Certificates</button></nav>}
    <div className="sidebar-foot">FreeIPA-powered identity management</div></aside>
    <section className="content"><header><div><p className="eyebrow">DIRECTORY</p><h1>{token?(tab==="users"?"Users":tab==="groups"?"Groups":tab==="dns"?"DNS management":"Certificates"):"Administrator sign in"}</h1></div>
      {token&&<div className="header-actions"><button className="secondary" onClick={()=>refresh()} disabled={busy}>Refresh</button><button className="secondary" onClick={signOut}>Sign out</button></div>}</header>
      {!token?<form className="panel auth-panel" onSubmit={signIn}><h2>Sign in to SimpleIPA</h2><p>Use the administrator account configured on your SimpleIPA server.</p>
        <label>Username<input autoComplete="username" required value={username} onChange={e=>setUsername(e.target.value)}/></label>
        <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={e=>setPassword(e.target.value)}/></label>
        <button disabled={busy}>{busy?"Signing in…":"Sign in"}</button><p className="notice" role="status">{notice}</p></form>:<>
        <section className="panel connect"><div><strong>Directory connection</strong><p>Authenticated administrator session. Sessions expire after 15 minutes.</p></div>
          <div className="connect-row"><button className="secondary" onClick={()=>setShowCreate(!showCreate)} disabled={tab==="dns"&&zones.length>0&&!selectedZone}>{showCreate?"Cancel":createLabel}</button></div>
          <p className="notice" role="status">{notice}</p></section>
        {showCreate&&<form className="panel create-form" onSubmit={submitCreate}><h2>{tab==="users"?"Create directory user":tab==="groups"?"Create directory group":tab==="certificates"?"Request a certificate":zones.length?"Create DNS record":"Create DNS zone"}</h2>
          {tab==="users"?<><label>Username<input name="username" required pattern="[a-zA-Z0-9._-]+" maxLength={64}/></label><label>Given name<input name="given_name" required maxLength={128}/></label><label>Family name<input name="family_name" required maxLength={128}/></label><label>Email<input name="email" type="email" maxLength={254}/></label></>
          :tab==="groups"?<><label>Group name<input name="name" required pattern="[a-zA-Z0-9._-]+" maxLength={64}/></label><label>Description<input name="description" maxLength={512}/></label></>
          :tab==="certificates"?<><p>Paste a PEM-encoded PKCS#10 CSR. The private key must stay on the device that generated it.</p><label>FreeIPA principal<input name="principal" required maxLength={255} placeholder="host/server.example.test@EXAMPLE.TEST"/></label><label>Certificate signing request (PEM)<textarea name="csr" required rows={10} maxLength={65536} placeholder="-----BEGIN CERTIFICATE REQUEST-----"/></label></>\n          :zones.length?<><label>Owner name<input name="record_name" required defaultValue="@" maxLength={63}/></label><label>Record type<select name="record_type" defaultValue="A"><option>A</option><option>AAAA</option><option>CNAME</option><option>TXT</option></select></label><label>Value<input name="value" required maxLength={255} placeholder="192.0.2.10 or target.example.test"/></label></>
          :<label>Zone name<input name="zone" required maxLength={253} placeholder="example.test"/></label>}
          <button disabled={busy}>{busy?"Saving…":"Create"}</button></form>}
        {tab==="certificates"?<section className="panel table-panel"><div className="table-heading"><h2>Issued certificates</h2><span>{certificates.length} listed</span></div><table><thead><tr><th>Serial</th><th>Principal</th><th>Status</th><th>Expires</th></tr></thead><tbody>{certificates.map(c=><tr key={c.serial_number}><td>{c.serial_number}</td><td>{c.principal||c.subject||"—"}</td><td>{c.status||"—"}</td><td>{c.expires_on||"—"}</td></tr>)}{certificates.length===0&&<tr><td colSpan={4} className="empty">No certificates returned by FreeIPA.</td></tr>}</tbody></table><p className="notice">Certificate issuance and validity are controlled by FreeIPA Dogtag CA policy. Renewal and revocation are not exposed here.</p></section>:tab==="dns"?<section className="panel table-panel"><div className="table-heading"><h2>DNS zones and records</h2><span>{zones.length} zones</span></div>
          <label>Selected zone<select value={selectedZone} onChange={e=>{setSelectedZone(e.target.value);void loadRecords(e.target.value);}}><option value="">Select a zone</option>{zones.map(z=><option key={z.name} value={z.name}>{z.name}</option>)}</select></label>
          {selectedZone?<table><thead><tr><th>Name</th><th>Type</th><th>Value</th></tr></thead><tbody>{records.map((r,i)=><tr key={r.name+r.record_type+r.value+i}><td>{r.name}</td><td>{r.record_type}</td><td>{r.value}</td></tr>)}{records.length===0&&<tr><td colSpan={3} className="empty">No records found for this zone apex.</td></tr>}</tbody></table>:<p className="empty">Create a DNS zone to begin managing records.</p>}
        </section>:<section className="panel table-panel"><div className="table-heading"><h2>{tab==="users"?"Directory users":"Directory groups"}</h2><span>{tab==="users"?users.length:groups.length} loaded</span></div>
          {tab==="users"?<table><thead><tr><th>Username</th><th>Name</th><th>Email</th></tr></thead><tbody>{users.map(u=><tr key={u.id}><td>{u.username}</td><td>{u.given_name} {u.family_name}</td><td>{u.email||"—"}</td></tr>)}{users.length===0&&<tr><td colSpan={3} className="empty">No users loaded.</td></tr>}</tbody></table>
          :<table><thead><tr><th>Group</th><th>Description</th></tr></thead><tbody>{groups.map(g=><tr key={g.id}><td>{g.name}</td><td>{g.description||"—"}</td></tr>)}{groups.length===0&&<tr><td colSpan={2} className="empty">No groups loaded.</td></tr>}</tbody></table>}
        </section>}
      </>}
      <p className="disclaimer">Directory changes are sent to the authenticated API. FreeIPA requires Kerberos mutual authentication over verified HTTPS. DNS deletion and certificate revocation are not available in this release. Private keys never leave the requesting device.</p>
    </section></main>;
}
