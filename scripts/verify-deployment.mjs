// Verifies that the contract deployed at an address is byte-for-byte the
// source in this repository.
//
//   node scripts/verify-deployment.mjs <contract-address> [path-to-contract.py]
//
// It fetches the deployed code from StudioNet (gen_getContractCode), hashes
// it, hashes the repository file, and prints both. Exit code 0 only if the
// SHA-256 digests are identical.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const RPC = "https://studio.genlayer.com/api";
const here = dirname(fileURLToPath(import.meta.url));
const addr = process.argv[2];
const file = process.argv[3] ?? resolve(here, "../contracts/governance_fork.py");

if (!/^0x[0-9a-fA-F]{40}$/.test(addr ?? "")) {
  console.error("usage: node scripts/verify-deployment.mjs <0x-contract-address> [contract.py]");
  process.exit(2);
}

const sha = (buf) => createHash("sha256").update(buf).digest("hex");

const res = await fetch(RPC, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "gen_getContractCode", params: [addr] }),
});
const body = await res.json();
if (!body.result) {
  console.error("RPC returned no code for", addr, JSON.stringify(body.error ?? body));
  process.exit(2);
}
const deployed = Buffer.from(body.result, "base64");
const local = readFileSync(file);

const deployedHash = sha(deployed);
const localHash = sha(local);
console.log("address        :", addr);
console.log("deployed bytes :", deployed.length, "sha256", deployedHash);
console.log("repo file      :", file);
console.log("repo bytes     :", local.length, "sha256", localHash);
console.log(deployedHash === localHash ? "\nMATCH: the deployed contract is exactly this source file." : "\nMISMATCH: the deployed code differs from this file.");
process.exitCode = deployedHash === localHash ? 0 : 1;
