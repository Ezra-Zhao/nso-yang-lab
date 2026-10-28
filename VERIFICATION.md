# VERIFICATION — nso-yang-lab

> **Declaration: this proof artifact is an NSO-style simulation,
> not real Cisco NSO.** No Cisco NSO software was downloaded,
> installed, or run; no NED was used; no device was configured.
> Everything below was actually executed locally on 2026-10-27
> (America/Los_Angeles) unless it is explicitly described as a web
> finding.

## 1. Attempt at the official path (real NSO) — where it stopped

Steps actually taken:

1. Checked the local environment: no NSO present.
   `which ncs` / `which ncs_cli` → not found; no `~/nso-*`
   installation directory; no Cisco/DevNet credentials in the
   environment.
2. Fetched Cisco's official NSO page (HTTP 200, page loads
   anonymously):
   `https://developer.cisco.com/site/nso/`
3. Checked how the free copy and the sandbox are actually gated,
   from Cisco/DevNet-facing sources:
   - The free NSO download is an *evaluation* copy under a
     click-to-accept licence: "it is available to download from
     DevNet, but only for non-production use. Although the terms of
     the download are outlined under a click-to-accept license…"
     (PyNet Labs summary of the DevNet offer). Downloading therefore
     requires signing in with a Cisco account **and personally
     accepting that licence**.
   - DevNet sandboxes likewise require an account: "You must have
     a DevNet account in order to use the Control Center sandbox"
     (Cisco DevNet docs); sandbox landing pages prompt "create your
     free DevNet account or login to the Sandbox".
   - Production NED packages are further gated: Cisco's own NSO
     documentation says to download them "from software.cisco.com
     using the URLs provided on your NED license certificates".

**Blocker, stated plainly:** obtaining real NSO requires (a) a
Cisco CCO/DevNet account and (b) personal acceptance of Cisco's
evaluation licence. No such account exists in this environment,
and registering an account / accepting a licence on someone else's
behalf was outside the authorised scope of this task. Per the task
rules the attempt stopped there — no licence was bypassed and no
unofficial copy was sought. Work proceeded on the fallback
(NSO-style simulation) path described in `README.md`.

What would unblock the official path: the candidate signs in at
developer.cisco.com with their own Cisco account, accepts the NSO
evaluation licence, and downloads the `.signed.bin` installer (or
reserves the DevNet NSO sandbox) — after which this lab's YANG
model is the natural first service package to load.

## 2. YANG model validation (pyang)

Environment: `python3 -m venv /tmp/nso-venv`,
`/tmp/nso-venv/bin/pip install pyang pytest` → pyang 2.7.1.

```
$ pyang --version
pyang 2.7.1

$ pyang models/site-service.yang
exit code: 0  (no output = no errors or warnings)
```

Full command/output archive, including `pyang -f tree` output
(showing the `leafref` as `-> /network/device/name`):
`models/pyang-validation.txt`.

## 3. Demo run

Command (renderer/demo need only the Python standard library):

```
$ python3 demo.py
NSO-style provisioning demo (SIMULATION - not real Cisco NSO)
flow: service data (YANG-shaped JSON) -> validate -> render per-device CLI

--- apply service from service-branch-beta.json ---
! === device: R2 (target format: Cisco IOS-style CLI, text only) ===
vlan 220
 name BETA-LTD_VLAN220
!
interface Vlan220
 description Service branch-beta customer beta-ltd device R2
 ip address 10.220.0.1 255.255.255.0
 no shutdown
!
ip route 10.200.0.0 255.255.255.0 10.220.0.254
!

--- apply service from service-site-alpha.json ---
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
ip route 172.16.50.0 255.255.255.0 10.110.0.253
!
demo OK: all example services validated and rendered
```

Exit code: 0.

## 4. Automated tests (pytest)

Command:

```
$ PATH=/tmp/nso-venv/bin:$PATH /tmp/nso-venv/bin/python -m pytest tests/ -v
```

Result (pytest 9.2.0 in the venv, Python 3.12.3):

```
collected 6 items

tests/test_nso_lab.py::test_yang_model_validates_with_pyang PASSED       [ 16%]
tests/test_nso_lab.py::test_render_alpha_contains_expected_lines PASSED  [ 33%]
tests/test_nso_lab.py::test_render_beta_targets_its_own_device_and_vlan PASSED [ 50%]
tests/test_nso_lab.py::test_missing_mandatory_leaf_is_rejected PASSED    [ 66%]
tests/test_nso_lab.py::test_out_of_range_vlan_id_is_rejected PASSED      [ 83%]
tests/test_nso_lab.py::test_bad_example_file_missing_customer_is_rejected PASSED [100%]

============================== 6 passed in 0.24s ===============================
```

Coverage, as required:
① YANG model passes pyang validation (test 1);
② renderer output for both example instances contains the expected
configuration lines — VLAN, SVI address/netmask, static routes
(tests 2–3);
③ bad data is rejected — missing mandatory `customer` leaf (in
memory and from a file) and an out-of-range `vlan-id` both raise
`ServiceDataError` (tests 4–6).

## 5. Scope confirmation

- Files were added **only** under `nso-yang-lab/` inside
  `net-assurance-lab`; no pre-existing file in that repository was
  modified (`git status` shows only the untracked `nso-yang-lab/`
  directory). Nothing was committed or pushed.
- Toolchain honesty: pyang/pytest were installed into a throwaway
  venv at `/tmp/nso-venv` (this system's Python is externally
  managed, so a plain `pip install --user` is refused); the lab
  itself depends only on the Python standard library at runtime.
