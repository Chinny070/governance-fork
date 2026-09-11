import {
  CONTRACT_ADDRESS,
  CONTRACT_SOURCE_COMMIT,
  CONTRACT_SOURCE_SHA256,
  REPO_URL,
  STUDIONET,
  explorerAddressUrl,
} from "../lib/contract";
import { getConstants } from "../lib/api";
import { formatGen, shortAddr } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";
import { DL, Row, SectionHead, Tag } from "../components/ui";
import { Mark } from "../components/Logo";

const FLOW: [string, string, "" | "accent" | "fork"][] = [
  ["Proposal", "A DAO imports a real governance proposal + its authoritative URL", ""],
  ["Intent", "The proposer states objective, scope, constraints, mutable vs immutable dimensions", ""],
  ["Evidence", "Community web pages fetched on-chain with gl.nondet.web.render, then frozen", ""],
  ["GenLayer adjudication", "Validators reach semantic consensus: does this faithfully represent the intent?", "accent"],
  ["Fork", "Anyone builds an alternative that keeps the intent and declares its delta", "fork"],
  ["Challenge", "Assert a dimension is wrong → re-adjudication, not a vote", "fork"],
  ["Finality", "The proposal or fork freezes with a provable, bonded verdict", ""],
];

function ForkDiagram() {
  return (
    <svg
      width="320"
      height="150"
      viewBox="0 0 320 150"
      fill="none"
      aria-hidden="true"
      style={{ maxWidth: "100%" }}
    >
      <text x="0" y="14" fontFamily="var(--mono)" fontSize="10" fill="var(--ink-3)">
        YES / NO
      </text>
      <line x1="16" y1="28" x2="16" y2="120" stroke="var(--line-3)" strokeWidth="1.5" />
      <circle cx="16" cy="28" r="3.5" fill="var(--ink-2)" />
      <text x="30" y="46" fontFamily="var(--mono)" fontSize="10" fill="var(--ink-4)">
        pass
      </text>
      <text x="30" y="112" fontFamily="var(--mono)" fontSize="10" fill="var(--ink-4)">
        reject
      </text>
      <circle cx="16" cy="120" r="3.5" fill="var(--ink-4)" />

      <text x="150" y="14" fontFamily="var(--mono)" fontSize="10" fill="var(--ink-3)">
        GOVERNANCE FORK
      </text>
      <line x1="166" y1="28" x2="166" y2="130" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="166" cy="28" r="3.5" fill="var(--blue)" />
      <path d="M166 54 H222 Q238 54 238 70 V84" stroke="var(--coral)" strokeWidth="1.5" />
      <circle cx="238" cy="86" r="3.5" fill="var(--coral)" />
      <path d="M166 82 H210" stroke="var(--coral)" strokeWidth="1.5" opacity="0.7" />
      <circle cx="212" cy="82" r="3" fill="var(--coral)" opacity="0.7" />
      <path d="M238 100 H286 Q300 100 300 114 V124" stroke="var(--coral)" strokeWidth="1.5" opacity="0.55" />
      <circle cx="300" cy="126" r="3" fill="var(--coral)" opacity="0.55" />
      <circle cx="166" cy="130" r="3.5" fill="currentColor" />
    </svg>
  );
}

export function AboutPanel() {
  const consts = useAsync(getConstants, []);

  return (
    <div className="stack-lg">
      <section className="hero" style={{ marginBottom: 0 }}>
        <p className="eyebrow">How it works</p>
        <h1 className="display" style={{ maxWidth: "18ch" }}>
          Disagreement should <span className="em">branch</span>, not just tally.
        </h1>
        <p className="lede">
          Governance Fork replaces the up/down vote with a lineage of proposals.
          Each version is judged by an on-chain LLM adjudication for whether it
          stays faithful to the original intent — and every judgement can be
          challenged into a re-adjudication.
        </p>
        <div className="row" style={{ marginTop: 22 }}>
          <button className="primary" onClick={() => navigate({ name: "build" })}>
            Build a proposal
          </button>
          <button onClick={() => navigate({ name: "explore" })}>
            Explore the registry
          </button>
        </div>
      </section>

      <div className="section">
        <SectionHead eyebrow="Mechanism" title="One proposal, many descendants" />
        <div className="flow">
          {FLOW.map(([k, d, kind], i) => (
            <div key={k} style={{ width: "100%" }}>
              <div className={`step ${kind}`}>
                <span className="mk" />
                <span className="k">{k}</span>
                <span className="d">{d}</span>
              </div>
              {i < FLOW.length - 1 && <div className="pipe" />}
            </div>
          ))}
        </div>
      </div>

      <div className="section">
        <SectionHead eyebrow="Why" title="Not yes / no" />
        <div className="row" style={{ gap: 40, alignItems: "flex-start" }}>
          <ForkDiagram />
          <p className="muted" style={{ maxWidth: "38ch" }}>
            A vote collapses a rich proposal into one bit. A fork keeps it
            editable: the objection becomes a concrete alternative, the
            alternative is adjudicated for faithfulness, and the result is a tree
            you can inspect — not a number.
          </p>
        </div>
      </div>

      <div className="section">
        <SectionHead eyebrow="Contract" title="Production deployment" />
        <DL>
          <Row k="Address">
            <a
              className="mono"
              href={explorerAddressUrl(CONTRACT_ADDRESS)}
              target="_blank"
              rel="noreferrer"
            >
              {CONTRACT_ADDRESS}
            </a>
          </Row>
          <Row k="Network">
            GenLayer StudioNet · chain {STUDIONET.chainIdDec} ({STUDIONET.chainIdHex})
          </Row>
          <Row k="RPC">{STUDIONET.rpcUrl}</Row>
          <Row k="Source">
            commit {CONTRACT_SOURCE_COMMIT} · 16 write + 17 view + 2 admin
          </Row>
          <Row k="SHA-256">
            <span className="mono tiny">{CONTRACT_SOURCE_SHA256}</span>
          </Row>
          {consts.data && (
            <>
              <Row k="Treasury admin">
                <span className="mono">{shortAddr(consts.data.treasury_addr, 6)}</span>
              </Row>
              <Row k="Treasury pool">{formatGen(consts.data.treasury_pool)}</Row>
              <Row k="Bonds">
                envelope {formatGen(consts.data.envelope_bond)} · fork{" "}
                {formatGen(consts.data.fork_creation_bond)} · challenge{" "}
                {formatGen(consts.data.challenge_bond)} · flip reward{" "}
                {formatGen(consts.data.challenger_flip_reward)}
              </Row>
              <Row k="State">
                <Tag tone={consts.data.paused ? "red" : "green"} dot>
                  {consts.data.paused ? "PAUSED" : "active"}
                </Tag>
              </Row>
            </>
          )}
          <Row k="Repository">
            <a href={REPO_URL} target="_blank" rel="noreferrer">
              {REPO_URL}
            </a>
          </Row>
        </DL>
      </div>

      <div className="section">
        <SectionHead eyebrow="Runtime" title="Notes" />
        <ul className="muted" style={{ marginTop: 0, paddingLeft: 18 }}>
          <li>
            <strong>Undetermined:</strong> a semantic transaction with no
            validator consensus commits zero state. The UI shows this distinctly
            from a contract rejection — re-arm and run again (3 retries, then a
            deterministic UNCLEAR terminal).
          </li>
          <li>
            <strong>Payable safety:</strong> on this runtime a reverted payable
            call keeps the attached value, so <code>lock_bond</code> is the only
            payable method and never reverts for a policy reason. Every other
            action is non-payable and consumes a pre-locked bond.
          </li>
          <li>
            <strong>No block time:</strong> challenge windows are owner-gated
            actions, not timestamps.
          </li>
          <li>
            <strong>StudioNet payout:</strong> contract-side GEN accounting is
            exact and on-chain; the final EOA credit of a refund is a documented
            StudioNet simulation gap that lands on a full chain layer.
          </li>
        </ul>
      </div>

      <div className="row faint tiny" style={{ gap: 10 }}>
        <Mark size={16} branchColor="var(--ink-3)" />
        Governance Fork
      </div>
    </div>
  );
}
