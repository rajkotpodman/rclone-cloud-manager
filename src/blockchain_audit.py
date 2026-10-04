"""
Cryptographic Blockchain Audit Trail & Merkle Tree Verification.
Provides tamper-proof provenance for cloud backup snapshots and replication jobs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Path setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

AUDIT_DIR = PROJECT_ROOT / "audit"
DEFAULT_CHAIN_FILE = AUDIT_DIR / "chain.json"
OPERATOR_SECRET = os.getenv(
    "AUDIT_OPERATOR_SECRET", "rclone-audit-hmac-master-key-2026"
)


def sha256_hash(data: str) -> str:
    """Calculates SHA-256 hex digest of a string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_file_sha256(file_path: Path) -> str:
    """Computes SHA-256 checksum of a physical file."""
    if not file_path.exists() or file_path.is_dir():
        return sha256_hash(str(file_path))
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# =====================================================================
# Merkle Tree Construction & Proof Generation
# =====================================================================


def build_merkle_tree(leaf_hashes: List[str]) -> Tuple[str, List[List[str]]]:
    """
    Constructs a standard binary SHA-256 Merkle tree from leaf hashes.
    If level count is odd, duplicates the last node.
    Returns: (merkle_root, tree_levels)
    """
    if not leaf_hashes:
        empty_root = sha256_hash("EMPTY_MERKLE_TREE")
        return empty_root, [[empty_root]]

    levels: List[List[str]] = [list(leaf_hashes)]
    current_level = list(leaf_hashes)

    while len(current_level) > 1:
        next_level: List[str] = []
        if len(current_level) % 2 != 0:
            current_level.append(current_level[-1])

        for i in range(0, len(current_level), 2):
            combined = current_level[i] + current_level[i + 1]
            parent_hash = sha256_hash(combined)
            next_level.append(parent_hash)

        levels.append(next_level)
        current_level = next_level

    return levels[-1][0], levels


def generate_merkle_proof(
    leaf_index: int, tree_levels: List[List[str]]
) -> List[Dict[str, str]]:
    """
    Generates an audit proof path for a leaf at leaf_index.
    Returns list of dicts with sibling hash and position ('left' | 'right').
    """
    proof: List[Dict[str, str]] = []
    idx = leaf_index

    for level in tree_levels[:-1]:
        # Handle odd level sizing
        working_level = list(level)
        if len(working_level) % 2 != 0:
            working_level.append(working_level[-1])

        if idx % 2 == 0:
            # Sibling is on the right
            sibling_idx = idx + 1
            if sibling_idx < len(working_level):
                proof.append(
                    {"sibling": working_level[sibling_idx], "position": "right"}
                )
        else:
            # Sibling is on the left
            sibling_idx = idx - 1
            proof.append({"sibling": working_level[sibling_idx], "position": "left"})

        idx //= 2

    return proof


def verify_merkle_proof(
    leaf_hash: str, proof: List[Dict[str, str]], expected_root: str
) -> bool:
    """Validates that a leaf_hash belongs to the expected Merkle root using proof."""
    current = leaf_hash
    for item in proof:
        sibling = item["sibling"]
        position = item["position"]
        if position == "right":
            current = sha256_hash(current + sibling)
        else:
            current = sha256_hash(sibling + current)
    return current == expected_root


# =====================================================================
# Block & BackupChain
# =====================================================================


class Block:
    """Cryptographic block representing a backup event and its file manifest."""

    def __init__(
        self,
        index: int,
        timestamp: str,
        previous_hash: str,
        data_hash: str,
        merkle_root: str,
        nonce: int,
        hash: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.index = index
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.data_hash = data_hash
        self.merkle_root = merkle_root
        self.nonce = nonce
        self.hash = hash
        self.metadata = metadata or {}

    def compute_hash(self, nonce: Optional[int] = None) -> str:
        """Calculates canonical block hash."""
        n = self.nonce if nonce is None else nonce
        payload = (
            f"{self.index}:{self.timestamp}:{self.previous_hash}:"
            f"{self.data_hash}:{self.merkle_root}:{n}"
        )
        return sha256_hash(payload)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes block to JSON-compatible dictionary."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "data_hash": self.data_hash,
            "merkle_root": self.merkle_root,
            "nonce": self.nonce,
            "hash": self.hash,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Block:
        """Deserializes block from dictionary."""
        return cls(
            index=data["index"],
            timestamp=data["timestamp"],
            previous_hash=data["previous_hash"],
            data_hash=data["data_hash"],
            merkle_root=data["merkle_root"],
            nonce=data["nonce"],
            hash=data["hash"],
            metadata=data.get("metadata", {}),
        )


class BackupChain:
    """Cryptographic blockchain managing tamper-proof cloud backup receipts."""

    def __init__(
        self,
        chain_file: Optional[Path] = None,
        difficulty: int = 1,
    ) -> None:
        self.chain_file = chain_file or DEFAULT_CHAIN_FILE
        self.difficulty = difficulty
        self.blocks: List[Block] = []
        self._load_or_init()

    def _generate_operator_signature(self, message: str) -> str:
        """Creates HMAC-SHA256 digital signature representing operator approval."""
        return hmac.new(
            OPERATOR_SECRET.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _create_genesis_block(self) -> Block:
        """Constructs canonical Genesis block."""
        timestamp = "2026-01-01T00:00:00Z"
        empty_root = sha256_hash("GENESIS_MERKLE_ROOT")
        data_hash = sha256_hash("GENESIS_DATA_PAYLOAD")
        nonce = 0
        genesis = Block(
            index=0,
            timestamp=timestamp,
            previous_hash="0" * 64,
            data_hash=data_hash,
            merkle_root=empty_root,
            nonce=0,
            hash="",
            metadata={
                "command": "GENESIS_INIT",
                "src": "origin",
                "dst": "chain",
                "operator": "Rajkot Podman (Cloud Automation Engineer)",
                "operator_signature": self._generate_operator_signature("GENESIS"),
                "files": [],
            },
        )
        # Mine genesis block
        while True:
            h = genesis.compute_hash(nonce)
            if h.startswith("0" * self.difficulty):
                genesis.nonce = nonce
                genesis.hash = h
                break
            nonce += 1
        return genesis

    def _load_or_init(self) -> None:
        """Loads chain from audit/chain.json or creates genesis block."""
        if self.chain_file.exists():
            try:
                raw = json.loads(self.chain_file.read_text(encoding="utf-8"))
                self.blocks = [Block.from_dict(b) for b in raw]
                if self.blocks:
                    return
            except Exception:
                pass

        self.blocks = [self._create_genesis_block()]
        self.export_chain()

    def get_latest_block(self) -> Block:
        """Returns the most recent block on the chain."""
        return self.blocks[-1]

    def add_block(
        self,
        file_manifest: List[Dict[str, Any]],
        command: str = "sync",
        src: str = "gdrive:",
        dst: str = "s3:backup",
        operator: str = "Rajkot Podman",
        operator_signature: Optional[str] = None,
    ) -> Block:
        """
        Creates SHA-256 Merkle root of files, mines proof-of-work, and appends block.
        file_manifest format: [{"path": "file1.txt", "hash": "<sha256>", "size": 1024}]
        """
        previous_block = self.get_latest_block()
        index = previous_block.index + 1
        timestamp = datetime.now().isoformat()

        # Extract file hashes to build Merkle Tree
        leaf_hashes: List[str] = []
        for item in file_manifest:
            f_hash = item.get("hash")
            if not f_hash:
                f_hash = sha256_hash(item.get("path", str(item)))
                item["hash"] = f_hash
            leaf_hashes.append(f_hash)

        merkle_root, _ = build_merkle_tree(leaf_hashes)

        # Prepare metadata payload
        sig = operator_signature or self._generate_operator_signature(
            f"{index}:{timestamp}:{merkle_root}"
        )
        metadata = {
            "command": command,
            "src": src,
            "dst": dst,
            "operator": operator,
            "operator_signature": sig,
            "files": file_manifest,
        }

        data_json = json.dumps(metadata, sort_keys=True)
        data_hash = sha256_hash(data_json)

        # Mine block meeting difficulty
        nonce = 0
        candidate = Block(
            index=index,
            timestamp=timestamp,
            previous_hash=previous_block.hash,
            data_hash=data_hash,
            merkle_root=merkle_root,
            nonce=0,
            hash="",
            metadata=metadata,
        )

        prefix = "0" * self.difficulty
        while True:
            candidate_hash = candidate.compute_hash(nonce)
            if candidate_hash.startswith(prefix):
                candidate.nonce = nonce
                candidate.hash = candidate_hash
                break
            nonce += 1

        self.blocks.append(candidate)
        self.export_chain()
        return candidate

    def verify_chain(self) -> Tuple[bool, str]:
        """
        Validates the cryptographic integrity of the entire chain:
        1. Parent-child hash linkages
        2. Proof-of-work compliance
        3. Recalculated block hashes
        4. Recalculated Merkle roots from file manifests
        """
        if not self.blocks:
            return False, "Chain is empty."

        prefix = "0" * self.difficulty

        for i, block in enumerate(self.blocks):
            # 1. Verify recalculation of block hash
            expected_hash = block.compute_hash()
            if block.hash != expected_hash:
                return (
                    False,
                    f"Block #{block.index} hash mismatch: {block.hash} != {expected_hash}",
                )

            # 2. Verify difficulty target
            if not block.hash.startswith(prefix):
                return (
                    False,
                    f"Block #{block.index} does not satisfy difficulty requirement '{prefix}'.",
                )

            # 3. Verify linkage to previous block
            if i > 0:
                prev_block = self.blocks[i - 1]
                if block.previous_hash != prev_block.hash:
                    return (
                        False,
                        f"Block #{block.index} previous_hash link broken: "
                        f"{block.previous_hash} != {prev_block.hash}",
                    )

            # 4. Verify Merkle root against stored file manifest
            files = block.metadata.get("files", [])
            if files:
                file_hashes = [f["hash"] for f in files if "hash" in f]
                recomputed_root, _ = build_merkle_tree(file_hashes)
                if block.merkle_root != recomputed_root:
                    return (
                        False,
                        f"Block #{block.index} Merkle root corrupt: "
                        f"{block.merkle_root} != {recomputed_root}",
                    )

        return (
            True,
            f"Chain integrity verified: {len(self.blocks)} blocks are tamper-free.",
        )

    def export_chain(self, file_path: Optional[Path] = None) -> Path:
        """Saves chain to JSON file (audit/chain.json)."""
        target = file_path or self.chain_file
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = [b.to_dict() for b in self.blocks]
        target.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        return target

    def get_proof(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """
        Locates file_hash across blocks and generates its Merkle proof path.
        Returns dictionary with proof details or None if not found.
        """
        for block in reversed(self.blocks):
            files = block.metadata.get("files", [])
            file_hashes = [f.get("hash") for f in files if f.get("hash")]

            if file_hash in file_hashes:
                leaf_index = file_hashes.index(file_hash)
                matched_file = files[leaf_index]
                _, levels = build_merkle_tree(file_hashes)
                proof = generate_merkle_proof(leaf_index, levels)

                is_valid = verify_merkle_proof(file_hash, proof, block.merkle_root)

                return {
                    "file_path": matched_file.get("path"),
                    "file_hash": file_hash,
                    "file_size": matched_file.get("size", 0),
                    "block_index": block.index,
                    "block_hash": block.hash,
                    "block_timestamp": block.timestamp,
                    "merkle_root": block.merkle_root,
                    "proof_path": proof,
                    "verified": is_valid,
                }
        return None
