import fs from "node:fs";
import path from "node:path";
import { ContractFactory, JsonRpcProvider, Wallet } from "ethers";

const root = process.cwd();
const rpcUrl = process.env.WEB3_RPC_URL;
const privateKey = process.env.WEB3_PRIVATE_KEY;
if (!rpcUrl || !privateKey) throw new Error("WEB3_RPC_URL and WEB3_PRIVATE_KEY are required");

const artifact = JSON.parse(fs.readFileSync(path.join(root, "web3", "artifacts", "NashhalTrustAnchor.json"), "utf8"));
const provider = new JsonRpcProvider(rpcUrl);
const wallet = new Wallet(privateKey, provider);
const network = await provider.getNetwork();
if (Number(network.chainId) !== 11155111) throw new Error("Expected Sepolia chainId 11155111, received " + network.chainId);

const factory = new ContractFactory(artifact.abi, artifact.bytecode, wallet);
const contract = await factory.deploy(wallet.address);
await contract.waitForDeployment();
const address = await contract.getAddress();

console.log(JSON.stringify({
  network: "sepolia",
  chainId: Number(network.chainId),
  deployer: wallet.address,
  contractAddress: address,
  explorer: "https://sepolia.etherscan.io/address/" + address
}, null, 2));