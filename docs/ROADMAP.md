# Roadmap

## Foundation
- [x] Feature registry and dependency-aware dry-run planner
- [x] FastAPI and React dashboard foundation
- [x] Authenticated user/group management API boundary
- [x] FreeIPA JSON-RPC adapter foundation (mock-tested; live realm validation pending)
- [x] Rocky/AlmaLinux server preflight and guided interactive installation wrapper
- [x] FreeIPA service status health check
- [x] Authenticated DNS zone and A/AAAA/CNAME/TXT record API (mock-tested; live DNS validation pending)
- [x] Authenticated Dogtag certificate inventory and CSR request API (mock-tested; live CA validation pending)
- [x] Dashboard certificate request and inventory screens

## Next
- [ ] Execute disposable KVM/libvirt integration lab on Rocky Linux and AlmaLinux, with Ubuntu and Debian clients
- [ ] Add end-to-end DNS, Kerberos, TLS and client-enrolment acceptance checks
- [x] Add dashboard DNS zone and record management screens
- [ ] Add safe backup/restore and documented recovery workflow
- [x] Add guarded interactive Ubuntu/Debian client enrolment wrapper
- [ ] Execute real Ubuntu/Debian client enrolment in the disposable VM lab
- [ ] Add multi-administrator RBAC, audit trail and production session hardening
- [ ] Add replica and upgrade workflows

## Optional
- [ ] SMB client access
- [ ] Samba file-server domain-member integration
