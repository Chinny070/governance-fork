import { WalletProvider } from "./lib/wallet";
import { useRoute, navigate, type Route } from "./lib/router";
import { Header, WalletNotice } from "./components/Header";
import { Explorer } from "./views/Explorer";
import { ProposalWorkspace } from "./views/ProposalWorkspace";
import { BuildFlow } from "./views/BuildFlow";
import { BondsPanel } from "./views/BondsPanel";
import { AboutPanel } from "./views/AboutPanel";
import { REPO_URL } from "./lib/contract";

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

  return (
    <WalletProvider>
      <Header tab={activeTab(route)} />
      <div className="wrap page">
        <WalletNotice />
        <Body route={route} />

        <footer className="footer">
          <span>Governance Fork · GenLayer StudioNet</span>
          <a href={REPO_URL} target="_blank" rel="noreferrer">
            Source
          </a>
          <button className="link" onClick={() => navigate({ name: "about" })}>
            How it works
          </button>
        </footer>
      </div>
    </WalletProvider>
  );
}
