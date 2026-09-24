// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Nashhal Trust Anchor
/// @notice Anchors hashes of published newsroom manifests on-chain.
/// @dev No article text, images, or private information are stored here.
contract NashhalTrustAnchor is Ownable2Step {
    struct Anchor {
        uint64 anchoredAt;
        string cid;
        address submitter;
    }

    mapping(bytes32 => Anchor) public anchors;

    event ManifestAnchored(
        bytes32 indexed manifestHash,
        string cid,
        uint64 anchoredAt,
        address indexed submitter
    );

    error AlreadyAnchored(bytes32 manifestHash);
    error EmptyManifestHash();
    error EmptyCid();

    constructor(address initialOwner) Ownable(initialOwner) {}

    function anchorManifest(bytes32 manifestHash, string calldata cid) external onlyOwner {
        if (manifestHash == bytes32(0)) revert EmptyManifestHash();
        if (bytes(cid).length == 0) revert EmptyCid();
        if (anchors[manifestHash].anchoredAt != 0) revert AlreadyAnchored(manifestHash);

        uint64 timestamp = uint64(block.timestamp);
        anchors[manifestHash] = Anchor({
            anchoredAt: timestamp,
            cid: cid,
            submitter: msg.sender
        });

        emit ManifestAnchored(manifestHash, cid, timestamp, msg.sender);
    }

    function isAnchored(bytes32 manifestHash) external view returns (bool) {
        return anchors[manifestHash].anchoredAt != 0;
    }

    function getAnchor(bytes32 manifestHash)
        external
        view
        returns (uint64 anchoredAt, string memory cid, address submitter)
    {
        Anchor memory anchor = anchors[manifestHash];
        return (anchor.anchoredAt, anchor.cid, anchor.submitter);
    }
}
