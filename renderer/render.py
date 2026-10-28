"""NSO-style service renderer (SIMULATION - not real Cisco NSO).

Reads one service instance that conforms (by convention, checked
here in code) to ``models/site-service.yang``, validates the
mandatory leafs the YANG model declares, and renders Cisco IOS-style
CLI text for the target device.

What this mirrors in real NSO:
  * YANG ``mandatory true`` leafs        -> REQUIRED_FIELDS check below
  * NSO service template / FASTMAP logic -> the string.Template blocks
  * A NED's device-side syntax           -> the IOS CLI emitted here
  * A provisioning transaction           -> demo.py applying every
                                            example in order and
                                            printing the result

What it does NOT do: talk to NSO, CDB, NETCONF, or any real device.
Output is text only; nothing is pushed anywhere.
"""

from __future__ import annotations

import ipaddress
import json
from string import Template

# Leafs declared "mandatory true" (or key leafs) in site-service.yang.
REQUIRED_FIELDS = ("name", "customer", "device", "vlan-id", "gateway")

VLAN_TEMPLATE = Template(
    """\
vlan $vlan_id
 name $vlan_name
!
interface Vlan$vlan_id
 description Service $service_name customer $customer device $device
 ip address $gateway $netmask
 $svi_state
!"""
)

ROUTE_TEMPLATE = Template(
    "ip route $destination $netmask $next_hop"
)


class ServiceDataError(ValueError):
    """Raised when service data violates the YANG model's rules."""


def validate_service(service: dict) -> None:
    """Enforce the mandatory/range rules declared in the YANG model.

    Real NSO does this validation in CDB from the YANG schema itself.
    This function is the local stand-in and exists so bad data fails
    loudly instead of rendering a half-formed configuration.
    """
    if not isinstance(service, dict):
        raise ServiceDataError("service instance must be a JSON object")

    for field in REQUIRED_FIELDS:
        value = service.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ServiceDataError(
                f"missing mandatory leaf: {field} "
                f"(declared 'mandatory true' / key in site-service.yang)"
            )

    vlan_id = service["vlan-id"]
    if not isinstance(vlan_id, int) or not (1 <= vlan_id <= 4094):
        raise ServiceDataError(
            f"vlan-id out of range 1..4094: {vlan_id!r}"
        )

    prefix_length = service.get("subnet-prefix-length", 24)
    if not isinstance(prefix_length, int) or not (0 <= prefix_length <= 32):
        raise ServiceDataError(
            f"subnet-prefix-length out of range 0..32: {prefix_length!r}"
        )

    # Raises ValueError (AddressValueError) on a malformed address.
    try:
        ipaddress.IPv4Address(service["gateway"])
    except ValueError as exc:
        raise ServiceDataError(f"invalid gateway address: {exc}") from exc

    for route in service.get("static-routes", []):
        if not route.get("next-hop"):
            raise ServiceDataError(
                "static-route missing mandatory leaf: next-hop "
                f"(route: {route!r})"
            )
        if not route.get("destination-prefix"):
            raise ServiceDataError(
                f"static-route missing key leaf: destination-prefix "
                f"(route: {route!r})"
            )
        try:
            ipaddress.IPv4Address(route["destination-prefix"])
            ipaddress.IPv4Address(route["next-hop"])
        except ValueError as exc:
            raise ServiceDataError(
                f"invalid address in static-route: {exc}"
            ) from exc


def _netmask(prefix_length: int) -> str:
    return str(ipaddress.IPv4Network(f"0.0.0.0/{prefix_length}").netmask)


def render_service(service: dict) -> str:
    """Render one validated service instance to IOS-style CLI text."""
    validate_service(service)

    vlan_id = service["vlan-id"]
    prefix_length = service.get("subnet-prefix-length", 24)
    vlan_name = service.get("vlan-name") or (
        service["customer"].upper().replace(" ", "_") + f"_VLAN{vlan_id}"
    )
    enabled = service.get("enabled", True)

    lines = [
        f"! === device: {service['device']} "
        f"(target format: Cisco IOS-style CLI, text only) ===",
        VLAN_TEMPLATE.substitute(
            vlan_id=vlan_id,
            vlan_name=vlan_name,
            service_name=service["name"],
            customer=service["customer"],
            device=service["device"],
            gateway=service["gateway"],
            netmask=_netmask(prefix_length),
            svi_state="no shutdown" if enabled else "shutdown",
        ),
    ]

    for route in service.get("static-routes", []):
        route_prefix = route.get("prefix-length", 24)
        lines.append(
            ROUTE_TEMPLATE.substitute(
                destination=route["destination-prefix"],
                netmask=_netmask(route_prefix),
                next_hop=route["next-hop"],
            )
        )
    if service.get("static-routes"):
        lines.append("!")

    return "\n".join(lines)


def load_service(path: str) -> dict:
    """Load one service instance (JSON form of the YANG data)."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    services = data.get("site-service")
    if not services or not isinstance(services, list):
        raise ServiceDataError(
            f"{path}: expected a top-level 'site-service' list"
        )
    return services[0]


def render_file(path: str) -> str:
    return render_service(load_service(path))
