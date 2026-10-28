# nso-yang-lab — NSO-Style Service Modelling & Rendering (Simulation)

> **Honesty statement, up front:** This lab is an **NSO-style
> simulation**, not real Cisco NSO. No NSO instance was installed or
> run, no NED was loaded, and no real or virtual network device was
> configured. It demonstrates the *method* of NSO service
> orchestration — YANG service model → service data → template
> rendering → per-device configuration — reproduced locally with
> open tooling (pyang + Python standard library). See
> `VERIFICATION.md` for the attempt to obtain real NSO and exactly
> where that path stopped.

## Purpose

Cisco NSO (Network Services Orchestrator) provisions network
services by:

1. describing the service in a **YANG service model**,
2. accepting **service data** that conforms to that model into its
   Configuration Database (CDB), with the model itself enforcing
   mandatory leafs, ranges and references,
3. mapping service data to device configuration through a **service
   template / service-mapping code**,
4. translating the device-neutral result into device-native syntax
   through a **NED** (Network Element Driver), inside a single
   **provisioning transaction** that either commits everywhere or
   rolls back.

This lab reproduces that same flow, step for step, at the smallest
useful scale: one simplified service — a site VLAN with an SVI
gateway plus static routes — modelled in YANG, validated with
pyang, and rendered to Cisco IOS-style CLI text by a small Python
renderer.

## Correspondence with real NSO

| Real Cisco NSO concept | This lab's stand-in | Where |
|---|---|---|
| Service model (YANG package, service point list) | YANG module `site-service`: `list site-service` with key leaf, `mandatory true` leafs, ranges, defaults | `models/site-service.yang` |
| Device inventory (`/devices/device`, populated via NEDs) | Minimal `container network / list device` in the same module, present so the service's `device` leaf can be a real `leafref` | `models/site-service.yang` |
| CDB schema validation (mandatory / range / leafref enforced by NSO itself) | pyang validates the model; the renderer's `validate_service()` enforces the model's mandatory/range rules on instance data and rejects bad data | `renderer/render.py` |
| Service template / FASTMAP mapping logic | `string.Template` blocks (`VLAN_TEMPLATE`, `ROUTE_TEMPLATE`) filled from service data | `renderer/render.py` |
| NED (device-native syntax per platform) | The renderer's output format: Cisco IOS-style CLI text. The NED's role here is only a *target-format specification* — the emitted text is what an IOS NED would be asked to produce; no NED code exists in this lab | renderer output (see `demo.py`) |
| Provisioning transaction (commit / dry-run across devices) | `demo.py` "apply" step: loads each example service, validates it, and renders the per-device configuration in order. It is a dry-run in spirit — output is printed, nothing is sent anywhere | `demo.py` |
| Service instance data (NETCONF/XML or JSON in CDB) | Two example instances in JSON (JSON encoding of the YANG data) | `examples/service-site-alpha.json`, `examples/service-branch-beta.json` |

## Layout

```
nso-yang-lab/
├── README.md                  this file
├── VERIFICATION.md            evidence: real-NSO attempt, pyang, demo, pytest
├── demo.py                    one-command demo (apply all examples)
├── models/
│   ├── site-service.yang      the YANG service model
│   └── pyang-validation.txt   archived pyang command + output
├── examples/
│   ├── service-site-alpha.json    service instance 1 (R1, VLAN 110)
│   └── service-branch-beta.json   service instance 2 (R2, VLAN 220)
├── renderer/
│   ├── __init__.py
│   └── render.py              validation + template rendering (stdlib only)
└── tests/
    └── test_nso_lab.py        pytest: pyang, rendering, bad-data rejection
```

## Run it

The renderer and demo use **only the Python standard library**
(templates use `string.Template`, so no Jinja2 dependency is
needed). pyang and pytest are only needed for validation/tests:

```bash
python3 -m venv /tmp/nso-venv
/tmp/nso-venv/bin/pip install pyang pytest

cd nso-yang-lab
/tmp/nso-venv/bin/pyang models/site-service.yang   # model validation
python3 demo.py                                    # full flow, stdlib only
PATH=/tmp/nso-venv/bin:$PATH /tmp/nso-venv/bin/python -m pytest tests/ -v
```

`demo.py` prints, for each example, a block like:

```
! === device: R1 (target format: Cisco IOS-style CLI, text only) ===
vlan 110
 name ALPHA_USERS
!
interface Vlan110
 description Service site-alpha customer alpha-corp device R1
 ip address 10.110.0.1 255.255.255.0
 no shutdown
!
ip route 10.200.0.0 255.255.255.0 10.110.0.254
```

## Boundaries (what this lab is not)

- **Not real NSO.** The YANG module has never been compiled into an
  NSO package, loaded with `packages reload`, or committed through
  NSO's CLI/NETCONF/RESTCONF interfaces.
- **No real devices, no NEDs.** Output is unverified CLI text; it
  has not been applied to, or checked against, any router or switch.
- **Validation is partial by design.** pyang proves the *model* is
  well-formed. Instance-data checks in the renderer cover the
  model's mandatory leafs, the VLAN/prefix ranges and address
  formats; they are a hand-written stand-in for CDB validation, not
  a full YANG instance validator (a tool such as yanglint with
  instance data would be the next step up).
- **Simplifications vs. a production NSO service:** single target
  device per service (real services usually reference device
  groups), no service re-deploy / partial-sync semantics, no
  transaction rollback, no operational data or actions/RPCs.
- The model defines its own `ipv4-address` typedef so it validates
  standalone; a production model would import `ietf-inet-types`.

## Why the fallback path was taken

A free NSO evaluation does exist on Cisco DevNet, and DevNet
sandboxes exist — but both sit behind a Cisco (CCO/DevNet) account
and a click-to-accept licence, and production NEDs sit behind
software.cisco.com licence certificates. No Cisco account was
available in this environment, and creating one / accepting the
licence on the candidate's behalf was out of scope, so no NSO
download was performed. The exact findings are recorded in
`VERIFICATION.md`. Nothing was obtained from any unofficial source.
