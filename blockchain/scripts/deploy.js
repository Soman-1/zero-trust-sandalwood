const hre = require("hardhat");

async function main() {
  const Registry = await hre.ethers.getContractFactory("SandalwoodAuditRegistry");
  const registry = await Registry.deploy();
  await registry.waitForDeployment();
  const address = await registry.getAddress();
  const [deployer] = await hre.ethers.getSigners();

  console.log(JSON.stringify({
    contractAddress: address,
    deployer: deployer.address,
    chainId: (await hre.ethers.provider.getNetwork()).chainId.toString(),
  }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
