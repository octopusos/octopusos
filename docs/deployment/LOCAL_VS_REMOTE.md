# Extension System: Local vs Remote Deployment

## Deployment Modes

### Local-Only Mode (v1.0+)
**Status**: ✅ Production-Ready

**Characteristics**:
- Single user, localhost only (127.0.0.1)
- No network exposure
- User installs extensions for themselves
- Trust model: Self-trust (user trusts their own actions)

**Security Posture**:
- ✅ Core contracts enforced (no arbitrary code execution)
- ✅ Sandbox isolation (work dir, PATH, ENV)
- ✅ Audit logging
- ✅ SHA256 verification
- ⚠️ No admin token (not needed in single-user mode)

**Suitable For**:
- Personal productivity tools
- Development environments
- Local automation

---

### Remote-Exposed Mode (v1.1+)
**Status**: ⚠️ Requires Additional Hardening

**Characteristics**:
- Multi-user or network-accessible (0.0.0.0 or public IP)
- Multiple users may install extensions
- Trust model: Admin approval required

**Additional Requirements** (v1.1+):
- ✅ Admin token gate for install/uninstall/enable/disable
- ✅ Reverse proxy + authentication layer (nginx, Caddy, etc.)
- ✅ Audit log monitoring and alerting
- ✅ Rate limiting on extension operations
- ✅ IP whitelisting for admin operations

**Temporary Hardening** (v1.0 on Remote):
If you must deploy v1.0 remotely before v1.1:

1. **Reverse Proxy with Basic Auth**:
   ```nginx
   location /api/extensions {
       auth_basic "Admin Area";
       auth_basic_user_file /etc/nginx/.htpasswd;
       proxy_pass http://localhost:8000;
   }
   ```

2. **Firewall Rules**:
   ```bash
   # Only allow admin IPs to access extension API
   ufw allow from 192.168.1.100 to any port 8000
   ```

3. **Audit Log Monitoring**:
   ```bash
   # Alert on extension installs
   tail -f ~/.agentos/logs/system.log | grep "extension.*install"
   ```

**Suitable For** (v1.1+):
- Team collaboration tools
- Shared development environments
- Enterprise deployments

---

## Migration Path

### v1.0 → v1.1
When upgrading to v1.1 with admin token support:

1. Enable admin token in config:
   ```python
   REQUIRE_ADMIN_TOKEN = True
   ADMIN_TOKEN_SECRET = "generate-secure-token"
   ```

2. Existing installations remain enabled (grandfathered)

3. New operations require token:
   ```bash
   curl -X POST /api/extensions/install \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -F "file=@extension.zip"
   ```

---

## Security Trade-offs

| Aspect | Local-Only | Remote-Exposed (v1.0) | Remote-Exposed (v1.1+) |
|--------|------------|----------------------|----------------------|
| Admin Token | ⚠️ Not needed | ❌ Missing (risky) | ✅ Required |
| Core Contracts | ✅ Enforced | ✅ Enforced | ✅ Enforced |
| Audit Logs | ✅ Enabled | ✅ Enabled | ✅ Enabled + Monitoring |
| Trust Model | Self-trust | ⚠️ Trust all users | ✅ Admin approval |
| Production Ready | ✅ Yes | ⚠️ Use temp hardening | ✅ Yes |

---

## Recommendation

**For v1.0**:
- ✅ Deploy to localhost (127.0.0.1) only
- ✅ Single-user scenarios
- ⚠️ If must expose remotely: use nginx + basic auth

**For v1.1+**:
- ✅ Deploy to any network
- ✅ Multi-user scenarios
- ✅ Admin token enforcement built-in
