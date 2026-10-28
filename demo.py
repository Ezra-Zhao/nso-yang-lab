#!/usr/bin/env python3
"""One-command demo of the NSO-style provisioning flow (simulation).

    python3 demo.py

For each example service instance in examples/:
  1. load the service data (JSON form of the YANG model),
  2. validate it against the rules in models/site-service.yang,
  3. render the per-device IOS-style CLI configuration.

This stands in for an NSO provisioning transaction: service data in,
device configuration out. No real NSO, no real device, text only.
"""

from __future__ import annotations

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from renderer.render import render_file  # noqa: E402


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    examples = sorted(glob.glob(os.path.join(here, "examples", "*.json")))
    if not examples:
        print("no example service instances found", file=sys.stderr)
        return 1

    print("NSO-style provisioning demo (SIMULATION - not real Cisco NSO)")
    print("flow: service data (YANG-shaped JSON) -> validate -> render "
          "per-device CLI")
    for path in examples:
        print()
        print(f"--- apply service from {os.path.basename(path)} ---")
        print(render_file(path))
    print("demo OK: all example services validated and rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
