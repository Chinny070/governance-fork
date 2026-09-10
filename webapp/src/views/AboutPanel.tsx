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
import { Badge, Card, KV, Row } from "../components/ui";

const STEPS = [
  ["DAO", "register_dao — name the governance body"],
  ["Root proposal", "import_root_proposal — the authoritative proposal + params"],
  ["Bond lock", 'lock_bond("ENVELOPE") — 0.1 GEN, the only payable call'],
  ["Intent envelope", "submit_root_envelope — objective, scope, constraints, mutable/immutable dimensions, evidence"],
  ["Evidence", "close_evidence → fetch_evidence (real gl.nondet.web.render, one item per tx) → seal_evidence"],
  ["Adjudication", "adjudicate (arm) → run_adjudication (semantic consensus, eq_principle.prompt_comparative)"],
  ["Verdict", "FAITHFUL / NOT_FAITHFUL / UNCLEAR / INVALID with per-dimension findings"],
  ["Challenge", 'lock_bond("CHALLENGE") → challenge_verdict — assert a specific dimension is wrong, trigger re-adjudication'],
  ["Finality", "finalize — owner-gated, force-finality once the challenge budget is spent"],
  ["Bond settlement", "settle_bond — deterministic disposition; refund + slash == amount; flip reward from the pool"],
  ["Fork", 'lock_bond("FORK_CREATION") → create_fork — a semantic descendant that keeps the intent and declares its delta'],
  ["Proposal tree", "every fork runs the same pipeline; a fork is forkable only once finalized FAITHFUL"],
];

export function AboutPanel() {
  const consts = useAsync(getConstants, []);

  return (
    <div className="stack">
      <Card title="Governance Fork">
        <p style={{ marginTop: 0, fontSize: 15 }}>
          <strong>Don't vote YES or NO. Change the proposal.</strong>
        </p>
        <p className="muted">
          Governance Fork is a semantic-descendant DAO governance registry built
          as a GenLayer Intelligent Contract. Instead of an up/down vote, a
          participant creates a <em>fork</em> of a proposal: a new version that
          keeps the original intent and declares exactly what it changes. An
          on-chain LLM adjudication (GenLayer's optimistic-democracy consensus)
          decides whether each version faithfully represents its parent's
          intent. Anyone can challenge a verdict; the challenge is re-adjudicated,
          not counted as a vote.
        </p>
        <div className="row">
          <button className="primary" onClick={() => navigate({ name: "build" })}>
            Build a proposal
          </button>
          <button onClick={() => navigate({ name: "explore" })}>
            Explore the registry
          </button>
        </div>
      </Card>

      <Card title="Production contract">
        <KV>
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
            GenLayer StudioNet · chain {STUDIONET.chainIdDec} (
            {STUDIONET.chainIdHex})
          </Row>
          <Row k="RPC">{STUDIONET.rpcUrl}</Row>
          <Row k="Source commit">{CONTRACT_SOURCE_COMMIT}</Row>
          <Row k="Source SHA-256">
            <span className="mono tiny">{CONTRACT_SOURCE_SHA256}</span>
          </Row>
          <Row k="ABI">16 write + 17 view + 2 admin (35 methods)</Row>
          {consts.data && (
            <>
              <Row k="Treasury admin">
                <span className="mono" title={consts.data.treasury_addr}>
                  {shortAddr(consts.data.treasury_addr, 6)}
                </span>
              </Row>
              <Row k="Treasury pool">
                {formatGen(consts.data.treasury_pool)}
              </Row>
              <Row k="Bonds">
                envelope {formatGen(consts.data.envelope_bond)} · fork{" "}
                {formatGen(consts.data.fork_creation_bond)} · challenge{" "}
                {formatGen(consts.data.challenge_bond)} · flip reward{" "}
                {formatGen(consts.data.challenger_flip_reward)}
              </Row>
              <Row k="Contract state">
                <Badge tone={consts.data.paused ? "bad" : "ok"}>
                  {consts.data.paused ? "PAUSED" : "active"}
                </Badge>
              </Row>
            </>
          )}
          <Row k="Repository">
            <a href={REPO_URL} target="_blank" rel="noreferrer">
              {REPO_URL}
            </a>
          </Row>
        </KV>
      </Card>

      <Card title="Full lifecycle">
        <div className="list">
          {STEPS.map(([name, detail], i) => (
            <div className="list-item" key={i} style={{ cursor: "default" }}>
              <span className="badge neutral">{i + 1}</span>
              <div className="grow">
                <div className="primary-line">{name}</div>
                <div className="tiny faint mono">{detail}</div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Runtime notes">
        <ul className="muted" style={{ marginTop: 0 }}>
          <li>
            <strong>Undetermined:</strong> a semantic transaction with no
            validator consensus commits zero state. The UI surfaces this
            distinctly from a contract rejection — re-arm and run again (3
            retries, then a deterministic UNCLEAR terminal).
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
            <strong>StudioNet payout note:</strong> contract-side GEN accounting
            (capture into balance, deduction on settlement, treasury pool) is
            exact and on-chain. The final EOA credit of a refund is a documented
            StudioNet simulation gap that lands on a full chain layer.
          </li>
        </ul>
      </Card>
    </div>
  );
}
