import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { Contract, JsonRpcProvider, Wallet } from "ethers";

const packageRoot = process.cwd();
const repoRoot = path.resolve(packageRoot, "..");
const newsPath = path.join(repoRoot, "data", "news.json");
const outDir = path.join(repoRoot, "data", "web3");
const manifestPath = path.join(outDir, "manifest.json");
const anchorPath = path.join(outDir, "anchor.json");
const artifactPath = path.join(packageRoot, "artifacts", "NashhalTrustAnchor.json");

function clean(v) {
  return String(v ?? "").replace(/<[^>]+>/g, " ").replace(/\\s+/g, " ").trim();
}

const data = JSON.parse(fs.readFileSync(newsPath, "utf8"));
const items = Array.isArray(data) ? data : (data.items || data.news || []);
const records = items
  .filter((x) => x && x.status === "published" && x.id && x.content_hash)
  .map((x) => ({ id: clean(x.id), content_hash: clean(x.content_hash), published: clean(x.published || x.published_at) }))
  .sort((a, b) => a.id.localeCompare(b.id));

if (!records.length) { console.log("[WEB3] no published records to anchor"); process.exit(0); }

const canonical = JSON.stringify({ schema: "nashhal-trust-manifest/v1", records });
const manifestHash = "0x" + crypto.createHash("sha256").update(canonical, "utf8").digest("hex");
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(manifestPath, JSON.stringify({
  schema: "nashhal-trust-manifest/v1",
  generated_at: new Date().toISOString(),
  hash_algorithm: "SHA-256",
  manifest_hash: manifestHash,
  records
}, null, 2) + "\n");

let cid = process.env.IPFS_CID || "";
if (!cid && process.env.IPFS_API_URL) {
  const form = new FormData();
  form.append("file", new Blob([fs.readFileSync(manifestPath)], { type: "application/json" }), "manifest.json");
  const headers = {};
  if (process.env.IPFS_API_TOKEN) headers.Authorization = "Bearer " + process.env.IPFS_API_TOKEN;
  const response = await fetch(process.env.IPFS_API_URL, { method: "POST", headers, body: form });
  if (!response.ok) throw new Error("IPFS upload failed: HTTP " + response.status + " " + await response.text());
  const raw = await response.text();
  const lines = raw.trim().split("\n").filter(Boolean);
  const last = JSON.parse(lines[lines.length - 1]);
  cid = last.Hash || last.cid || "";
  if (!cid) throw new Error("IPFS endpoint returned no CID");
}

const result = {
  status: "prepared",
  network: "sepolia",
  chain_id: 11155111,
  manifest_hash: manifestHash,
  manifest_file: "data/web3/manifest.json",
  record_count: records.length,
  cid: cid || null,
  contract_address: process.env.WEB3_CONTRACT_ADDRESS || null,
  transaction_hash: null,
  anchored_at: null,
  explorer_url: null
};

const rpcUrl = process.env.WEB3_RPC_URL;
const privateKey = process.env.WEB3_PRIVATE_KEY;
const contractAddress = process.env.WEB3_CONTRACT_ADDRESS;
if (rpcUrl && privateKey && contractAddress) {
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
  const provider = new JsonRpcProvider(rpcUrl);
  const wallet = new Wallet(privateKey, provider);
  const network = await provider.getNetwork();
  if (Number(network.chainId) !== 11155111) throw new Error("Expected Sepolia chainId 11155111, received " + network.chainId);
  const contract = new Contract(contractAddress, artifact.abi, wallet);
  const existing = await contract.getAnchor(manifestHash);
  if (Number(existing[0]) > 0) {
    result.status = "anchored";
    result.anchored_at = Number(existing[0]);
    result.cid = existing[1] || result.cid;
  } else {
    if (!cid) throw new Error("IPFS CID is required before on-chain anchoring");
    const tx = await contract.anchorManifest(manifestHash, cid);
    const receipt = await tx.wait();
    result.status = "anchored";
    result.transaction_hash = receipt.hash;
    result.anchored_at = Math.floor(Date.now() / 1000);
  }
  result.explorer_url = result.transaction_hash ? "https://sepolia.etherscan.io/tx/" + result.transaction_hash : null;
}

fs.writeFileSync(anchorPath, JSON.stringify(result, null, 2) + "\n");
console.log(JSON.stringify(result, null, 2));