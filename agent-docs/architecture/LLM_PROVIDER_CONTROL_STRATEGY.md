# LLM Provider Control Strategy for Enterprise MCP Deployments

**Version**: 1.0  
**Date**: January 2025  
**Classification**: Internal  

---

## Executive Summary

This document addresses a critical enterprise security challenge: **how to control which LLM providers employees use when accessing corporate systems via MCP (Model Context Protocol)**.

The core problem is that MCP servers are "blind" to which LLM is calling them. When an employee uses an AI coding assistant to access Gmail, Drive, or Jira via MCP, the MCP server only sees the tool request—not whether the underlying LLM is an approved provider (AWS Bedrock, GCP Vertex) or an unapproved one (personal OpenAI key, xAI, local Ollama).

This creates a data leakage risk: corporate data flows through the LLM provider for processing, and without controls, that provider could be anyone.

---

## Table of Contents

1. [The Problem: MCP's Blind Spot](#the-problem-mcps-blind-spot)
2. [Threat Scenarios](#threat-scenarios)
3. [Control Strategies](#control-strategies)
4. [Implementation Approaches](#implementation-approaches)
5. [Recommended Architecture](#recommended-architecture)
6. [Quick Start Guide](#quick-start-guide)
7. [Limitations and Residual Risks](#limitations-and-residual-risks)

---

## The Problem: MCP's Blind Spot

### How MCP Works

In a typical MCP setup, an AI client (like Claude Code or Cursor) has two separate connections:

1. **LLM Connection**: The client sends prompts to an LLM provider and receives responses
2. **MCP Connection**: The client connects to MCP servers to execute tools (read email, create documents, etc.)

The critical issue is that these are **independent connections**. The MCP server receives tool requests but has no visibility into which LLM provider processed the prompt that led to that request.

```
┌─────────────────────────────────────────────────────────────────┐
│                      AI CLIENT                                  │
│                                                                 │
│   ┌─────────────────┐              ┌─────────────────┐          │
│   │  LLM Provider   │◄────────────►│   MCP Client    │          │
│   │  (Unknown to    │   Internal   │                 │          │
│   │   MCP server)   │   coupling   │                 │          │
│   └─────────────────┘              └────────┬────────┘          │
│                                             │                   │
└─────────────────────────────────────────────┼───────────────────┘
                                              │
                                              │ MCP Protocol
                                              │ (No LLM info)
                                              ▼
                                    ┌─────────────────┐
                                    │   MCP Server    │
                                    │                 │
                                    │ Sees: tool call │
                                    │ Doesn't see:    │
                                    │ which LLM       │
                                    └─────────────────┘
```

### Why This Matters

When an employee asks their AI assistant to "summarize my recent emails," the following happens:

1. The MCP client fetches emails from Gmail via the MCP server
2. The email content is sent to the LLM provider for summarization
3. The LLM processes the content and returns a summary

If the employee is using a personal OpenAI API key instead of the corporate-approved AWS Bedrock, your email content is now processed by OpenAI—potentially without a Data Processing Agreement, without audit trails, and without your knowledge.

---

## Threat Scenarios

### Scenario 1: Personal API Keys

An employee signs up for an OpenAI account, gets an API key, and configures their AI coding assistant to use it. They then connect to corporate MCP servers. All corporate data accessed via MCP flows through OpenAI's infrastructure.

**Risk**: Data processed by provider without corporate contract, DPA, or security review.

### Scenario 2: Free/Cheap Alternatives

An employee discovers a cheaper LLM provider or a "free" service. They configure their client to use it. The provider may have weak security practices, log all prompts, or be located in a jurisdiction with different data protection laws.

**Risk**: Data exposure to unknown third parties, potential compliance violations.

### Scenario 3: Local Models

An employee runs Ollama or LM Studio locally to avoid API costs. While this keeps data on-device, the local model may have different capabilities, safety guardrails, or could be a modified/compromised version.

**Risk**: Inconsistent security posture, potential for jailbroken models.

### Scenario 4: Malicious Middleware

An employee uses a third-party "AI aggregator" service that promises to route requests to the cheapest provider. This middleware sees all prompts and responses.

**Risk**: Man-in-the-middle exposure, data harvesting.

---

## Control Strategies

There are five primary strategies for controlling LLM provider usage, each with different tradeoffs.

### Strategy 1: Network-Level Blocking

**Concept**: Use your existing network security infrastructure (Zscaler, firewall, DNS) to block direct access to unapproved LLM provider APIs.

**How it works**:
- Block outbound connections to `api.openai.com`, `api.anthropic.com`, `x.ai`, etc.
- Allow only connections to approved endpoints (`bedrock-runtime.*.amazonaws.com`, `*.aiplatform.googleapis.com`)

**Advantages**:
- Quick to implement (policy change in existing tools)
- Works regardless of which AI client is used
- No new infrastructure required

**Limitations**:
- Doesn't prevent local models (Ollama on localhost)
- Sophisticated users might use VPNs or proxies to bypass
- Requires maintaining an up-to-date blocklist as new providers emerge

**Effectiveness**: Blocks ~80% of shadow AI usage with minimal effort.

### Strategy 2: LLM Proxy Gateway

**Concept**: Deploy a corporate proxy that all LLM traffic must flow through. The proxy authenticates users, logs requests, and routes only to approved providers.

**How it works**:
- Employees configure AI clients to use `https://llm-proxy.company.com` instead of direct provider URLs
- The proxy validates the user (via corporate SSO), logs the request, and forwards to an approved provider
- Corporate API credentials are stored in the proxy, not on employee devices

**Advantages**:
- Full visibility and audit trail of all LLM usage
- Centralized credential management (employees never see API keys)
- Can enforce additional policies (rate limiting, content filtering, cost controls)
- Can transparently remap models (user requests "gpt-4" → proxy routes to Bedrock Claude)

**Limitations**:
- Requires deploying and maintaining new infrastructure
- AI clients must support custom endpoints (most do)
- Adds a small amount of latency

**Effectiveness**: Very high when combined with network blocking.

### Strategy 3: Managed Client Distribution

**Concept**: Instead of letting employees install and configure their own AI clients, distribute pre-configured clients via MDM with locked settings.

**How it works**:
- IT packages approved AI clients (Claude Code, Cursor, etc.) with corporate configuration
- Configuration specifies the LLM proxy endpoint and cannot be changed by users
- Unapproved AI applications are blocked from installation

**Advantages**:
- Prevents configuration tampering
- Ensures consistent security posture across all users
- Can include additional security controls (certificate pinning, etc.)

**Limitations**:
- Not all AI clients support locked configurations
- Requires ongoing MDM management
- May limit flexibility for power users
- Users might find workarounds (web-based AI tools, personal devices)

**Effectiveness**: High for managed devices, but doesn't cover BYOD or web access.

### Strategy 4: Endpoint Monitoring and Detection

**Concept**: Use EDR/endpoint monitoring to detect unauthorized LLM usage and alert security teams.

**How it works**:
- Monitor for processes associated with local LLMs (ollama, llama.cpp, lm-studio)
- Scan AI client configuration files for unauthorized API keys or endpoints
- Alert on network connections to known LLM provider IPs that bypass the proxy

**Advantages**:
- Catches bypass attempts that other controls miss
- Provides evidence for policy enforcement
- Can trigger automated remediation

**Limitations**:
- Detection, not prevention (user has already violated policy)
- Requires tuning to avoid false positives
- Privacy considerations around monitoring employee devices

**Effectiveness**: Good as a backstop, not as a primary control.

### Strategy 5: MCP-Level Client Attestation

**Concept**: Modify the MCP protocol flow to include attestation about which LLM provider is being used, allowing the MCP server/gateway to reject requests from unapproved providers.

**How it works**:
- Corporate AI clients are modified to include signed attestation in MCP requests
- Attestation includes: client ID, LLM provider, model name, timestamp
- MCP gateway validates attestation before allowing tool execution

**Advantages**:
- Direct enforcement at the MCP layer
- Cryptographic verification of client claims
- Works even if network controls are bypassed

**Limitations**:
- Requires custom/modified AI clients (not available off-the-shelf today)
- Adds complexity to MCP infrastructure
- Attestation can potentially be forged if client is compromised

**Effectiveness**: Theoretically very high, but requires significant development effort.

---

## Implementation Approaches

### Approach A: Quick Win (1-2 Days)

**Goal**: Immediate risk reduction with minimal effort.

**Actions**:
1. Update Zscaler/firewall policies to block direct access to public LLM APIs
2. Publish an Acceptable Use Policy for AI tools
3. Communicate approved LLM providers and how to configure them

**Blocked endpoints**:
- `api.openai.com`
- `api.anthropic.com`
- `x.ai`, `api.x.ai`
- `api.mistral.ai`
- `api.cohere.ai`
- `api.together.ai`
- `api.groq.com`
- `api.deepseek.com`
- `generativelanguage.googleapis.com` (direct Gemini API)

**Allowed endpoints**:
- `bedrock-runtime.*.amazonaws.com` (AWS Bedrock)
- `*.aiplatform.googleapis.com` (GCP Vertex AI)
- `*.openai.azure.com` (Azure OpenAI, if applicable)

### Approach B: Standard Enterprise (2-4 Weeks)

**Goal**: Full control and visibility over LLM usage.

**Actions**:
1. Deploy an LLM proxy gateway (Kong AI Gateway, LiteLLM, or custom)
2. Configure the proxy to authenticate via corporate IdP (EntraID, Okta)
3. Store LLM provider credentials in the proxy (Vault or similar)
4. Update network policies to only allow LLM traffic through the proxy
5. Distribute configuration guides for approved AI clients
6. Enable comprehensive logging and monitoring

**LLM Proxy Gateway responsibilities**:
- Authenticate users via SSO
- Validate requests against policy (allowed models, rate limits)
- Inject corporate API credentials
- Route to approved providers
- Log all requests for audit
- Optionally: content filtering, PII detection, cost tracking

### Approach C: High Security (1-2 Months)

**Goal**: Defense in depth with multiple enforcement points.

**Actions**:
1. All controls from Approach B, plus:
2. MDM-distributed AI clients with locked configurations
3. Application allowlisting to prevent unapproved AI tools
4. EDR rules to detect local LLM processes
5. Regular audits of AI client configurations
6. DLP integration to detect sensitive data in LLM prompts

---

## Recommended Architecture

For organizations with existing Zscaler, EntraID, and cloud provider contracts (AWS/GCP), the recommended architecture combines network controls with an LLM proxy gateway.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  EMPLOYEE DEVICE                     CORPORATE INFRASTRUCTURE               │
│  ┌─────────────────┐                                                        │
│  │                 │                 ┌─────────────────────────────────┐    │
│  │  AI Client      │                 │         LLM PROXY GATEWAY       │    │
│  │  (Claude Code)  │────────────────►│                                 │    │
│  │                 │  LLM requests   │  • Authenticates via EntraID    │    │
│  │  Configured:    │                 │  • Routes to Bedrock/Vertex     │    │
│  │  llm-proxy.     │                 │  • Injects API credentials      │    │
│  │  company.com    │                 │  • Logs all requests            │    │
│  │                 │                 │                                 │    │
│  │                 │                 └───────────────┬─────────────────┘    │
│  │                 │                                 │                      │
│  │                 │                                 ▼                      │
│  │                 │                 ┌───────────────────────────────┐      │
│  │                 │                 │  AWS Bedrock / GCP Vertex     │      │
│  │                 │                 │  (Approved LLM Providers)     │      │
│  │                 │                 └───────────────────────────────┘      │
│  │                 │                                                        │
│  │                 │                 ┌─────────────────────────────────┐    │
│  │                 │────────────────►│         MCP GATEWAY            │    │
│  │                 │  MCP requests   │                                 │    │
│  │  Configured:    │                 │  • Authenticates user          │    │
│  │  mcp.company    │                 │  • Routes to approved MCPs     │    │
│  │  .com           │                 │  • Logs tool invocations       │    │
│  │                 │                 │                                 │    │
│  └─────────────────┘                 └───────────────┬─────────────────┘    │
│                                                      │                      │
│  ZSCALER                                             ▼                      │
│  ┌─────────────────┐                 ┌───────────────────────────────┐      │
│  │ Blocks direct   │                 │  MCP Servers                  │      │
│  │ access to:      │                 │  (Gmail, Drive, Atlassian)    │      │
│  │ • api.openai    │                 └───────────────────────────────┘      │
│  │ • api.anthropic │                                                        │
│  │ • etc.          │                                                        │
│  └─────────────────┘                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Two separate gateways**: LLM traffic and MCP traffic are controlled independently. Both need protection.

2. **Network as backstop**: Even if a user misconfigures their client, Zscaler blocks direct access to unapproved providers.

3. **Credentials never on endpoints**: API keys for Bedrock/Vertex are stored in the proxy, not on employee devices.

4. **Comprehensive logging**: Both gateways log all requests, enabling audit and anomaly detection.

5. **SSO integration**: Users authenticate with existing corporate identity, no separate AI credentials.

---

## Quick Start Guide

### Prerequisites
- Zscaler Internet Access (or equivalent firewall/proxy)
- EntraID or Google Workspace for SSO
- AWS and/or GCP account with Bedrock/Vertex enabled

### Week 1: Network Controls

**Step 1**: Create a Zscaler URL category for blocked LLM providers:
```
Category Name: Blocked-LLM-Providers
URLs:
  - api.openai.com
  - api.anthropic.com
  - x.ai
  - api.x.ai
  - api.mistral.ai
  - api.cohere.ai
  - api.together.ai
  - api.groq.com
  - api.deepseek.com
  - generativelanguage.googleapis.com
```

**Step 2**: Create a blocking rule for this category.

**Step 3**: Create an allow rule for approved providers:
```
Allowed URLs:
  - bedrock-runtime.*.amazonaws.com
  - *.aiplatform.googleapis.com
```

**Step 4**: Communicate to employees that direct LLM API access is blocked and provide instructions for approved alternatives.

### Week 2-4: LLM Proxy Gateway

**Step 1**: Choose a gateway solution:
- **Kong AI Gateway**: Full-featured, enterprise support, commercial
- **LiteLLM Proxy**: Open source, simple, good for starting
- **Custom**: Build on top of a standard API gateway

**Step 2**: Deploy the gateway in your cloud environment (AWS/GCP).

**Step 3**: Configure SSO integration with EntraID.

**Step 4**: Configure routing to approved LLM providers:
```yaml
# Example LiteLLM configuration
model_list:
  - model_name: "gpt-4"
    litellm_params:
      model: "bedrock/anthropic.claude-sonnet-4-20250514"
      aws_region_name: "us-east-1"
      
  - model_name: "claude-3-opus"
    litellm_params:
      model: "bedrock/anthropic.claude-3-opus"
      aws_region_name: "us-east-1"
      
  - model_name: "gemini-pro"
    litellm_params:
      model: "vertex_ai/gemini-pro"
      vertex_project: "your-project-id"
      vertex_location: "us-central1"
```

**Step 5**: Update Zscaler to only allow LLM provider access from the proxy's IP addresses.

**Step 6**: Distribute client configuration instructions to employees.

### Ongoing: Monitoring and Compliance

- Review LLM proxy logs weekly for unusual patterns
- Monitor Zscaler logs for blocked LLM access attempts
- Conduct quarterly audits of AI client configurations
- Update blocked provider list as new services emerge

---

## Limitations and Residual Risks

### What These Controls Don't Prevent

1. **Copy-paste exfiltration**: A user can copy data from an approved tool and paste it into ChatGPT's web interface. Mitigation: DLP tools, browser isolation.

2. **Personal devices**: If users access corporate systems from unmanaged devices, they can use any LLM. Mitigation: Require managed devices for MCP access, device posture checks.

3. **Screenshots and photos**: Users can photograph their screen. Mitigation: Policy, training, physical security.

4. **Sophisticated bypass**: Determined users might use VPNs, tunneling, or other techniques. Mitigation: Endpoint monitoring, anomaly detection.

5. **Web-based AI tools**: ChatGPT, Claude.ai, Gemini web interfaces. Mitigation: Block these URLs in Zscaler, or use browser isolation.

### Residual Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Employee uses personal API key | Low (after controls) | Medium | Network blocking + monitoring |
| Employee uses web-based AI | Medium | Medium | URL blocking + DLP |
| Employee uses local LLM | Low | Low | EDR monitoring |
| Sophisticated bypass attempt | Very Low | High | Anomaly detection + incident response |
| Data copied to personal device | Medium | High | DLP + device management |

### Recommended Acceptance Criteria

For most organizations, implementing Approach B (LLM Proxy Gateway + Network Controls) reduces the risk of unauthorized LLM usage to an acceptable level. The residual risks primarily involve determined insider threats, which require different controls (DLP, insider threat programs, etc.).

---

## Appendix: Vendor Comparison for LLM Proxy Gateways

| Solution | Type | SSO Support | Logging | Cost Control | Pricing |
|----------|------|-------------|---------|--------------|---------|
| Kong AI Gateway | Commercial | Yes | Comprehensive | Yes | $$$$ |
| Traefik AI Gateway | Commercial | Yes | Comprehensive | Yes | $$$ |
| LiteLLM Proxy | Open Source | Basic | Good | Yes | Free |
| Portkey | Commercial | Yes | Comprehensive | Yes | $$ |
| Helicone | Commercial | Yes | Comprehensive | Yes | $$ |
| Custom (API Gateway + Logic) | DIY | Depends | Depends | Depends | $ + effort |

### Selection Criteria

- **Enterprise with existing Kong/Traefik**: Use their AI Gateway add-on
- **Startup or small team**: LiteLLM Proxy is sufficient
- **Need advanced observability**: Helicone or Portkey
- **Maximum control**: Custom solution on top of AWS API Gateway or similar

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | January 2025 | Security Team | Initial release |
