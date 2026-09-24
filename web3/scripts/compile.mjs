import fs from "node:fs";
import path from "node:path";
import solc from "solc";

const root = process.cwd();
const sourcePath = path.join(root, "contracts", "NashhalTrustAnchor.sol");
const source = fs.readFileSync(sourcePath, "utf8");

const input = {
  language: "Solidity",
  sources: { "NashhalTrustAnchor.sol": { content: source } },
  settings: {
    optimizer: { enabled: true, runs: 200 },
    outputSelection: { "*": { "*": ["abi", "evm.bytecode.object", "evm.deployedBytecode.object"] } }
  }
};

function findImports(importPath) {
  const full = path.join(root, "node_modules", importPath);
  if (!fs.existsSync(full)) return { error: "Import not found: " + importPath };
  return { contents: fs.readFileSync(full, "utf8") };
}

const output = JSON.parse(solc.compile(JSON.stringify(input), { import: findImports }));
const errors = (output.errors || []).filter((e) => e.severity === "error");
if (errors.length) {
  for (const error of errors) console.error(error.formattedMessage);
  process.exit(1);
}

const contract = output.contracts["NashhalTrustAnchor.sol"].NashhalTrustAnchor;
const artifact = {
  contractName: "NashhalTrustAnchor",
  compiler: solc.version(),
  abi: contract.abi,
  bytecode: "0x" + contract.evm.bytecode.object,
  deployedBytecode: "0x" + contract.evm.deployedBytecode.object
};

const outDir = path.join(root, "web3", "artifacts");
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, "NashhalTrustAnchor.json"), JSON.stringify(artifact, null, 2) + "\n");
console.log("[WEB3] compiled " + artifact.contractName + " with " + artifact.compiler);