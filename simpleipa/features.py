from dataclasses import dataclass

@dataclass(frozen=True)
class Feature:
    key: str
    title: str
    description: str
    roles: tuple[str, ...]
    dependencies: tuple[str, ...] = ()

FEATURES = {
    "users_and_groups": Feature("users_and_groups", "User and group management",
        "Manage identities, groups and memberships.", ("server",)),
    "dns": Feature("dns", "DNS management",
        "Manage authoritative identity-domain DNS zones and records.", ("server",)),
    "certificates": Feature("certificates", "Certificate management",
        "Issue, renew and revoke certificates through the PKI service.", ("server",)),
    "linux_clients": Feature("linux_clients", "Linux client management",
        "Enrol and manage supported Ubuntu and Debian clients.", ("server",)),
    "ssh_keys": Feature("ssh_keys", "SSH key management",
        "Publish centrally managed SSH public keys.", ("server", "client"),
        ("users_and_groups",)),
    "sudo_rules": Feature("sudo_rules", "Sudo permissions",
        "Manage centrally defined sudo rules.", ("server", "client"),
        ("users_and_groups",)),
    "smb_client": Feature("smb_client", "SMB client access",
        "Configure Linux clients to access SMB shares.", ("client",),
        ("linux_clients",)),
    "smb_server": Feature("smb_server", "Samba file-server integration",
        "Configure a separate Samba host as an identity-domain member.", ("server",),
        ("users_and_groups",)),
}

DEFAULT_SERVER_FEATURES = (
    "users_and_groups", "dns", "certificates",
    "linux_clients", "ssh_keys", "sudo_rules",
)
SERVER_PLATFORMS = ("rocky", "almalinux")
CLIENT_PLATFORMS = ("ubuntu", "debian")
