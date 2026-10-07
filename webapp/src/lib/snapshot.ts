// Import a real proposal from Snapshot by URL. Pure parsing/mapping helpers
// are separate from the network calls so they can be unit-tested.
//
// Two Snapshot proposal shapes exist:
//   - off-chain: .../#/<space>/proposal/0x<64 hex>        -> hub.snapshot.org
//   - on-chain (Snapshot X): .../#/(org/<slug>/)?<network>:<0xspace>/proposal/<decimal id>
//                                                          -> api.snapshot.box

export interface SnapshotProposal {
  id: string;
  title: string;
  body: string;
  choices: string[];
  state: string;
  author: string;
  space: { id: string; name: string };
  /** canonical link to the proposal page */
  link: string;
  /** link to the space/DAO page */
  spaceLink: string;
}

export interface ImportedFields {
  daoName: string;
  daoUrl: string;
  externalId: string;
  title: string;
  proposalUrl: string;
  keys: string[];
  values: string[];
}

export type ParsedSnapshotUrl =
  | { kind: "offchain"; space: string; id: string }
  | { kind: "onchain"; network: string; space: string; id: string };

const HOSTS = "(?:www\\.)?(?:snapshot\\.org|snapshot\\.box|testnet\\.snapshot\\.org)\\.?";

const OFFCHAIN = new RegExp(
  `^https?://${HOSTS}/#/(?:s:|[a-z]+:)?([^/\\s:]+)/proposal/(0x[0-9a-fA-F]{64})/?$`,
);
const ONCHAIN = new RegExp(
  `^https?://${HOSTS}/#/(?:org/[^/\\s]+/)?([a-z0-9-]+):(0x[0-9a-fA-F]{40})/proposal/(\\d+)/?$`,
);

export function parseSnapshotUrl(raw: string): ParsedSnapshotUrl | null {
  const s = raw.trim();
  const on = s.match(ONCHAIN);
  if (on) return { kind: "onchain", network: on[1], space: on[2], id: on[3] };
  const off = s.match(OFFCHAIN);
  if (off) return { kind: "offchain", space: off[1], id: off[2] };
  return null;
}

const clip = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
const oneLine = (s: string) => s.replace(/[\r\n]+/g, " ").trim();

export function mapSnapshot(p: SnapshotProposal): ImportedFields {
  const keys: string[] = [];
  const values: string[] = [];
  const add = (k: string, v: string) => {
    if (keys.length >= 32) return;
    keys.push(clip(oneLine(k), 64));
    values.push(clip(oneLine(v), 256));
  };
  add("source", "snapshot");
  add("space", p.space.id);
  add("state", p.state);
  add("author", p.author);
  p.choices.slice(0, 20).forEach((c, i) => add(`choice_${i + 1}`, c));
  return {
    daoName: clip(oneLine(p.space.name || p.space.id), 128),
    daoUrl: clip(p.spaceLink, 512),
    externalId: clip(p.id, 128),
    title: clip(oneLine(p.title), 256),
    proposalUrl: clip(p.link, 512),
    keys,
    values,
  };
}

async function gql(url: string, query: string, variables: Record<string, unknown>) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query, variables }),
  });
  if (!r.ok) throw new Error(`Snapshot returned HTTP ${r.status}`);
  return r.json();
}

export async function fetchSnapshotProposal(
  parsed: ParsedSnapshotUrl,
): Promise<SnapshotProposal> {
  if (parsed.kind === "offchain") {
    const j = await gql(
      "https://hub.snapshot.org/graphql",
      `query($id:String!){proposal(id:$id){id title body choices state author space{id name}}}`,
      { id: parsed.id },
    );
    const p = j?.data?.proposal;
    if (!p) throw new Error("Snapshot has no proposal with that id.");
    return {
      ...p,
      link: `https://snapshot.org/#/${p.space.id}/proposal/${p.id}`,
      spaceLink: `https://snapshot.org/#/${p.space.id}`,
    } as SnapshotProposal;
  }
  // On-chain (Snapshot X). The API is keyed by "<space address>/<proposal id>"
  // with the network as the indexer; the address must keep its checksummed case.
  const j = await gql(
    "https://api.snapshot.box",
    `query($id:String!,$ix:String!){proposal(id:$id,indexer:$ix){proposal_id state author{id} link space{id metadata{name}} metadata{title body choices}}}`,
    { id: `${parsed.space}/${parsed.id}`, ix: parsed.network },
  );
  const p = j?.data?.proposal;
  if (!p) {
    throw new Error(
      j?.errors?.[0]?.message?.startsWith("Row not found")
        ? "Snapshot has no on-chain proposal with that id."
        : "Could not load that proposal from Snapshot.",
    );
  }
  return {
    id: p.proposal_id,
    title: p.metadata?.title ?? "",
    body: p.metadata?.body ?? "",
    choices: p.metadata?.choices ?? [],
    state: p.state,
    author: p.author?.id ?? "",
    space: { id: p.space.id, name: p.space.metadata?.name ?? p.space.id },
    link: p.link,
    spaceLink: `https://snapshot.box/#/${parsed.network}:${parsed.space}`,
  };
}
