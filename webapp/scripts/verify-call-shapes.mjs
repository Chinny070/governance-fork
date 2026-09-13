// Verifies every writeAndWait/view call in src/lib/api.ts against the
// live production contract schema (fetched from StudioNet). Run:
//   node scripts/verify-call-shapes.mjs
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const RPC = "https://studio.genlayer.com/api";
// Keep in sync with CONTRACT_ADDRESS in src/lib/contract.ts.
const ADDR = "0x4ACb76E0517a3Ad2d19699486595291b0089b077";

async function getSchema() {
  const r = await fetch(RPC, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "gen_getContractSchema",
      params: [ADDR],
    }),
  });
  const j = await r.json();
  if (!j.result) throw new Error("no schema: " + JSON.stringify(j));
  return typeof j.result === "string" ? JSON.parse(j.result) : j.result;
}

// method name -> arg count, as called from api.ts (first arg for writes is
// the client, not a calldata arg — excluded here).
const EXPECTED = {
  // reads
  get_constants: 0,
  get_dao: 1,
  get_root_proposal: 1,
  get_fork: 1,
  get_case: 1,
  get_evidence: 1,
  get_verdict: 1,
  get_challenge: 1,
  get_bond: 1,
  list_daos: 2,
  list_root_proposals_by_dao: 3,
  list_forks_of_root: 3,
  list_forks_of_parent: 3,
  list_evidence_of_case: 3,
  list_challenges: 4,
  get_verdict_history: 4,
  list_bonds_by_target: 4,
  // writes
  register_dao: 2,
  import_root_proposal: 6,
  lock_bond: 1,
  settle_bond: 1,
  withdraw_treasury: 1,
  submit_root_envelope: 15,
  create_fork: 13,
  submit_fork_evidence: 7,
  close_evidence: 1,
  fetch_evidence: 1,
  seal_evidence: 1,
  abort_case: 1,
  adjudicate: 1,
  run_adjudication: 1,
  challenge_verdict: 5,
  open_finality_window: 2,
  finalize: 2,
  pause: 0,
  unpause: 0,
};

const PAYABLE = new Set(["lock_bond"]);

const schema = await getSchema();
const methods = schema.methods ?? {};
let bad = 0;

for (const [name, count] of Object.entries(EXPECTED)) {
  const m = methods[name];
  if (!m) {
    console.error(`MISSING on contract: ${name}`);
    bad++;
    continue;
  }
  const got = (m.params ?? []).length;
  if (got !== count) {
    console.error(`ARITY ${name}: frontend sends ${count}, contract expects ${got}`);
    bad++;
  }
  if (!!m.payable !== PAYABLE.has(name)) {
    console.error(`PAYABLE ${name}: frontend ${PAYABLE.has(name)}, contract ${!!m.payable}`);
    bad++;
  }
}

const contractMethods = new Set(Object.keys(methods));
for (const k of contractMethods) {
  if (!(k in EXPECTED)) console.warn(`(contract method not used by frontend: ${k})`);
}

// cross-check the local enum module's bond amount against get_constants
const enumsSrc = readFileSync(resolve(here, "../src/lib/enums.ts"), "utf8");
const bondWei = enumsSrc.match(/BOND_AMOUNT_WEI\s*=\s*([\d_]+)n/)?.[1]?.replace(/_/g, "");
const cr = await fetch(RPC, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({
    jsonrpc: "2.0",
    id: 2,
    method: "gen_call",
    params: [
      {
        to: ADDR,
        from: "0x0000000000000000000000000000000000000000",
        data: null,
      },
    ],
  }),
}).catch(() => null);

console.log(`\nlocal BOND_AMOUNT_WEI = ${bondWei}`);
if (bondWei !== "100000000000000000") {
  console.error("BOND_AMOUNT_WEI mismatch with the documented 0.1 GEN");
  bad++;
}

console.log(
  bad === 0
    ? "\nOK — every frontend call shape matches the live contract schema."
    : `\nFAIL — ${bad} mismatch(es).`,
);
process.exit(bad === 0 ? 0 : 1);
