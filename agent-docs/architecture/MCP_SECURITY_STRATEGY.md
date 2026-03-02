# MCP Security Strategy for Enterprise Deployment

**Version**: 1.0  
**Date**: January 2025  
**Classification**: Internal  

---

## Executive Summary

This document outlines a security strategy for deploying MCP (Model Context Protocol) servers in an enterprise environment while maintaining control over which AI/LLM providers can access corporate systems.

**Core Problem**: Enabling MCP-based AI tooling while preventing data leakage to unapproved third-party LLM providers.

**Solution**: A layered security approach using MCP Gateways, client authentication, network controls, and operational policies.

---

## Table of Contents

1. [Threat Model](#threat-model)
2. [Security Tiers Overview](#security-tiers-overview)
3. [Architecture](#architecture)
4. [Tier 1: Quick Wins](#tier-1-quick-wins-low-effort-high-impact)
5. [Tier 2: Standard Enterprise](#tier-2-standard-enterprise-medium-effort)
6. [Tier 3: High Security](#tier-3-high-security-significant-effort)
7. [Tier 4: Maximum Security](#tier-4-maximum-security-air-gapped)
8. [Implementation Roadmap](#implementation-roadmap)
9. [Vendor Comparison](#vendor-comparison)
10. [Appendix: Attack Vectors](#appendix-attack-vectors-from-wiz-research)

---

## Threat Model

### Assets to Protect
| Asset | Sensitivity | MCP Exposure |
|-------|-------------|--------------|
| Email content (Gmail) | High | Full read/write via MCP tools |
| Documents (Drive) | High | Full read/write via MCP tools |
| Calendar (meetings, attendees) | Medium | Full read/write via MCP tools |
| OAuth tokens | Critical | Stored in MCP server process |
| Internal business logic | Medium | Exposed via tool descriptions |

### Threat Actors
| Actor | Motivation | Capability |
|-------|------------|------------|
| Malicious LLM Provider | Data harvesting | Full visibility into prompts/responses |
| Compromised MCP Server | Credential theft | Access to OAuth tokens, filesystem |
| Malicious Employee | Data exfiltration | Intentional use of unapproved providers |
| Careless Employee | Convenience | Accidental use of personal API keys |
| External Attacker | Corporate espionage | Prompt injection, DNS rebinding |

### Primary Risks
1. **Shadow AI**: Employees routing corporate data through unapproved LLM providers
2. **Token Theft**: Malicious servers exfiltrating OAuth credentials
3. **Prompt Injection**: Untrusted content triggering dangerous tool execution
4. **Data Leakage**: Sensitive information sent to third-party AI services
5. **Audit Gap**: No visibility into what AI tools access what data

---

## Security Tiers Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SECURITY MATURITY LEVELS                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TIER 4: MAXIMUM SECURITY                                          ████████│
│  Air-gapped, self-hosted LLMs, hardware security                   ████████│
│  Effort: ██████████  Friction: ██████████  Protection: ██████████  ████████│
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  TIER 3: HIGH SECURITY                                          ██████████ │
│  MCP Gateway, mTLS, sandboxing, full audit                      ██████████ │
│  Effort: ████████░░  Friction: ██████░░░░  Protection: █████████░ ████████ │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  TIER 2: STANDARD ENTERPRISE                                  ████████████ │
│  OAuth gateway, approved providers, logging                   ████████████ │
│  Effort: ██████░░░░  Friction: ████░░░░░░  Protection: ███████░░░ ████████ │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  TIER 1: QUICK WINS                                         ██████████████ │
│  Network controls, policy, approved client list             ██████████████ │
│  Effort: ████░░░░░░  Friction: ██░░░░░░░░  Protection: █████░░░░░ ████████ │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  TIER 0: NO CONTROLS (Current State)                      ████████████████ │
│  Anyone can use any LLM with any MCP server               ████████████████ │
│  Effort: ░░░░░░░░░░  Friction: ░░░░░░░░░░  Protection: ░░░░░░░░░░         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Quick Reference: What Each Tier Provides

| Tier | Blocks Unapproved LLMs | Prevents Personal Keys | Audit Trail | Prompt Inspection | Token Protection |
|------|------------------------|------------------------|-------------|-------------------|------------------|
| 0    | ✗ | ✗ | ✗ | ✗ | ✗ |
| 1    | ◐ (policy only) | ◐ (policy only) | ◐ (basic) | ✗ | ✗ |
| 2    | ✓ | ✓ | ✓ | ◐ | ◐ |
| 3    | ✓ | ✓ | ✓ | ✓ | ✓ |
| 4    | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## Architecture

### Tier 1 Architecture (Quick Wins)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CORPORATE NETWORK                                    │
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │ Employee        │                                                        │
│  │ Workstation     │                                                        │
│  │                 │                                                        │
│  │ ┌─────────────┐ │                                                        │
│  │ │ Approved AI │ │         ┌─────────────────────────────────┐            │
│  │ │ Client      │─┼────────▶│  Approved LLM Providers         │            │
│  │ │ (Claude     │ │         │  (AWS Bedrock / GCP Vertex)     │            │
│  │ │  Code)      │ │         │                                 │            │
│  │ └─────────────┘ │         │  API Keys: Corporate-managed    │            │
│  │        │        │         └─────────────────────────────────┘            │
│  │        │        │                        │                               │
│  │        ▼        │                        ▼                               │
│  │ ┌─────────────┐ │         ┌─────────────────────────────────┐            │
│  │ │ MCP Server  │ │         │  MCP Server (Local Process)     │            │
│  │ │ (Local)     │◀┼─────────│  - Gmail tools                  │            │
│  │ └─────────────┘ │         │  - Drive tools                  │            │
│  └─────────────────┘         │  - Calendar tools               │            │
│                              └─────────────────────────────────┘            │
│                                                                             │
│  CONTROLS:                                                                  │
│  ├─ [POLICY] Acceptable Use Policy for AI tools                            │
│  ├─ [NETWORK] DNS blocking of unapproved LLM endpoints                      │
│  ├─ [CONFIG] Corporate-managed API keys distributed via MDM                 │
│  └─ [LOGGING] Basic access logs on MCP server                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Tier 2 Architecture (Standard Enterprise)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CORPORATE NETWORK                                    │
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │ Employee        │                                                        │
│  │ Workstation     │                                                        │
│  │                 │                                                        │
│  │ ┌─────────────┐ │      ┌─────────────────────────────────────────────┐   │
│  │ │ Approved AI │ │      │              AI PROXY / GATEWAY             │   │
│  │ │ Client      │─┼─────▶│                                             │   │
│  │ └─────────────┘ │      │  ┌─────────────────────────────────────┐    │   │
│  └─────────────────┘      │  │         SECURITY CONTROLS           │    │   │
│                           │  │                                     │    │   │
│  ✗ BLOCKED:               │  │  1. OAuth 2.1 Authentication        │    │   │
│  ├─ api.openai.com        │  │  2. Client ID Allowlist             │    │   │
│  ├─ api.anthropic.com     │  │  3. Request/Response Logging        │    │   │
│  ├─ Personal API keys     │  │  4. Rate Limiting                   │    │   │
│  └─ Unapproved clients    │  │                                     │    │   │
│                           │  └─────────────────────────────────────┘    │   │
│                           │                     │                        │   │
│                           │        ┌────────────┴────────────┐           │   │
│                           │        ▼                         ▼           │   │
│                           │  ┌───────────┐           ┌───────────┐       │   │
│                           │  │   AWS     │           │   GCP     │       │   │
│                           │  │  Bedrock  │           │  Vertex   │       │   │
│                           │  └─────┬─────┘           └─────┬─────┘       │   │
│                           │        └───────────┬───────────┘             │   │
│                           └────────────────────┼─────────────────────────┘   │
│                                                ▼                             │
│                           ┌─────────────────────────────────────────────┐   │
│                           │           MCP SERVER CLUSTER                │   │
│                           │                                             │   │
│                           │  ┌─────────┐ ┌─────────┐ ┌─────────────┐    │   │
│                           │  │  Gmail  │ │  Drive  │ │  Calendar   │    │   │
│                           │  │   MCP   │ │   MCP   │ │     MCP     │    │   │
│                           │  └─────────┘ └─────────┘ └─────────────┘    │   │
│                           │                                             │   │
│                           │  Registry: Internal approved servers only   │   │
│                           └─────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Tier 3 Architecture (High Security)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CORPORATE NETWORK (VPC)                              │
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │ Employee        │                                                        │
│  │ Workstation     │                                                        │
│  │ (MDM Managed)   │                                                        │
│  │                 │                                                        │
│  │ ┌─────────────┐ │                                                        │
│  │ │ Approved AI │ │      ┌─────────────────────────────────────────────┐   │
│  │ │ Client      │─┼─────▶│           MCP GATEWAY (HA Cluster)          │   │
│  │ │ + mTLS Cert │ │      │                                             │   │
│  │ └─────────────┘ │      │  ┌─────────────────────────────────────┐    │   │
│  └─────────────────┘      │  │      COMPREHENSIVE CONTROLS         │    │   │
│                           │  │                                     │    │   │
│  ✗ BLOCKED (Firewall):    │  │  1. mTLS Client Authentication      │    │   │
│  ├─ All public LLM APIs   │  │  2. OAuth 2.1 + OIDC Integration    │    │   │
│  ├─ Unapproved egress     │  │  3. Client/Provider Allowlist       │    │   │
│  └─ Non-corporate certs   │  │  4. Prompt Injection Detection      │    │   │
│                           │  │  5. PII/Secret Scanning             │    │   │
│                           │  │  6. Human-in-the-Loop Gates         │    │   │
│                           │  │  7. Full Request/Response Audit     │    │   │
│                           │  │  8. Anomaly Detection               │    │   │
│                           │  └─────────────────────────────────────┘    │   │
│                           │                     │                        │   │
│                           │        ┌────────────┴────────────┐           │   │
│                           │        ▼                         ▼           │   │
│                           │  ┌───────────┐           ┌───────────┐       │   │
│                           │  │   AWS     │           │   GCP     │       │   │
│                           │  │  Bedrock  │           │  Vertex   │       │   │
│                           │  │ (Private  │           │ (Private  │       │   │
│                           │  │  Link)    │           │  Connect) │       │   │
│                           │  └─────┬─────┘           └─────┬─────┘       │   │
│                           │        └───────────┬───────────┘             │   │
│                           └────────────────────┼─────────────────────────┘   │
│                                                ▼                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │              SANDBOXED MCP SERVER ENVIRONMENT                         │   │
│  │                                                                       │   │
│  │  ┌────────────────────────────────────────────────────────────────┐  │   │
│  │  │  Kubernetes Cluster (Isolated Namespace)                       │  │   │
│  │  │                                                                │  │   │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │  │   │
│  │  │  │   Pod:       │  │   Pod:       │  │   Pod:       │          │  │   │
│  │  │  │  Gmail MCP   │  │  Drive MCP   │  │ Calendar MCP │          │  │   │
│  │  │  │              │  │              │  │              │          │  │   │
│  │  │  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │          │  │   │
│  │  │  │ │ Container│ │  │ │ Container│ │  │ │ Container│ │          │  │   │
│  │  │  │ │ (gVisor) │ │  │ │ (gVisor) │ │  │ │ (gVisor) │ │          │  │   │
│  │  │  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │          │  │   │
│  │  │  │              │  │              │  │              │          │  │   │
│  │  │  │ Network:     │  │ Network:     │  │ Network:     │          │  │   │
│  │  │  │ Egress→GW    │  │ Egress→GW    │  │ Egress→GW    │          │  │   │
│  │  │  │ only         │  │ only         │  │ only         │          │  │   │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘          │  │   │
│  │  │                                                                │  │   │
│  │  │  Secrets: HashiCorp Vault (Dynamic OAuth tokens)               │  │   │
│  │  └────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                       │   │
│  │  ┌────────────────────────────────────────────────────────────────┐  │   │
│  │  │  Observability Stack                                           │  │   │
│  │  │  ├─ OpenTelemetry (Traces)                                     │  │   │
│  │  │  ├─ Prometheus (Metrics)                                       │  │   │
│  │  │  ├─ Loki (Logs)                                                │  │   │
│  │  │  └─ SIEM Integration (Splunk/Sentinel)                         │  │   │
│  │  └────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Tier 4 Architecture (Maximum Security / Air-Gapped)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AIR-GAPPED / HIGHLY RESTRICTED NETWORK                    │
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │ Secure          │                                                        │
│  │ Workstation     │                                                        │
│  │ (Hardened OS)   │                                                        │
│  │                 │                                                        │
│  │ ┌─────────────┐ │      ┌─────────────────────────────────────────────┐   │
│  │ │ Approved AI │ │      │           MCP GATEWAY (HA + HSM)            │   │
│  │ │ Client      │─┼─────▶│                                             │   │
│  │ │ + HW Token  │ │      │  All Tier 3 controls PLUS:                  │   │
│  │ └─────────────┘ │      │                                             │   │
│  └─────────────────┘      │  • Hardware Security Module (HSM)           │   │
│                           │  • Certificate-based auth (PIV/CAC)         │   │
│                           │  • Real-time DLP integration                │   │
│                           │  • Behavioral analytics                     │   │
│                           │  • Break-glass procedures                   │   │
│                           │                                             │   │
│  ✗ NO EXTERNAL            └──────────────────┬──────────────────────────┘   │
│    CONNECTIVITY                              │                              │
│                                              ▼                              │
│                           ┌─────────────────────────────────────────────┐   │
│                           │        SELF-HOSTED LLM CLUSTER              │   │
│                           │                                             │   │
│                           │  ┌─────────────────────────────────────┐    │   │
│                           │  │  On-Premise GPU Cluster             │    │   │
│                           │  │                                     │    │   │
│                           │  │  • Llama 3.1 405B (or similar)      │    │   │
│                           │  │  • vLLM / TGI serving               │    │   │
│                           │  │  • No external API calls            │    │   │
│                           │  │  • Full data sovereignty            │    │   │
│                           │  └─────────────────────────────────────┘    │   │
│                           │                     │                        │   │
│                           └─────────────────────┼────────────────────────┘   │
│                                                 ▼                            │
│                           ┌─────────────────────────────────────────────┐   │
│                           │     ISOLATED MCP SERVER ENVIRONMENT         │   │
│                           │                                             │   │
│                           │  • Air-gapped Kubernetes                    │   │
│                           │  • Hardware-isolated containers             │   │
│                           │  • Encrypted storage (LUKS + TPM)           │   │
│                           │  • Physical access controls                 │   │
│                           │                                             │   │
│                           └─────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tier 1: Quick Wins (Low Effort, High Impact)

**Timeline**: 1-2 weeks  
**Effort**: Low  
**Friction**: Minimal  
**Protection Level**: Basic but meaningful  

### Controls

| Control | Description | Effort | Impact |
|---------|-------------|--------|--------|
| **Acceptable Use Policy** | Document approved AI tools and LLM providers | 2 days | ★★★☆☆ |
| **DNS Blocking** | Block direct access to `api.openai.com`, `api.anthropic.com`, etc. | 1 day | ★★★★☆ |
| **Approved Client List** | Publish list of sanctioned AI clients (Claude Code, Cursor, etc.) | 1 day | ★★★☆☆ |
| **Corporate API Keys** | Distribute AWS Bedrock/GCP Vertex keys via MDM or secrets manager | 3 days | ★★★★☆ |
| **Basic Logging** | Enable access logging on MCP servers | 1 day | ★★★☆☆ |
| **MCP Server Registry** | Create internal list of approved MCP servers | 1 day | ★★★★☆ |

### Implementation

#### 1.1 DNS/Network Blocking
```bash
# Example: Block at corporate DNS or firewall
# Add to blocklist:
api.openai.com
api.anthropic.com
generativelanguage.googleapis.com  # Direct Gemini API
api.cohere.ai
api.mistral.ai
# ... other public LLM APIs

# ALLOW (via approved proxy only):
bedrock-runtime.*.amazonaws.com  # AWS Bedrock
*-aiplatform.googleapis.com      # GCP Vertex AI
```

#### 1.2 Corporate API Key Distribution
```yaml
# Example: Distribute via environment variables or config
# Managed by IT, not visible to end users

# For AWS Bedrock (via IAM role, not raw keys)
AWS_PROFILE: corporate-ai-profile
AWS_REGION: us-east-1

# For GCP Vertex (via service account)
GOOGLE_APPLICATION_CREDENTIALS: /etc/corp/vertex-sa.json
```

#### 1.3 Approved MCP Server Registry
```yaml
# internal-mcp-registry.yaml
approved_servers:
  - name: gws-mcp-advanced
    version: ">=1.0.0"
    source: internal
    maintainer: platform-team@company.com
    risk_level: low
    
  - name: internal-jira-mcp
    version: ">=2.1.0"
    source: internal
    maintainer: devtools@company.com
    risk_level: low

blocked_servers:
  - pattern: "npm:*"      # No random npm packages
  - pattern: "github:*"   # No unvetted GitHub repos
```

### What This Achieves
- ✓ Employees can't accidentally use personal OpenAI/Anthropic keys
- ✓ Basic audit trail of MCP usage
- ✓ Clear policy on approved tools
- ✗ Determined users can still bypass (VPN, mobile hotspot)
- ✗ No cryptographic enforcement

---

## Tier 2: Standard Enterprise (Medium Effort)

**Timeline**: 4-8 weeks  
**Effort**: Medium  
**Friction**: Low-Medium  
**Protection Level**: Strong  

### Controls

| Control | Description | Effort | Impact |
|---------|-------------|--------|--------|
| **AI Proxy/Gateway** | Central proxy for all LLM traffic | 2 weeks | ★★★★★ |
| **OAuth 2.1 Authentication** | Authenticate all AI clients via corporate IdP | 1 week | ★★★★★ |
| **Client Allowlist** | Cryptographically enforce approved clients | 3 days | ★★★★★ |
| **Centralized Key Management** | All API keys in Vault, never on endpoints | 1 week | ★★★★☆ |
| **Request/Response Logging** | Full audit trail of all AI interactions | 3 days | ★★★★☆ |
| **Egress Firewall** | Block all LLM traffic except through proxy | 2 days | ★★★★★ |

### Implementation

#### 2.1 Deploy AI Gateway

**Option A: Kong AI Gateway**
```yaml
# kong.yaml
plugins:
  - name: ai-proxy
    config:
      route_type: llm/v1/chat
      auth:
        header_name: Authorization
        header_value: "Bearer ${vault://aws-bedrock-key}"
      model:
        provider: bedrock
        name: anthropic.claude-3-sonnet
        
  - name: oauth2-introspection
    config:
      introspection_url: https://idp.company.com/oauth2/introspect
      client_id: ai-gateway
      client_secret: ${vault://oauth-secret}
      
  - name: acl
    config:
      allow:
        - approved-ai-clients
```

**Option B: Traefik AI Gateway**
```yaml
# traefik-mcp.yaml
http:
  middlewares:
    mcp-auth:
      plugin:
        mcp:
          jwt:
            issuer: https://idp.company.com
            audience: mcp-gateway
          tbac:
            policies:
              - match:
                  claims:
                    groups: ["ai-users"]
                action: allow
              - action: deny
```

**Option C: Microsoft MCP Gateway (Open Source)**
```yaml
# mcp-gateway-config.yaml
authentication:
  provider: entra-id
  tenant_id: ${AZURE_TENANT_ID}
  client_id: ${MCP_GATEWAY_CLIENT_ID}
  
authorization:
  roles:
    - name: ai-user
      permissions:
        - tools:read
        - tools:execute
    - name: ai-admin
      permissions:
        - tools:*
        - servers:*
        
allowed_clients:
  - client_id: claude-code-corp
    name: "Claude Code (Corporate)"
  - client_id: cursor-corp
    name: "Cursor (Corporate)"
```

#### 2.2 OAuth 2.1 Client Authentication
```python
# Pseudo-code for gateway authentication
async def authenticate_request(request: Request) -> AuthContext:
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    # Validate with corporate IdP
    claims = await idp.introspect(token)
    
    if not claims.get("active"):
        raise Unauthorized("Invalid or expired token")
    
    # Check client is in allowlist
    client_id = claims.get("client_id")
    if client_id not in APPROVED_CLIENTS:
        audit_log.warning(f"Blocked unapproved client: {client_id}")
        raise Forbidden(f"Client '{client_id}' not approved for AI access")
    
    # Check user has AI access
    if "ai-users" not in claims.get("groups", []):
        raise Forbidden("User not authorized for AI tools")
    
    return AuthContext(
        user_id=claims["sub"],
        client_id=client_id,
        scopes=claims.get("scope", "").split(),
    )
```

#### 2.3 Centralized Key Management
```hcl
# Vault policy for AI keys
path "secret/data/ai/aws-bedrock" {
  capabilities = ["read"]
  allowed_parameters = {
    "requester" = ["ai-gateway"]
  }
}

path "secret/data/ai/gcp-vertex" {
  capabilities = ["read"]
  allowed_parameters = {
    "requester" = ["ai-gateway"]
  }
}

# No direct access for users
path "secret/data/ai/*" {
  capabilities = ["deny"]
}
```

### What This Achieves
- ✓ Cryptographic enforcement of approved clients
- ✓ All LLM traffic flows through controlled gateway
- ✓ Full audit trail with user attribution
- ✓ API keys never exposed to end users
- ✓ Centralized policy enforcement
- ◐ Prompt content not yet inspected

---

## Tier 3: High Security (Significant Effort)

**Timeline**: 2-4 months  
**Effort**: High  
**Friction**: Medium  
**Protection Level**: Very Strong  

### Controls

| Control | Description | Effort | Impact |
|---------|-------------|--------|--------|
| **mTLS Client Auth** | Certificate-based client authentication | 2 weeks | ★★★★★ |
| **MCP Server Sandboxing** | Container isolation with gVisor/Kata | 3 weeks | ★★★★★ |
| **Prompt Injection Detection** | AI-powered guardrails on inputs | 2 weeks | ★★★★☆ |
| **PII/Secret Scanning** | Detect sensitive data in prompts | 1 week | ★★★★☆ |
| **Human-in-the-Loop** | Approval gates for destructive operations | 2 weeks | ★★★★☆ |
| **Private Connectivity** | AWS PrivateLink / GCP Private Connect | 2 weeks | ★★★★★ |
| **SIEM Integration** | Real-time security monitoring | 2 weeks | ★★★★☆ |
| **Anomaly Detection** | ML-based unusual behavior detection | 3 weeks | ★★★☆☆ |

### Implementation

#### 3.1 mTLS Client Authentication
```yaml
# Gateway mTLS configuration
tls:
  client_auth:
    mode: require
    ca_certificates:
      - /etc/certs/corporate-ca.pem
    
  # Only accept certs issued by corporate CA
  # with specific attributes
  client_cert_validation:
    required_ou: "AI-Approved-Clients"
    required_cn_pattern: "^(claude-code|cursor|continue)-corp$"
```

#### 3.2 MCP Server Sandboxing
```yaml
# Kubernetes pod security for MCP servers
apiVersion: v1
kind: Pod
metadata:
  name: gmail-mcp
  annotations:
    # Use gVisor for syscall filtering
    io.kubernetes.cri-o.userns-mode: "auto"
spec:
  runtimeClassName: gvisor
  
  securityContext:
    runAsNonRoot: true
    runAsUser: 65534
    fsGroup: 65534
    seccompProfile:
      type: RuntimeDefault
      
  containers:
    - name: mcp-server
      image: internal-registry/gws-mcp-advanced:1.0.0
      
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
          
      resources:
        limits:
          memory: "512Mi"
          cpu: "500m"
          
  # Network policy: only allow egress to gateway
  # Defined separately in NetworkPolicy resource
```

```yaml
# Network policy for MCP pods
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mcp-server-egress
spec:
  podSelector:
    matchLabels:
      app: mcp-server
  policyTypes:
    - Egress
  egress:
    # Only allow traffic to the MCP gateway
    - to:
        - podSelector:
            matchLabels:
              app: mcp-gateway
      ports:
        - port: 443
    # Allow DNS
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - port: 53
          protocol: UDP
```

#### 3.3 Prompt Injection Detection
```python
# Gateway guardrail middleware
from guardrails import PromptInjectionDetector, PIIScanner

async def inspect_request(request: MCPRequest) -> None:
    # Check for prompt injection attempts
    injection_score = await PromptInjectionDetector.analyze(
        request.prompt,
        threshold=0.8
    )
    
    if injection_score > 0.8:
        audit_log.alert(
            event="prompt_injection_detected",
            user=request.user_id,
            score=injection_score,
            prompt_hash=hash(request.prompt)
        )
        raise SecurityViolation("Potential prompt injection detected")
    
    # Scan for PII/secrets
    pii_findings = await PIIScanner.scan(request.prompt)
    
    if pii_findings.has_critical():
        audit_log.alert(
            event="pii_in_prompt",
            user=request.user_id,
            types=pii_findings.types
        )
        # Option: redact and continue, or block
        request.prompt = pii_findings.redacted_text
```

#### 3.4 Human-in-the-Loop for Destructive Operations
```python
# Tool classification and approval gates
DESTRUCTIVE_TOOLS = {
    "send_gmail_message": ApprovalLevel.NOTIFY,
    "delete_drive_file": ApprovalLevel.REQUIRE_APPROVAL,
    "delete_event": ApprovalLevel.REQUIRE_APPROVAL,
    "batch_modify_gmail_message_labels": ApprovalLevel.NOTIFY,
}

async def execute_tool(request: ToolRequest) -> ToolResponse:
    approval_level = DESTRUCTIVE_TOOLS.get(
        request.tool_name, 
        ApprovalLevel.AUTO_APPROVE
    )
    
    if approval_level == ApprovalLevel.REQUIRE_APPROVAL:
        # Send approval request to user's device
        approval = await request_user_approval(
            user_id=request.user_id,
            tool=request.tool_name,
            params=request.params,
            timeout_seconds=60
        )
        
        if not approval.granted:
            audit_log.info(f"User denied tool execution: {request.tool_name}")
            raise ToolExecutionDenied("User denied approval")
    
    elif approval_level == ApprovalLevel.NOTIFY:
        # Notify but don't block
        await notify_user(
            user_id=request.user_id,
            message=f"AI executed: {request.tool_name}"
        )
    
    return await execute_tool_internal(request)
```

#### 3.5 Private Connectivity (No Public Internet)
```hcl
# Terraform: AWS PrivateLink for Bedrock
resource "aws_vpc_endpoint" "bedrock" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.us-east-1.bedrock-runtime"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.bedrock_endpoint.id]
  private_dns_enabled = true
}

# GCP Private Service Connect for Vertex AI
resource "google_compute_global_address" "vertex_psc" {
  name          = "vertex-ai-psc"
  purpose       = "PRIVATE_SERVICE_CONNECT"
  address_type  = "INTERNAL"
  network       = google_compute_network.main.id
}
```

### What This Achieves
- ✓ Defense in depth with multiple security layers
- ✓ Compromised MCP server has limited blast radius
- ✓ Prompt injection attacks detected and blocked
- ✓ Sensitive data redacted before reaching LLM
- ✓ User approval for high-risk operations
- ✓ No data traverses public internet
- ✓ Full observability and alerting

---

## Tier 4: Maximum Security (Air-Gapped)

**Timeline**: 6-12 months  
**Effort**: Very High  
**Friction**: High  
**Protection Level**: Maximum  

### When to Use Tier 4
- Classified or highly regulated data (defense, healthcare, finance)
- Zero tolerance for data leaving your infrastructure
- Compliance requirements mandate air-gapping
- Nation-state threat actors in your threat model

### Additional Controls

| Control | Description | Effort | Impact |
|---------|-------------|--------|--------|
| **Self-Hosted LLM** | On-premise Llama/Mistral deployment | 2 months | ★★★★★ |
| **Hardware Security Modules** | HSM for all cryptographic operations | 1 month | ★★★★★ |
| **Physical Access Controls** | Biometric + badge for server rooms | 1 month | ★★★★☆ |
| **Air-Gap Network** | No internet connectivity | 2 weeks | ★★★★★ |
| **Hardware Tokens** | PIV/CAC cards for authentication | 1 month | ★★★★★ |
| **Real-time DLP** | Inline data loss prevention | 1 month | ★★★★☆ |
| **Behavioral Analytics** | UEBA for insider threat detection | 2 months | ★★★☆☆ |

### Self-Hosted LLM Options

| Model | Parameters | Hardware Required | Quality vs GPT-4 |
|-------|------------|-------------------|------------------|
| Llama 3.1 405B | 405B | 8x H100 (80GB) | ~95% |
| Llama 3.1 70B | 70B | 2x H100 (80GB) | ~85% |
| Mistral Large 2 | 123B | 4x H100 (80GB) | ~90% |
| Qwen 2.5 72B | 72B | 2x H100 (80GB) | ~85% |

```yaml
# Example: vLLM deployment for self-hosted LLM
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llama-3-405b
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: vllm
          image: vllm/vllm-openai:latest
          args:
            - --model=meta-llama/Llama-3.1-405B-Instruct
            - --tensor-parallel-size=8
            - --max-model-len=32768
          resources:
            limits:
              nvidia.com/gpu: 8
          volumeMounts:
            - name: model-cache
              mountPath: /root/.cache/huggingface
      nodeSelector:
        gpu-type: h100-80gb
```

### What This Achieves
- ✓ Complete data sovereignty - nothing leaves your infrastructure
- ✓ Immune to cloud provider breaches
- ✓ Meets strictest compliance requirements
- ✓ No dependency on external AI providers
- ✗ Significant infrastructure investment
- ✗ Model quality may lag frontier models
- ✗ Higher operational complexity

---

## Implementation Roadmap

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        IMPLEMENTATION TIMELINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MONTH 1                    MONTH 2-3                  MONTH 4-6            │
│  ────────                   ─────────                  ─────────            │
│                                                                             │
│  ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐  │
│  │   TIER 1        │        │   TIER 2        │        │   TIER 3        │  │
│  │   Quick Wins    │───────▶│   Standard      │───────▶│   High          │  │
│  │                 │        │   Enterprise    │        │   Security      │  │
│  └─────────────────┘        └─────────────────┘        └─────────────────┘  │
│                                                                             │
│  Week 1-2:                  Week 1-4:                  Week 1-4:            │
│  • Draft AI policy          • Deploy AI Gateway        • Implement mTLS     │
│  • DNS blocking             • OAuth integration        • Deploy sandboxing  │
│  • Approved client list     • Client allowlist         • Private endpoints  │
│                                                                             │
│  Week 3-4:                  Week 5-8:                  Week 5-8:            │
│  • Distribute corp keys     • Centralize keys          • Guardrails         │
│  • Enable basic logging     • Full audit logging       • PII scanning       │
│  • Create MCP registry      • Egress firewall          • HITL gates         │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  DECISION POINT: Evaluate if Tier 4 (air-gap) is required based on:        │
│  • Regulatory requirements                                                  │
│  • Data sensitivity classification                                          │
│  • Threat model assessment                                                  │
│  • Cost-benefit analysis                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Starting Point

For most enterprises with AWS/GCP contracts:

1. **Start with Tier 1** (Week 1-2)
   - Immediate risk reduction with minimal friction
   - Establishes policy foundation

2. **Progress to Tier 2** (Month 1-2)
   - Deploy AI Gateway (Kong, Traefik, or Microsoft MCP Gateway)
   - Integrate with existing IdP
   - This is the **minimum viable security** for production

3. **Evaluate Tier 3** (Month 3-6)
   - Based on incident patterns and compliance needs
   - Prioritize controls based on risk assessment

---

## Vendor Comparison

### MCP Gateway Solutions

| Vendor | Type | Auth | Sandboxing | Guardrails | Pricing |
|--------|------|------|------------|------------|---------|
| **Microsoft MCP Gateway** | OSS | Entra ID | K8s native | Basic | Free |
| **Kong AI Gateway** | Commercial | OAuth 2.0, OIDC | Plugin | Advanced | $$$$ |
| **Traefik MCP Gateway** | Commercial | JWT, OIDC | Docker | TBAC | $$$ |
| **TrueFoundry** | Commercial | OAuth | K8s | Advanced | $$$ |
| **Cloudflare MCP Portals** | SaaS | Zero Trust | Managed | Basic | $$ |
| **IBM ContextForge** | OSS | OAuth | K8s | Basic | Free |

### AI Gateway Solutions (LLM Proxy)

| Vendor | Providers Supported | Key Features | Pricing |
|--------|---------------------|--------------|---------|
| **Kong AI Gateway** | All major | Full governance, plugins | $$$$ |
| **Traefik AI Gateway** | All major | PII protection, guardrails | $$$ |
| **Apigee (Google)** | All major | Enterprise API mgmt | $$$$ |
| **MLflow AI Gateway** | All major | OSS, basic governance | Free |
| **LiteLLM** | All major | OSS, simple proxy | Free |

### Recommendation by Company Size

| Company Size | Recommended Stack |
|--------------|-------------------|
| **Startup (<50)** | Tier 1 + LiteLLM proxy |
| **SMB (50-500)** | Tier 2 + Kong/Traefik |
| **Enterprise (500-5000)** | Tier 2-3 + Kong/Apigee |
| **Large Enterprise (5000+)** | Tier 3 + Full stack |
| **Regulated Industry** | Tier 3-4 + Self-hosted LLM |

---

## Appendix: Attack Vectors (from Wiz Research)

### A.1 Token Theft
**Attack**: Malicious MCP server exfiltrates OAuth tokens
**Mitigation**: 
- Sandbox MCP servers with no filesystem access
- Use short-lived tokens with minimal scopes
- Store tokens in Vault, not in MCP server process

### A.2 Indirect Prompt Injection
**Attack**: Malicious content in email/doc tricks LLM into dangerous actions
**Mitigation**:
- Prompt injection detection at gateway
- Human-in-the-loop for destructive operations
- Tool annotations (readOnly, destructive)

### A.3 Tool Shadowing
**Attack**: Malicious server registers tool with same name as legitimate tool
**Mitigation**:
- Tool namespacing (e.g., `company.gmail.send`)
- Internal registry with signed tool definitions
- Gateway validates tool sources

### A.4 DNS Rebinding (SSE Transport)
**Attack**: Attacker hijacks SSE connection via DNS rebinding
**Mitigation**:
- Use Streamable HTTP with origin validation
- TLS termination at gateway
- Validate Host headers

### A.5 Auto-Run Exploitation
**Attack**: Compromised tool response triggers automatic dangerous action
**Mitigation**:
- Disable auto-run for sensitive tools
- Require explicit user approval
- Rate limiting on tool execution

### A.6 Vendor Data Exposure
**Attack**: Remote MCP server stores/leaks sensitive context
**Mitigation**:
- Prefer local MCP servers
- Audit remote server code
- Use internal registry only

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01 | Security Team | Initial release |

---

## References

1. Wiz Research: "Inside MCP Security: A Research Guide on Emerging Risks"
2. Anthropic MCP Specification: https://modelcontextprotocol.io
3. Microsoft MCP Gateway: https://github.com/microsoft/mcp-gateway
4. Block/Goose MCP Security: https://block.github.io/goose/blog/2025/03/31/securing-mcp/
5. Stytch MCP Security Guide: https://stytch.com/blog/mcp-security/
6. Kong AI Gateway: https://konghq.com/products/kong-ai-gateway
7. Traefik MCP Gateway: https://traefik.io/solutions/mcp-gateway
