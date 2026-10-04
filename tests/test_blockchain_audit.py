"""
Unit tests for Cryptographic Blockchain Audit Trail and Merkle Proof Engine.
"""

from src.blockchain_audit import (
    BackupChain,
    build_merkle_tree,
    generate_merkle_proof,
    sha256_hash,
    verify_merkle_proof,
)
from src.verify_audit import audit_add, audit_export, audit_proof, audit_verify


def test_merkle_tree_construction_and_proof():
    """Verify Merkle tree construction and proof verification logic."""
    leaf_hashes = [
        sha256_hash("file_a.txt"),
        sha256_hash("file_b.csv"),
        sha256_hash("file_c.json"),
        sha256_hash("file_d.tar.gz"),
    ]
    root, levels = build_merkle_tree(leaf_hashes)
    assert len(root) == 64
    assert len(levels) == 3

    # Generate and verify proof for each leaf
    for idx, leaf in enumerate(leaf_hashes):
        proof = generate_merkle_proof(idx, levels)
        assert verify_merkle_proof(leaf, proof, root) is True


def test_blockchain_genesis_and_add_block(tmp_path):
    """Test chain initialization with genesis block and adding blocks."""
    chain_file = tmp_path / "chain.json"
    chain = BackupChain(chain_file=chain_file, difficulty=1)

    assert len(chain.blocks) == 1
    genesis = chain.blocks[0]
    assert genesis.index == 0
    assert genesis.previous_hash == "0" * 64

    # Add block
    manifest = [
        {"path": "data/db.sqlite", "hash": sha256_hash("db_content"), "size": 1024},
        {"path": "data/app.log", "hash": sha256_hash("log_content"), "size": 2048},
    ]
    block = chain.add_block(manifest, command="backup", src="local", dst="s3:test")
    assert block.index == 1
    assert block.previous_hash == genesis.hash
    assert len(chain.blocks) == 2

    # Verify chain
    valid, msg = chain.verify_chain()
    assert valid is True
    assert "2 blocks" in msg


def test_blockchain_tamper_detection(tmp_path):
    """Test that modifying a block hash or payload causes verify_chain to fail."""
    chain_file = tmp_path / "chain.json"
    chain = BackupChain(chain_file=chain_file, difficulty=1)

    manifest = [{"path": "file1.txt", "hash": sha256_hash("f1"), "size": 100}]
    chain.add_block(manifest, command="sync")

    valid, _ = chain.verify_chain()
    assert valid is True

    # Tamper with block #1 data_hash
    chain.blocks[1].data_hash = sha256_hash("tampered_payload")
    valid_after_tamper, error_msg = chain.verify_chain()
    assert valid_after_tamper is False
    assert "mismatch" in error_msg.lower() or "broken" in error_msg.lower()


def test_get_merkle_proof_from_chain(tmp_path):
    """Test retrieving Merkle proof for a specific file hash from chain."""
    chain_file = tmp_path / "chain.json"
    chain = BackupChain(chain_file=chain_file, difficulty=1)

    target_hash = sha256_hash("important_patient_record.pdf")
    manifest = [
        {"path": "patient.pdf", "hash": target_hash, "size": 5000},
        {"path": "doctor_notes.txt", "hash": sha256_hash("notes"), "size": 200},
    ]
    chain.add_block(manifest)

    proof_info = chain.get_proof(target_hash)
    assert proof_info is not None
    assert proof_info["file_hash"] == target_hash
    assert proof_info["verified"] is True
    assert proof_info["block_index"] == 1


def test_cli_audit_commands(tmp_path):
    """Test CLI functions: audit_add, audit_verify, audit_proof, audit_export."""
    ret_add = audit_add(src="test_src", dst="test_dst")
    assert ret_add == 0

    ret_verify = audit_verify()
    assert ret_verify == 0

    chain = BackupChain()
    latest_block = chain.get_latest_block()
    first_file = latest_block.metadata["files"][0]

    ret_proof = audit_proof(first_file["hash"])
    assert ret_proof == 0

    pdf_out = tmp_path / "test_report.pdf"
    ret_export = audit_export(output_path=pdf_out)
    assert ret_export == 0
    assert pdf_out.exists()
