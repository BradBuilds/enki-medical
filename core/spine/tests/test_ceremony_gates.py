"""
Tests for ceremony gates.

Validates Gate A (pack integrity), Gate B (ceremony determinism),
and Gate C (admission compatibility).

Authority: GDU Technical Build Plan v2.4.0 §Phase 2.2
"""

import pytest
import json
from pathlib import Path
from core.spine.ceremony_gates import (
    gate_a_pack_integrity,
    gate_b_ceremony_determinism,
    gate_c_admission_compatibility,
    run_all_gates,
    GateError
)
from core.spine.validation_transcript import ValidationTranscript, ValidationOutcome
from core.spine.active_set import ActiveSet, PackDeclaration


class TestGateAPackIntegrity:
    """Test Gate A: Pack Integrity."""
    
    def test_gate_a_passes_valid_pack(self, tmp_path):
        """Valid pack passes Gate A."""
        pack_dir = tmp_path / "testpack"
        pack_dir.mkdir()
        
        # Create valid pack.json
        pack_json = {
            "pack_id": "testpack",
            "version": "1.0.0",
            "name": "Test Pack",
            "definitions": [],
            "namespaces_owned": ["testpack"]
        }
        with open(pack_dir / "pack.json", 'w') as f:
            json.dump(pack_json, f)
        
        # Create definitions directory
        (pack_dir / "definitions").mkdir()
        
        errors = gate_a_pack_integrity({"testpack": pack_dir})
        
        assert len(errors) == 0
    
    def test_gate_a_rejects_missing_pack_json(self, tmp_path):
        """Pack without pack.json fails Gate A."""
        pack_dir = tmp_path / "testpack"
        pack_dir.mkdir()
        
        errors = gate_a_pack_integrity({"testpack": pack_dir})
        
        assert len(errors) == 1
        assert errors[0].code == "PACK_JSON_MISSING"
        assert errors[0].gate == "A"
    
    def test_gate_a_rejects_missing_namespaces_owned(self, tmp_path):
        """Pack without namespaces_owned fails Gate A."""
        pack_dir = tmp_path / "testpack"
        pack_dir.mkdir()
        
        pack_json = {
            "pack_id": "testpack",
            "version": "1.0.0",
            "definitions": []
        }
        with open(pack_dir / "pack.json", 'w') as f:
            json.dump(pack_json, f)
        
        (pack_dir / "definitions").mkdir()
        
        errors = gate_a_pack_integrity({"testpack": pack_dir})
        
        assert any(e.code == "NAMESPACES_OWNED_MISSING" for e in errors)
    
    def test_gate_a_rejects_volatile_fields(self, tmp_path):
        """Pack with volatile data fails Gate A."""
        pack_dir = tmp_path / "testpack"
        pack_dir.mkdir()
        
        pack_json = {
            "pack_id": "testpack",
            "version": "1.0.0",
            "namespaces_owned": ["testpack"],
            "definitions": [],
            "build_path": "/tmp/build123"  # Volatile!
        }
        with open(pack_dir / "pack.json", 'w') as f:
            json.dump(pack_json, f)
        
        (pack_dir / "definitions").mkdir()
        
        errors = gate_a_pack_integrity({"testpack": pack_dir})
        
        assert any(e.code == "VOLATILE_FIELD_DETECTED" for e in errors)
    
    def test_gate_a_rejects_missing_definitions_dir(self, tmp_path):
        """Pack without definitions/ directory fails Gate A."""
        pack_dir = tmp_path / "testpack"
        pack_dir.mkdir()
        
        pack_json = {
            "pack_id": "testpack",
            "version": "1.0.0",
            "namespaces_owned": ["testpack"],
            "definitions": []
        }
        with open(pack_dir / "pack.json", 'w') as f:
            json.dump(pack_json, f)
        
        errors = gate_a_pack_integrity({"testpack": pack_dir})
        
        assert any(e.code == "DEFINITIONS_DIR_MISSING" for e in errors)


class TestGateBCeremonyDeterminism:
    """Test Gate B: Ceremony Determinism."""
    
    def test_gate_b_passes_valid_transcript(self):
        """Valid transcript passes Gate B."""
        t = ValidationTranscript()
        t.record_step("hash_check", "pack1", ValidationOutcome.PASS, include_timestamp=False)
        t.record_step("namespace_check", "pack1", ValidationOutcome.PASS, include_timestamp=False)
        
        errors = gate_b_ceremony_determinism(t)
        
        assert len(errors) == 0
    
    def test_gate_b_detects_machine_specific_data(self):
        """Transcript with machine-specific data fails Gate B."""
        t = ValidationTranscript()
        t.record_step(
            "test_step",
            "pack1",
            ValidationOutcome.FAIL,
            error_code="ERROR",
            context={"path": "/tmp/build/pack1"},  # Machine-specific!
            include_timestamp=False
        )
        
        errors = gate_b_ceremony_determinism(t)
        
        assert len(errors) > 0
        assert any(e.code == "MACHINE_SPECIFIC_DATA" for e in errors)
    
    def test_gate_b_detects_credentials(self):
        """Transcript with credentials fails Gate B."""
        t = ValidationTranscript()
        t.record_step(
            "test_step",
            "pack1",
            ValidationOutcome.PASS,
            context={"api_key": "secret123"},  # Credential!
            include_timestamp=False
        )
        
        errors = gate_b_ceremony_determinism(t)
        
        assert len(errors) > 0
        assert any(e.code == "CREDENTIAL_IN_TRANSCRIPT" for e in errors)
    
    def test_gate_b_validates_sequence_ordering(self):
        """Out-of-order sequence numbers fail Gate B."""
        t = ValidationTranscript()
        t.record_step("test1", "pack1", ValidationOutcome.PASS, include_timestamp=False)
        t.record_step("test2", "pack1", ValidationOutcome.PASS, include_timestamp=False)
        
        # Manually corrupt sequence
        t.entries[1].sequence_number = 99
        
        errors = gate_b_ceremony_determinism(t)
        
        assert any(e.code == "SEQUENCE_OUT_OF_ORDER" for e in errors)


class TestGateCAdmissionCompatibility:
    """Test Gate C: Admission Compatibility."""
    
    def test_gate_c_passes_no_collisions(self):
        """No namespace collisions passes Gate C."""
        packs_namespaces = {
            "identity": ["identity"],
            "base60": ["numeric.base60"]
        }
        
        new_packs = [
            {"pack_id": "identity", "version": "0.2.0"},
            {"pack_id": "base60", "version": "0.2.0"}
        ]
        
        errors = gate_c_admission_compatibility(None, new_packs, packs_namespaces)
        
        assert len(errors) == 0
    
    def test_gate_c_detects_namespace_collision(self):
        """Namespace collision fails Gate C."""
        packs_namespaces = {
            "pack1": ["shared"],
            "pack2": ["shared"]  # Collision!
        }
        
        new_packs = [
            {"pack_id": "pack1", "version": "1.0.0"},
            {"pack_id": "pack2", "version": "1.0.0"}
        ]
        
        errors = gate_c_admission_compatibility(None, new_packs, packs_namespaces)
        
        assert len(errors) > 0
        assert any(e.code == "NAMESPACE_COLLISION" for e in errors)
        collision_error = next(e for e in errors if e.code == "NAMESPACE_COLLISION")
        assert "shared" in collision_error.context["namespace"]
    
    def test_gate_c_enforces_version_monotonicity(self):
        """Version downgrade fails Gate C."""
        # Old active set with identity v0.2.0
        old_active_set = ActiveSet(
            version="1.0.0",
            packs=[
                PackDeclaration(
                    pack_id="identity",
                    version="0.2.0",
                    content_hash="sha256:abc123"
                )
            ]
        )
        
        # New pack tries to use v0.1.0 (downgrade!)
        new_packs = [
            {"pack_id": "identity", "version": "0.1.0"}
        ]
        
        packs_namespaces = {
            "identity": ["identity"]
        }
        
        errors = gate_c_admission_compatibility(old_active_set, new_packs, packs_namespaces)
        
        assert len(errors) > 0
        assert any(e.code == "VERSION_MONOTONICITY_VIOLATION" for e in errors)
    
    def test_gate_c_allows_version_increase(self):
        """Version increase passes Gate C."""
        old_active_set = ActiveSet(
            version="1.0.0",
            packs=[
                PackDeclaration(
                    pack_id="identity",
                    version="0.2.0",
                    content_hash="sha256:abc123"
                )
            ]
        )
        
        new_packs = [
            {"pack_id": "identity", "version": "0.3.0"}
        ]
        
        packs_namespaces = {
            "identity": ["identity"]
        }
        
        errors = gate_c_admission_compatibility(old_active_set, new_packs, packs_namespaces)
        
        assert len(errors) == 0
    
    def test_gate_c_rejects_same_version(self):
        """Same version (V' = V) fails Gate C."""
        old_active_set = ActiveSet(
            version="1.0.0",
            packs=[
                PackDeclaration(
                    pack_id="identity",
                    version="0.2.0",
                    content_hash="sha256:abc123"
                )
            ]
        )
        
        new_packs = [
            {"pack_id": "identity", "version": "0.2.0"}  # Same version!
        ]
        
        packs_namespaces = {
            "identity": ["identity"]
        }
        
        errors = gate_c_admission_compatibility(old_active_set, new_packs, packs_namespaces)
        
        assert len(errors) > 0
        assert any(e.code == "VERSION_MONOTONICITY_VIOLATION" for e in errors)


class TestRunAllGates:
    """Test integrated gate execution."""
    
    def test_run_all_gates_success(self, tmp_path):
        """All gates passing returns success."""
        # Setup valid pack
        pack_dir = tmp_path / "testpack"
        pack_dir.mkdir()
        
        pack_json = {
            "pack_id": "testpack",
            "version": "1.0.0",
            "name": "Test",
            "definitions": [],
            "namespaces_owned": ["testpack"]
        }
        with open(pack_dir / "pack.json", 'w') as f:
            json.dump(pack_json, f)
        
        (pack_dir / "definitions").mkdir()
        
        # Valid transcript
        t = ValidationTranscript()
        t.record_step("test", "testpack", ValidationOutcome.PASS, include_timestamp=False)
        
        # No collisions
        packs_namespaces = {"testpack": ["testpack"]}
        new_packs = [{"pack_id": "testpack", "version": "1.0.0"}]
        
        result = run_all_gates(
            {"testpack": pack_dir},
            t,
            None,
            new_packs,
            packs_namespaces
        )
        
        assert result["passed"] is True
        assert result["gates"]["A"] is True
        assert result["gates"]["B"] is True
        assert result["gates"]["C"] is True
        assert len(result["errors"]) == 0
    
    def test_run_all_gates_failure_stops_all(self, tmp_path):
        """Any gate failure causes overall failure."""
        # Invalid pack (missing definitions/)
        pack_dir = tmp_path / "testpack"
        pack_dir.mkdir()
        
        pack_json = {
            "pack_id": "testpack",
            "version": "1.0.0",
            "namespaces_owned": ["testpack"],
            "definitions": []
        }
        with open(pack_dir / "pack.json", 'w') as f:
            json.dump(pack_json, f)
        # No definitions/ directory!
        
        t = ValidationTranscript()
        t.record_step("test", "testpack", ValidationOutcome.PASS, include_timestamp=False)
        
        result = run_all_gates(
            {"testpack": pack_dir},
            t,
            None,
            [{"pack_id": "testpack", "version": "1.0.0"}],
            {"testpack": ["testpack"]}
        )
        
        assert result["passed"] is False
        assert result["gates"]["A"] is False  # Gate A should fail
        assert len(result["errors"]) > 0
