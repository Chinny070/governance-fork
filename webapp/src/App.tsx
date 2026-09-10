import { WalletProvider } from "./lib/wallet";
import { navigate, useRoute, type Route } from "./lib/router";
import { WalletBar, WalletNotice } from "./components/WalletBar";
import { Explorer } from "./views/Explorer";
import { ProposalWorkspace } from "./views/ProposalWorkspace";
import { BuildFlow } from "./views/BuildFlow";
import { BondsPanel } from "./views/BondsPanel";
import { AboutPanel } from "./views/AboutPanel";
import { REPO_URL } from "./lib/contract";

const TABS: { name: Route["name"]; label: string }[] = [
  { name: "explore", label: "Explore" },
  { name: "build", label: "Build" },
  { name: "bonds", label: "Bonds" },
  { name: "about", label: "About" },
];

function Body({ route }: { route: Route }) {
  switch (route.name) {
    case "root":
      return <ProposalWorkspace kind="root" id={route.id} />;
    case "fork":
      return <ProposalWorkspace kind="fork" id={route.id} />;
    case "build":
      return <BuildFlow />;
    case "bonds":
      return <BondsPanel />;
    case "about":
      return <AboutPanel />;
    default:
      return <Explorer />;
  }
}

function activeTab(route: Route): Route["name"] {
  if (route.name === "root" || route.name === "fork") return "explore";
  return route.name;
}

export default function App() {
  const route = useRoute();
  const tab = activeTab(route);

  return (
    <WalletProvider>
      <div className="app">
        <header className="topbar">
          <button
            className="brand"
            style={{ border: "none", background: "none", padding: 0, textAlign: "left" }}
            onClick={() => navigate({ name: "explore" })}
          >
            <span className="title">Governance Fork</span>
            <span className="tag">Don't vote YES or NO. Change the proposal.</span>
          </button>
          <span className="spacer" />
          <WalletBar />
        </header>

        <nav className="tabs">
          {TABS.map((t) => (
            <button
              key={t.name}
              className={tab === t.name ? "active" : ""}
              onClick={() => navigate({ name: t.name } as Route)}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <WalletNotice />

        <main style={{ marginTop: 14 }}>
          <Body route={route} />
        </main>

        <footer className="foot">
          <span>GenLayer StudioNet · Intelligent Contract</span>
          <a href={REPO_URL} target="_blank" rel="noreferrer">
            Source
          </a>
          <button
            className="ghost tiny"
            style={{ padding: 0, border: "none" }}
            onClick={() => navigate({ name: "about" })}
          >
            About &amp; lifecycle
          </button>
        </footer>
      </div>
    </WalletProvider>
  );
}
