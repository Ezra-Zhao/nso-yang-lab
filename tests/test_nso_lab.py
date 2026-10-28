"""Tests for the NSO-style lab (simulation, not real Cisco NSO).

Covers:
  1. the YANG model validates with pyang,
  2. the renderer produces the expected configuration lines for
     both example service instances,
  3. bad data (a missing mandatory leaf, an out-of-range VLAN ID)
     is rejected instead of rendered.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

LAB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LAB_ROOT)

from renderer.render import ServiceDataError, render_file, render_service  # noqa: E402

MODEL = os.path.join(LAB_ROOT, "models", "site-service.yang")
EXAMPLE_ALPHA = os.path.join(LAB_ROOT, "examples", "service-site-alpha.json")
EXAMPLE_BETA = os.path.join(LAB_ROOT, "examples", "service-branch-beta.json")


def _pyang_command() -> list[str]:
    exe = shutil.which("pyang")
    if exe:
        return [exe]
    return [sys.executable, "-m", "pyang"]


def test_yang_model_validates_with_pyang():
    result = subprocess.run(
        _pyang_command() + [MODEL],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"pyang failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_render_alpha_contains_expected_lines():
    out = render_file(EXAMPLE_ALPHA)
    assert "vlan 110" in out
    assert "name ALPHA_USERS" in out
    assert "interface Vlan110" in out
    assert "ip address 10.110.0.1 255.255.255.0" in out
    assert "no shutdown" in out
    assert "ip route 10.200.0.0 255.255.255.0 10.110.0.254" in out
    assert "ip route 172.16.50.0 255.255.255.0 10.110.0.253" in out


def test_render_beta_targets_its_own_device_and_vlan():
    out = render_file(EXAMPLE_BETA)
    assert "device: R2" in out
    assert "vlan 220" in out
    assert "interface Vlan220" in out
    assert "ip address 10.220.0.1 255.255.255.0" in out
    assert "ip route 10.200.0.0 255.255.255.0 10.220.0.254" in out


def test_missing_mandatory_leaf_is_rejected():
    bad = {
        "name": "broken-service",
        # "customer" omitted: declared mandatory true in the YANG model
        "device": "R1",
        "vlan-id": 110,
        "gateway": "10.110.0.1",
    }
    with pytest.raises(ServiceDataError, match="customer"):
        render_service(bad)


def test_out_of_range_vlan_id_is_rejected():
    bad = {
        "name": "broken-service",
        "customer": "alpha-corp",
        "device": "R1",
        "vlan-id": 5000,  # YANG range is 1..4094
        "gateway": "10.110.0.1",
    }
    with pytest.raises(ServiceDataError, match="vlan-id"):
        render_service(bad)


def test_bad_example_file_missing_customer_is_rejected(tmp_path):
    import json

    data = {
        "site-service": [
            {
                "name": "broken-from-file",
                "device": "R1",
                "vlan-id": 110,
                "gateway": "10.110.0.1",
            }
        ]
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ServiceDataError, match="customer"):
        render_file(str(path))
