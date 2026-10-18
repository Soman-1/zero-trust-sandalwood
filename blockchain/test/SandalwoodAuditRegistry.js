const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("SandalwoodAuditRegistry", function () {
  let registry;
  let owner;
  let stranger;

  const ROOT_A = "0x1111111111111111111111111111111111111111111111111111111111111111";
  const ROOT_B = "0x2222222222222222222222222222222222222222222222222222222222222222";
  const ZERO = "0x0000000000000000000000000000000000000000000000000000000000000000";

  beforeEach(async function () {
    [owner, stranger] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("SandalwoodAuditRegistry");
    registry = await Factory.deploy();
    await registry.waitForDeployment();
  });

  it("sets deployer as owner", async function () {
    expect(await registry.owner()).to.equal(owner.address);
  });

  it("anchors a batch and verifies it", async function () {
    await expect(registry.recordAuditBatch(ROOT_A, 3, "batch-1")).to.emit(
      registry,
      "BatchAnchored"
    );

    const result = await registry.verifyAuditBatch(ROOT_A);
    expect(result.isAnchored).to.equal(true);
    expect(result.batchSize).to.equal(3n);
    expect(result.recorder).to.equal(owner.address);
    expect(await registry.getTotalBatches()).to.equal(1n);
  });

  it("rejects non-owner recorders", async function () {
    await expect(
      registry.connect(stranger).recordAuditBatch(ROOT_A, 1, "nope")
    ).to.be.revertedWith("Only registry owner can perform this operation");
  });

  it("rejects zero merkle root", async function () {
    await expect(registry.recordAuditBatch(ZERO, 1, "zero")).to.be.revertedWith(
      "Merkle root cannot be zero"
    );
  });

  it("rejects out-of-range batch sizes", async function () {
    await expect(registry.recordAuditBatch(ROOT_A, 0, "empty")).to.be.revertedWith(
      "Batch size out of range"
    );
    await expect(registry.recordAuditBatch(ROOT_A, 501, "too-big")).to.be.revertedWith(
      "Batch size out of range"
    );
  });

  it("rejects description over 128 bytes", async function () {
    const longDesc = "x".repeat(129);
    await expect(registry.recordAuditBatch(ROOT_A, 1, longDesc)).to.be.revertedWith(
      "Description exceeds 128 bytes"
    );
  });

  it("rejects duplicate merkle roots", async function () {
    await registry.recordAuditBatch(ROOT_A, 2, "first");
    await expect(registry.recordAuditBatch(ROOT_A, 2, "dup")).to.be.revertedWith(
      "Batch with this Merkle root is already anchored"
    );
  });

  it("tracks multiple distinct batches", async function () {
    await registry.recordAuditBatch(ROOT_A, 1, "a");
    await registry.recordAuditBatch(ROOT_B, 2, "b");
    expect(await registry.getTotalBatches()).to.equal(2n);
    expect(await registry.batchRoots(0)).to.equal(ROOT_A);
    expect(await registry.batchRoots(1)).to.equal(ROOT_B);
  });

  it("returns false for unknown roots", async function () {
    const result = await registry.verifyAuditBatch(ROOT_B);
    expect(result.isAnchored).to.equal(false);
    expect(result.batchSize).to.equal(0n);
  });

  it("allows owner to transfer ownership", async function () {
    await expect(registry.transferOwnership(stranger.address))
      .to.emit(registry, "OwnershipTransferred")
      .withArgs(owner.address, stranger.address);
    expect(await registry.owner()).to.equal(stranger.address);

    // New owner can record batches
    await expect(
      registry.connect(stranger).recordAuditBatch(ROOT_A, 1, "by-stranger")
    ).to.emit(registry, "BatchAnchored");

    // Old owner can no longer record
    await expect(
      registry.recordAuditBatch(ROOT_B, 1, "by-old-owner")
    ).to.be.revertedWith("Only registry owner can perform this operation");
  });

  it("rejects non-owner transferring ownership", async function () {
    await expect(
      registry.connect(stranger).transferOwnership(stranger.address)
    ).to.be.revertedWith("Only registry owner can perform this operation");
  });

  it("rejects transferring ownership to zero address or same owner", async function () {
    const ZERO_ADDRESS = "0x0000000000000000000000000000000000000000";
    await expect(registry.transferOwnership(ZERO_ADDRESS)).to.be.revertedWith(
      "New owner cannot be zero address"
    );
    await expect(registry.transferOwnership(owner.address)).to.be.revertedWith(
      "New owner must be different"
    );
  });
});
