import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import type { FormEvent } from "react";
import "./styles.css";

type ApiIcp = { id: string; name: string; industry: string; company_size: string; target_roles: string };
type Search = { id: string; icp_id?: string | null; query: string; location: string; status: string; leads_found?: number; contacted?: number; rejected?: number; fresh_leads?: number };
type Lead = { id: number; name: string; role: string; company: string; initials: string; color: string; industry: string; size: string; location: string; score: number; stage: "Discovery" | "First contact" | "Qualification"; email: string; linkedin: string; date: string };
const API_URL = import.meta.env.VITE_API_URL ?? "";
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { ...init, headers: { "Content-Type": "application/json" } });
  if (!response.ok) throw new Error(`${response.status} ${await response.text()}`);
  return response.json() as Promise<T>;
}

const leads: Lead[] = [
  { id: 1, name: "Sofia Ramirez", role: "VP of Revenue Operations", company: "Northstar Labs", initials: "SR", color: "lilac", industry: "B2B SaaS · Analytics", size: "51–200 employees", location: "Austin, TX", score: 96, stage: "First contact", email: "sofia@northstarlabs.io", linkedin: "linkedin.com/in/sofia-ramirez", date: "Today, 10:42 AM" },
  { id: 2, name: "Marcus Chen", role: "Founder & CEO", company: "Layerwise", initials: "MC", color: "mint", industry: "B2B SaaS · DevTools", size: "11–50 employees", location: "San Francisco, CA", score: 92, stage: "Qualification", email: "marcus@layerwise.dev", linkedin: "linkedin.com/in/marcus-chen", date: "Yesterday" },
  { id: 3, name: "Priya Patel", role: "Chief Operating Officer", company: "Verity Health", initials: "PP", color: "peach", industry: "HealthTech", size: "201–500 employees", location: "New York, NY", score: 89, stage: "Discovery", email: "priya@verity.health", linkedin: "linkedin.com/in/priyapatel", date: "—" },
  { id: 4, name: "James Okafor", role: "Head of Sales", company: "Formstacker", initials: "JO", color: "blue", industry: "B2B SaaS · Productivity", size: "51–200 employees", location: "Chicago, IL", score: 87, stage: "First contact", email: "james@formstacker.com", linkedin: "linkedin.com/in/james-okafor", date: "Oct 16, 2:18 PM" },
  { id: 5, name: "Elena Fischer", role: "Director of Growth", company: "Nimble Commerce", initials: "EF", color: "rose", industry: "E-commerce", size: "51–200 employees", location: "Denver, CO", score: 84, stage: "Discovery", email: "elena@nimblecommerce.co", linkedin: "linkedin.com/in/elena-fischer", date: "—" },
  { id: 6, name: "Daniel Kim", role: "VP of Marketing", company: "Pylon AI", initials: "DK", color: "yellow", industry: "Artificial Intelligence", size: "11–50 employees", location: "Seattle, WA", score: 82, stage: "First contact", email: "daniel@pylon.ai", linkedin: "linkedin.com/in/daniel-kim", date: "Oct 15, 9:06 AM" },
];
const discoveries: Discovery[] = [
  { name: "Series A SaaS revenue teams", meta: "B2B SaaS · 50–200 employees", location: "North America", count: 48, contacted: 31, rejected: 4, fresh: 12, date: "Updated 2h ago", color: "purple", leadIds: [1, 2, 4, 6] },
  { name: "Modern healthtech operators", meta: "HealthTech · 100–500 employees", location: "United States", count: 32, contacted: 18, rejected: 3, fresh: 8, date: "Updated yesterday", color: "green", leadIds: [3] },
  { name: "Product-led growth companies", meta: "B2B software · 10–100 employees", location: "United States", count: 27, contacted: 16, rejected: 2, fresh: 5, date: "Updated Oct 14", color: "orange", leadIds: [2, 6] },
];
type Discovery = { name: string; meta: string; location: string; count: number; contacted: number; rejected: number; fresh: number; date: string; color: string; leadIds: number[] };
type IcpProfile = { id: string; name: string; industry: string; companySize: string; targetRoles: string };
const starterProfiles: IcpProfile[] = [
  { id: "icp-saas", name: "Series A SaaS revenue teams", industry: "B2B SaaS", companySize: "50–200 employees", targetRoles: "VP Revenue, Head of Growth, Sales leaders" },
  { id: "icp-health", name: "Modern healthtech operators", industry: "HealthTech", companySize: "100–500 employees", targetRoles: "COO, VP Operations, Clinical leaders" },
  { id: "icp-plg", name: "Product-led growth companies", industry: "B2B software", companySize: "10–100 employees", targetRoles: "Head of Product, Growth leaders" },
];
type Page = "overview" | "profiles" | "discoveries" | "discovery-detail" | "detail";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function App() {
  const [page, setPage] = useState<Page>("overview");
  const [previousPage, setPreviousPage] = useState<"overview" | "discovery-detail">("overview");
  const [selectedLead, setSelectedLead] = useState<Lead>(leads[0]);
  const [selectedDiscovery, setSelectedDiscovery] = useState<Discovery>(discoveries[0]);
  const [searches, setSearches] = useState<Search[]>([]);
  const [icpProfiles, setIcpProfiles] = useState<IcpProfile[]>(() => {
    try { return JSON.parse(localStorage.getItem("dealcompass.icpProfiles") ?? "null") ?? starterProfiles; }
    catch { return starterProfiles; }
  });
  const [createdRuns, setCreatedRuns] = useState<Discovery[]>([]);
  const [locationProfile, setLocationProfile] = useState<IcpProfile | null>(null);
  const [query, setQuery] = useState("");
  const [industry, setIndustry] = useState("");
  const [companySize, setCompanySize] = useState("");
  const [targetRoles, setTargetRoles] = useState("");
  const [toast, setToast] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const load = () => {
    api<Search[]>("/api/v1/searches").then(setSearches).catch(() => setSearches([]));
    api<ApiIcp[]>("/api/v1/icps")
      .then(rows => {
        if (rows.length > 0) {
          setIcpProfiles([
            ...starterProfiles,
            ...rows.map(r => ({ id: r.id, name: r.name, industry: r.industry, companySize: r.company_size, targetRoles: r.target_roles })),
          ]);
        }
      })
      .catch(() => {});
  };
  useEffect(() => { load(); }, []);
  useEffect(() => { localStorage.setItem("dealcompass.icpProfiles", JSON.stringify(icpProfiles)); }, [icpProfiles]);

  const allDiscoveries: Discovery[] = [
    ...discoveries,
    ...createdRuns,
    ...searches.map(s => {
      const profile = icpProfiles.find(p => p.id === s.icp_id || s.query.startsWith(p.name));
      return {
        name: profile?.name ?? s.query,
        meta: profile ? [profile.industry, profile.companySize, profile.targetRoles].filter(Boolean).join(" · ") : "ICP from your targeting criteria",
        location: s.location,
        count: s.leads_found ?? 0,
        contacted: s.contacted ?? 0,
        rejected: s.rejected ?? 0,
        fresh: s.fresh_leads ?? 0,
        date: s.status,
        color: "purple",
        leadIds: [],
      };
    }),
  ];

  async function createProfile(event: FormEvent) {
    event.preventDefault();
    let createdId = `icp-${Date.now()}`;
    try {
      const saved = await api<ApiIcp>("/api/v1/icps", {
        method: "POST",
        body: JSON.stringify({ name: query, industry, company_size: companySize, target_roles: targetRoles }),
      });
      createdId = saved.id;
    } catch {
      // Fallback to localStorage ID when offline
    }
    const profile = { id: createdId, name: query, industry, companySize, targetRoles };
    setIcpProfiles(current => [...current, profile]);
    setCreateOpen(false);
    setPage("profiles");
    setToast("ICP created");
    setTimeout(() => setToast(""), 2500);
  }

  async function launchLocationSearch(profile: IcpProfile, searchLocation: string) {
    try {
      const description = [profile.name, profile.industry, profile.companySize, profile.targetRoles && `Roles: ${profile.targetRoles}`].filter(Boolean).join(" · ");
      const icpId = UUID_RE.test(profile.id) ? profile.id : null;
      await api<Search>("/api/v1/searches", { method: "POST", body: JSON.stringify({ query: description, location: searchLocation, icp_id: icpId }) });
      const updatedSearches = await api<Search[]>("/api/v1/searches").catch(() => null);
      if (updatedSearches) {
        setSearches(updatedSearches);
      } else {
        const run: Discovery = { name: profile.name, meta: [profile.industry, profile.companySize, profile.targetRoles].filter(Boolean).join(" · "), location: searchLocation, count: 0, contacted: 0, rejected: 0, fresh: 0, date: "Just created", color: "purple", leadIds: [] };
        setCreatedRuns(current => [run, ...current]);
      }
      setLocationProfile(null);
      setPage("discoveries");
      setToast(`Discovery started in ${searchLocation}`);
      setTimeout(() => setToast(""), 2500);
    } catch (e) {
      setToast(`Could not start discovery: ${String(e)}`);
      setTimeout(() => setToast(""), 3500);
    }
  }

  function openLead(lead: Lead, from: "overview" | "discovery-detail") {
    setSelectedLead(lead);
    setPreviousPage(from);
    setPage("detail");
  }

  function openDiscovery(discovery: Discovery) {
    setSelectedDiscovery(discovery);
    setPage("discovery-detail");
  }

  function openCreateModal() {
    setQuery("");
    setIndustry("");
    setCompanySize("");
    setTargetRoles("");
    setCreateOpen(true);
  }

  const leadDiscovery = allDiscoveries.find(d => d.leadIds.includes(selectedLead.id)) ?? selectedDiscovery;

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><span/><span/><span/></div><span>dealcompass</span></div>
      <div className="nav-label">WORKSPACE</div>
      <nav>
        <button className={page === "overview" ? "nav-item active" : "nav-item"} onClick={() => setPage("overview")}><Icon name="grid"/>Overview</button>
        <button className={page === "profiles" ? "nav-item active" : "nav-item"} onClick={() => setPage("profiles")}><Icon name="target"/>ICP<span className="nav-count">{icpProfiles.length}</span></button>
        <button className={page === "discoveries" || page === "discovery-detail" ? "nav-item active" : "nav-item"} onClick={() => setPage("discoveries")}><Icon name="spark"/>ICP discoveries<span className="nav-count">{allDiscoveries.length}</span></button>
      </nav>
    </aside>

    <main className="main-area">
      <header className="topbar">
        <div className="breadcrumbs">
          <strong>{page === "overview" ? "Overview" : page === "profiles" ? "ICP" : page === "discoveries" ? "ICP discoveries" : page === "discovery-detail" ? selectedDiscovery.name : selectedLead.name}</strong>
        </div>
      </header>
      {page === "overview" && <Overview leads={leads} profilesCount={icpProfiles.length} discoveriesCount={allDiscoveries.length} openLead={lead => openLead(lead, "overview")} goDiscoveries={() => setPage("discoveries")} openCreate={openCreateModal} />}
      {page === "profiles" && <Profiles profiles={icpProfiles} discoveryCounts={new Map(icpProfiles.map(p => [p.name, allDiscoveries.filter(d => d.name === p.name).length]))} openCreate={openCreateModal} onRunSearch={profile => setLocationProfile(profile)} />}
      {page === "discoveries" && <Discoveries discoveries={allDiscoveries} openDiscovery={openDiscovery} openCreate={() => setPage("profiles")} />}
      {page === "discovery-detail" && <DiscoveryDetail discovery={selectedDiscovery} back={() => setPage("discoveries")} openLead={lead => openLead(lead, "discovery-detail")} />}
      {page === "detail" && <Detail lead={selectedLead} back={() => setPage(previousPage)} backLabel={previousPage === "overview" ? "Back to overview" : `Back to ${selectedDiscovery.name}`} discovery={leadDiscovery} />}
    </main>
    {createOpen && <CreateModal close={() => setCreateOpen(false)} query={query} setQuery={setQuery} industry={industry} setIndustry={setIndustry} companySize={companySize} setCompanySize={setCompanySize} targetRoles={targetRoles} setTargetRoles={setTargetRoles} createProfile={createProfile} />}
    {locationProfile && <LocationDiscoveryModal profile={locationProfile} close={() => setLocationProfile(null)} onStart={launchLocationSearch} />}
    {toast && <div className="toast"><span>✓</span>{toast}</div>}
  </div>;
}

type DiscoveryFormProps = { close: () => void; query: string; setQuery: (v: string) => void; industry: string; setIndustry: (v: string) => void; companySize: string; setCompanySize: (v: string) => void; targetRoles: string; setTargetRoles: (v: string) => void; createProfile: (e: FormEvent) => void };
function CreateModal(props: DiscoveryFormProps) {
  return <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) props.close(); }}>
    <section className="create-modal form-only-modal">
      <header className="modal-header">
        <div>
          <span className="modal-mark"><Icon name="target"/></span>
          <div>
            <h2>Create an ICP</h2>
            <p>Define your ideal customer once, then search it in different locations.</p>
          </div>
        </div>
        <button className="modal-close" onClick={props.close}>×</button>
      </header>
      <form className="discovery-form" onSubmit={props.createProfile}>
        <label>ICP name<input value={props.query} onChange={e => props.setQuery(e.target.value)} placeholder="e.g. Growth-stage fintechs" required/></label>
        <div className="form-two-col">
          <label>Industry<input value={props.industry} onChange={e => props.setIndustry(e.target.value)} placeholder="e.g. B2B SaaS, Fintech"/></label>
          <label>Company size
            <select value={props.companySize} onChange={e => props.setCompanySize(e.target.value)}>
              <option value="">Any company size</option>
              <option>1–10 employees</option>
              <option>11–50 employees</option>
              <option>20–100 employees</option>
              <option>50–200 employees</option>
              <option>201–500 employees</option>
              <option>500+ employees</option>
            </select>
          </label>
        </div>
        <label>Target roles<input value={props.targetRoles} onChange={e => props.setTargetRoles(e.target.value)} placeholder="e.g. VP Sales, Head of Growth"/></label>
        <div className="form-footer">
          <button type="button" className="button secondary" onClick={props.close}>Cancel</button>
          <button className="button primary"><Icon name="plus"/>Create ICP</button>
        </div>
      </form>
    </section>
  </div>;
}

function Overview({ leads, profilesCount, discoveriesCount, openLead, goDiscoveries, openCreate }: { leads: Lead[]; profilesCount: number; discoveriesCount: number; openLead: (l: Lead) => void; goDiscoveries: () => void; openCreate: () => void }) {
  const qualifiedCount = leads.filter(l => l.stage === "Qualification").length;
  return <div className="content overview-content">
    <div className="page-heading">
      <div>
        <div className="eyebrow">OVERVIEW</div>
        <h1>Pipeline overview</h1>
        <p>Summary of your ICP, active location discoveries, and recent leads.</p>
      </div>
      <div className="heading-actions">
        <button className="button primary" onClick={openCreate}><Icon name="plus"/>New ICP</button>
      </div>
    </div>
    <section className="stats-grid">
      <Stat title="ICP" value={String(profilesCount)} foot="Saved targeting definitions" icon="target" color="lavender" />
      <Stat title="Active discoveries" value={String(discoveriesCount)} foot="Location-scoped runs" icon="spark" color="blue" />
      <Stat title="Leads discovered" value={String(leads.length)} foot="Prospects in workspace" icon="users" color="green" />
      <Stat title="In qualification" value={String(qualifiedCount)} foot="Active opportunities" icon="message" color="orange" />
    </section>
    <section className="panel recent-panel">
      <div className="panel-head">
        <div>
          <h2>Recent leads</h2>
          <p>Your latest discovered prospects</p>
        </div>
        <button className="link-button" onClick={goDiscoveries}>View discoveries <span>→</span></button>
      </div>
      <div className="table-wrap"><LeadTable leads={leads.slice(0, 4)} openLead={openLead}/></div>
    </section>
  </div>;
}

function Stat({ title, value, foot, icon, color }: { title: string; value: string; foot: string; icon: string; color: string }) {
  return <div className="stat-card">
    <div className="stat-top">
      <span>{title}</span>
      <span className={`stat-icon ${color}`}><Icon name={icon}/></span>
    </div>
    <div className="stat-bottom">
      <div>
        <strong>{value}</strong>
        <div className="stat-foot">{foot}</div>
      </div>
    </div>
  </div>;
}

function Profiles({ profiles, discoveryCounts, openCreate, onRunSearch }: { profiles: IcpProfile[]; discoveryCounts: Map<string, number>; openCreate: () => void; onRunSearch: (profile: IcpProfile) => void }) {
  return <div className="content profiles-content">
    <div className="page-heading">
      <div>
        <div className="eyebrow">TARGETING</div>
        <h1>ICP</h1>
        <p>Reusable definitions of your ideal customers. Discover them in as many locations as you need.</p>
      </div>
      <button className="button primary" onClick={openCreate}><Icon name="plus"/>Create ICP</button>
    </div>
    <div className="section-title"><div><h2>Saved ICP</h2><span className="count-pill">{profiles.length}</span></div></div>
    <section className="panel profile-list-panel">
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>ICP</th><th>INDUSTRY</th><th>COMPANY SIZE</th><th>TARGET ROLES</th><th>DISCOVERIES</th><th/></tr>
          </thead>
          <tbody>
            {profiles.map(profile => <tr key={profile.id}>
              <td><div className="discovery-name-cell"><span className="discovery-icon purple"><Icon name="target"/></span><span><strong>{profile.name}</strong><small>Reusable targeting criteria</small></span></div></td>
              <td>{profile.industry || "Any industry"}</td>
              <td>{profile.companySize || "Any size"}</td>
              <td>{profile.targetRoles || "Any decision maker"}</td>
              <td><span className="count-pill">{discoveryCounts.get(profile.name) ?? 0} locations</span></td>
              <td><button className="button secondary profile-search-button" onClick={() => onRunSearch(profile)}><Icon name="pin"/>Discover in a location</button></td>
            </tr>)}
          </tbody>
        </table>
      </div>
    </section>
  </div>;
}

function LocationDiscoveryModal({ profile, close, onStart }: { profile: IcpProfile; close: () => void; onStart: (p: IcpProfile, location: string) => void }) {
  const [searchLocation, setSearchLocation] = useState("");
  return <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) close(); }}>
    <section className="create-modal form-only-modal location-modal">
      <header className="modal-header">
        <div>
          <span className="modal-mark"><Icon name="pin"/></span>
          <div>
            <h2>Start an ICP discovery</h2>
            <p>Search this saved ICP in a specific location.</p>
          </div>
        </div>
        <button className="modal-close" onClick={close}>×</button>
      </header>
      <form className="discovery-form" onSubmit={e => { e.preventDefault(); onStart(profile, searchLocation); }}>
        <div className="selected-profile">
          <span className="discovery-icon purple"><Icon name="target"/></span>
          <div>
            <small>REUSABLE ICP</small>
            <b>{profile.name}</b>
            <span>{[profile.industry, profile.companySize, profile.targetRoles].filter(Boolean).join(" · ")}</span>
          </div>
        </div>
        <label>Search location<input autoFocus value={searchLocation} onChange={e => setSearchLocation(e.target.value)} placeholder="e.g. Colombia, New York, DACH" required/></label>
        <div className="form-footer">
          <button type="button" className="button secondary" onClick={close}>Cancel</button>
          <button className="button primary"><Icon name="spark"/>Search this location</button>
        </div>
      </form>
    </section>
  </div>;
}

function Discoveries({ discoveries: allDiscoveries, openDiscovery, openCreate }: { discoveries: Discovery[]; openDiscovery: (d: Discovery) => void; openCreate: () => void }) {
  return <div className="content discoveries-content">
    <div className="page-heading">
      <div>
        <div className="eyebrow">PROSPECTING</div>
        <h1>ICP discoveries</h1>
        <p>Explore location-based searches created from reusable ICP.</p>
      </div>
      <button className="button primary" onClick={openCreate}><Icon name="target"/>Choose ICP</button>
    </div>
    <div className="section-title">
      <div><h2>Your discoveries</h2><span className="count-pill">{allDiscoveries.length}</span></div>
    </div>
    <section className="panel discovery-list-panel">
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>ICP</th><th>SEARCH LOCATION</th><th>LEADS FOUND</th><th>CONTACTED</th><th>REJECTED</th><th>NEW LEADS</th><th>LAST UPDATED</th></tr>
          </thead>
          <tbody>
            {allDiscoveries.map((d, i) => <tr key={`${d.name}-${i}`} onClick={() => openDiscovery(d)}>
              <td><div className="discovery-name-cell"><span className={`discovery-icon ${d.color}`}><Icon name="target"/></span><span><strong>{d.name}</strong><small>{d.meta}</small></span></div></td>
              <td><span className="location-cell"><Icon name="pin"/>{d.location}</span></td>
              <td><b className="table-metric">{d.count}</b></td>
              <td><b className="table-metric">{d.contacted}</b></td>
              <td><b className="table-metric rejected-metric">{d.rejected}</b></td>
              <td><span className="fresh-pill">+{d.fresh}</span></td>
              <td><span className="activity-text">◷ &nbsp;{d.date}</span></td>
            </tr>)}
          </tbody>
        </table>
      </div>
    </section>
  </div>;
}

function DiscoveryDetail({ discovery, back, openLead }: { discovery: Discovery; back: () => void; openLead: (l: Lead) => void }) {
  const [filter, setFilter] = useState("All leads");
  const discoveryLeads = leads.filter(l => discovery.leadIds.includes(l.id));
  const shown = discoveryLeads.filter(l => filter === "All leads" || l.stage === filter);
  return <div className="content discovery-detail-content">
    <button className="back-link" onClick={back}>← &nbsp;All ICP discoveries</button>
    <div className="page-heading discovery-detail-heading">
      <div>
        <div className="eyebrow">ICP DISCOVERY · {discovery.location.toUpperCase()}</div>
        <h1>{discovery.name}</h1>
        <p>{discovery.meta}</p>
      </div>
    </div>
    <section className="discovery-stats">
      <div className="discovery-stat"><span className="discovery-stat-icon purple-stat"><Icon name="users"/></span><div><small>Leads found</small><strong>{discovery.count}</strong><span className="stat-note">Across this discovery</span></div></div>
      <div className="discovery-stat"><span className="discovery-stat-icon blue-stat"><Icon name="send"/></span><div><small>Contacted</small><strong>{discovery.contacted}</strong><span className="stat-note">{Math.round(discovery.contacted / Math.max(1, discovery.count) * 100)}% of leads found</span></div></div>
      <div className="discovery-stat"><span className="discovery-stat-icon red-stat"><Icon name="inbox"/></span><div><small>Rejected</small><strong>{discovery.rejected}</strong><span className="stat-note">Excluded from outreach</span></div></div>
      <div className="discovery-stat"><span className="discovery-stat-icon green-stat"><Icon name="message"/></span><div><small>In qualification</small><strong>{discoveryLeads.filter(l => l.stage === "Qualification").length}</strong><span className="stat-note">Active opportunities</span></div></div>
    </section>
    <section className="panel leads-panel discovery-leads-panel">
      <div className="leads-heading">
        <div>
          <h2>Leads in this discovery</h2>
          <p>People matching “{discovery.name}” in {discovery.location}</p>
        </div>
      </div>
      <div className="lead-controls">
        <div className="filter-tabs">
          {["All leads", "Discovery", "First contact", "Qualification"].map(t => <button className={filter === t ? "filter-active" : ""} key={t} onClick={() => setFilter(t)}>{t}{t === "All leads" && <span>{discoveryLeads.length}</span>}</button>)}
        </div>
      </div>
      <div className="table-wrap"><LeadTable leads={shown} openLead={openLead}/></div>
      <div className="table-footer"><span>Showing <b>{shown.length}</b> of <b>{discoveryLeads.length}</b> leads</span></div>
    </section>
  </div>;
}

function LeadTable({ leads: rows, openLead }: { leads: Lead[]; openLead: (l: Lead) => void }) {
  return <table>
    <thead>
      <tr><th>PERSON</th><th>COMPANY</th><th>ICP MATCH</th><th>PIPELINE STAGE</th><th>LAST ACTIVITY</th></tr>
    </thead>
    <tbody>
      {rows.map(lead => <tr key={lead.id} onClick={() => openLead(lead)}>
        <td><div className="person-cell"><div className={`avatar ${lead.color}`}>{lead.initials}</div><div><strong>{lead.name}</strong><small>{lead.role}</small></div></div></td>
        <td><div className="company-cell"><span className="company-logo">{lead.company.slice(0, 1)}</span><div><strong>{lead.company}</strong><small>{lead.industry}</small></div></div></td>
        <td><div className="score-cell"><span className="score-track"><i style={{ width: `${lead.score}%` }}/></span><b>{lead.score}%</b></div></td>
        <td><Stage stage={lead.stage}/></td>
        <td><span className="activity-text">{lead.date}</span></td>
      </tr>)}
    </tbody>
  </table>;
}
function Stage({ stage }: { stage: Lead["stage"] }) { return <span className={`stage stage-${stage.toLowerCase().replace(" ", "-")}`}><i/>{stage}</span>; }

function Detail({ lead, back, backLabel, discovery }: { lead: Lead; back: () => void; backLabel: string; discovery: Discovery }) {
  return <div className="content detail-content">
    <button className="back-link" onClick={back}>← &nbsp;{backLabel}</button>
    <div className="detail-heading">
      <div className="detail-profile">
        <div className={`avatar detail-avatar ${lead.color}`}>{lead.initials}</div>
        <div>
          <div className="detail-name-line"><h1>{lead.name}</h1></div>
          <p>{lead.role} <span>at</span> <b>{lead.company}</b></p>
          <div className="detail-tags">
            <span className="tag">{lead.industry}</span>
            <span className="tag">{lead.location}</span>
            <span className="tag match-tag"><Icon name="spark"/>{lead.score}% ICP match</span>
          </div>
        </div>
      </div>
    </div>
    <div className="pipeline">
      <div className="pipeline-step done"><span className="step-check">✓</span><span>Discovery</span></div>
      <div className="pipeline-line done-line"/>
      <div className={`pipeline-step ${lead.stage === "Discovery" ? "current" : "done"}`}><span className="step-check">{lead.stage === "Discovery" ? "2" : "✓"}</span><span>First contact</span></div>
      <div className={`pipeline-line ${lead.stage === "Qualification" ? "done-line" : ""}`}/>
      <div className={`pipeline-step ${lead.stage === "Qualification" ? "current" : ""}`}><span className="step-check">3</span><span>Qualification</span></div>
    </div>
    <div className="detail-layout">
      <section className="panel info-panel">
        <div className="panel-head">
          <div><h2>Lead overview</h2><p>Key details about this prospect</p></div>
        </div>
        <div className="info-grid">
          <Info label="Work email" value={lead.email} href={`mailto:${lead.email}`} icon="mail"/>
          <Info label="LinkedIn" value={lead.linkedin} href={`https://${lead.linkedin}`} icon="external"/>
          <Info label="Company size" value={lead.size} icon="users"/>
          <Info label="Location" value={lead.location} icon="pin"/>
          <Info label="Industry" value={lead.industry} icon="building"/>
          <Info label="Lead source" value={discovery.name} icon="spark"/>
        </div>
      </section>
      <section className="panel fit-panel">
        <div className="panel-head">
          <div><h2>Why this lead matches</h2><p>Signals aligned with your ideal customer profile</p></div>
          <span className="match-score">{lead.score}% match</span>
        </div>
        <div className="fit-signals">
          <span><i>✓</i> Company size fits your target ({lead.size})</span>
          <span><i>✓</i> Industry match ({lead.industry})</span>
          <span><i>✓</i> Decision maker role ({lead.role})</span>
          <span><i>✓</i> Located in {lead.location}</span>
        </div>
      </section>
    </div>
  </div>;
}
function Info({ label, value, href, icon }: { label: string; value: string; href?: string; icon: string }) {
  return <div className="info-item">
    <span className="info-icon"><Icon name={icon}/></span>
    <div>
      <small>{label}</small>
      {href ? <a href={href} target="_blank" rel="noreferrer" className="info-link">{value}</a> : <b>{value}</b>}
    </div>
  </div>;
}

function Icon({ name }: { name: string }) {
  const common = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  const paths: Record<string, React.ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    spark: <><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-2-5.8L4 11l6-2.2L12 3Z"/><path d="m19 14 .8 2.2L22 17l-2.2.8L19 20l-.8-2.2L16 17l2.2-.8L19 14Z"/></>,
    users: <><path d="M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2"/><circle cx="9.5" cy="7" r="4"/><path d="M20 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></>,
    building: <><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M9 21v-4h6v4M8 7h1m6 0h1M8 11h1m6 0h1"/></>,
    mail: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></>,
    inbox: <><path d="M4 4h16l2 11h-6l-2 3h-4l-2-3H2L4 4Z"/><path d="M2 15h6l2 3h4l2-3h6"/></>,
    plus: <><path d="M12 5v14M5 12h14"/></>,
    send: <><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></>,
    message: <><path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5Z"/></>,
    target: <><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/></>,
    external: <><path d="M14 3h7v7m0-7L10 14"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></>,
    pin: <><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2"/></>,
  };
  return <svg {...common}>{paths[name] ?? paths.spark}</svg>;
}

createRoot(document.getElementById("root")!).render(<App/>);
