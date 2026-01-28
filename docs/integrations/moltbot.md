# Moltbot Integration Guide

Complete guide for integrating Sentinel safety guardrails with [Moltbot](https://github.com/moltbot/moltbot).

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Basic Setup](#basic-setup)
- [Configuration](#configuration)
- [Use Cases](#use-cases)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Reference](#reference)

## Overview

`@sentinelseed/moltbot` provides AI safety guardrails for Moltbot, protecting your personal AI agent with:

| Feature | Description |
|---------|-------------|
| **Input Analysis** | Detect prompt injection and jailbreak attempts |
| **Output Validation** | Prevent data leaks (API keys, passwords, credentials) |
| **Tool Validation** | Block dangerous commands and system access |
| **Seed Injection** | Add safety context to AI processing |
| **Escape Hatches** | Bypass protection when needed |

### Protection Levels

| Level | Blocking | Best For |
|-------|----------|----------|
| `watch` | None | Daily use, full visibility |
| `guard` | Critical threats | Sensitive environments |
| `shield` | Maximum | High-security workflows |

## Prerequisites

- **Node.js** 18.0.0 or higher
- **Moltbot** 1.0.0 or higher
- **npm** or **pnpm**

Verify your environment:

```bash
node --version    # Should be v18+
moltbot --version # Should be 1.0.0+
```

## Installation

### Step 1: Install the Package

```bash
npm install @sentinelseed/moltbot
```

Or with pnpm:

```bash
pnpm add @sentinelseed/moltbot
```

### Step 2: Configure Moltbot

Add Sentinel to your Moltbot configuration file (`moltbot.config.json` or `~/.config/moltbot/config.json`):

```json
{
  "plugins": {
    "sentinel": {
      "level": "watch"
    }
  }
}
```

### Step 3: Verify Installation

Start Moltbot and check the logs:

```bash
moltbot start
```

You should see:

```
[sentinel] Sentinel initialized (level: watch)
```

## Basic Setup

### Minimal Configuration

For most users, this is all you need:

```json
{
  "plugins": {
    "sentinel": {
      "level": "watch"
    }
  }
}
```

This enables full monitoring with zero blocking.

### Recommended Configuration

For environments with sensitive data:

```json
{
  "plugins": {
    "sentinel": {
      "level": "guard"
    }
  }
}
```

This blocks data leaks and dangerous commands while allowing normal operations.

### High-Security Configuration

For maximum protection:

```json
{
  "plugins": {
    "sentinel": {
      "level": "shield",
      "alerts": {
        "enabled": true,
        "webhook": "https://your-webhook.com/sentinel",
        "minSeverity": "medium"
      }
    }
  }
}
```

## Configuration

### Full Configuration Reference

```json
{
  "plugins": {
    "sentinel": {
      "level": "guard",
      "alerts": {
        "enabled": true,
        "webhook": "https://your-webhook.com/sentinel",
        "minSeverity": "high"
      },
      "ignorePatterns": [
        "MY_SAFE_TOKEN",
        "TEST_KEY_*"
      ],
      "trustedTools": [
        "read_file",
        "write_file"
      ],
      "dangerousTools": [
        "custom_dangerous_tool"
      ],
      "logLevel": "info"
    }
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `level` | `string` | `"watch"` | Protection level: `off`, `watch`, `guard`, `shield` |
| `alerts.enabled` | `boolean` | `false` | Enable webhook alerts |
| `alerts.webhook` | `string` | - | Webhook URL for security alerts |
| `alerts.minSeverity` | `string` | `"medium"` | Minimum alert severity: `low`, `medium`, `high`, `critical` |
| `ignorePatterns` | `string[]` | `[]` | Patterns to ignore in validation (supports wildcards) |
| `trustedTools` | `string[]` | `[]` | Tools that bypass validation |
| `dangerousTools` | `string[]` | `[]` | Additional tools to block |
| `logLevel` | `string` | `"info"` | Log verbosity: `debug`, `info`, `warn`, `error` |

### Environment Variables

You can also configure via environment variables:

```bash
export SENTINEL_LEVEL=guard
export SENTINEL_WEBHOOK_URL=https://your-webhook.com/sentinel
export SENTINEL_LOG_LEVEL=debug
```

## Use Cases

### Use Case 1: Monitoring Development Environment

**Scenario:** You want visibility into what your AI agent is doing without any blocking.

**Configuration:**

```json
{
  "plugins": {
    "sentinel": {
      "level": "watch",
      "logLevel": "debug"
    }
  }
}
```

**What happens:**
- All actions are logged
- Threats are detected and alerted
- Nothing is blocked
- You see everything the agent does

### Use Case 2: Protecting API Keys

**Scenario:** Your agent has access to files containing API keys, and you want to prevent accidental leaks.

**Configuration:**

```json
{
  "plugins": {
    "sentinel": {
      "level": "guard"
    }
  }
}
```

**What happens:**
- Output containing API keys is blocked
- Output containing passwords is blocked
- Normal responses pass through
- You're notified when something is blocked

**Example blocked output:**

```
User: What's in my .env file?
Agent: Here are the contents:
       OPENAI_API_KEY=sk-1234...  <-- BLOCKED
```

### Use Case 3: Preventing Destructive Commands

**Scenario:** You want to prevent the agent from running dangerous shell commands.

**Configuration:**

```json
{
  "plugins": {
    "sentinel": {
      "level": "guard"
    }
  }
}
```

**What happens:**
- Commands like `rm -rf`, `drop table`, `format` are blocked
- System path access (`/etc/passwd`, `C:\Windows`) is blocked
- Normal file operations pass through

**Example blocked command:**

```
User: Clean up my disk
Agent: I'll run: rm -rf /tmp/*  <-- BLOCKED (destructive pattern)
```

### Use Case 4: Webhook Alerts to Slack

**Scenario:** You want to receive Slack notifications for security events.

**Configuration:**

```json
{
  "plugins": {
    "sentinel": {
      "level": "guard",
      "alerts": {
        "enabled": true,
        "webhook": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        "minSeverity": "high"
      }
    }
  }
}
```

**Webhook payload format:**

```json
{
  "type": "action_blocked",
  "severity": "critical",
  "message": "Blocked output: API key detected",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "sessionId": "session-123",
  "context": {
    "action": "output",
    "issueCount": 1
  }
}
```

### Use Case 5: Temporary Bypass for Trusted Operations

**Scenario:** You need to temporarily disable protection for a specific task.

**Commands:**

```bash
# Pause for 5 minutes
/sentinel pause 5m

# Allow just the next action
/sentinel allow-once

# Trust a specific tool for this session
/sentinel trust bash

# Resume protection
/sentinel resume
```

### Use Case 6: Custom Tool Allowlist/Blocklist

**Scenario:** You have custom tools that should always be trusted or blocked.

**Configuration:**

```json
{
  "plugins": {
    "sentinel": {
      "level": "guard",
      "trustedTools": [
        "my_safe_tool",
        "mcp__internal_*"
      ],
      "dangerousTools": [
        "legacy_dangerous_tool",
        "admin_*"
      ]
    }
  }
}
```

## Advanced Usage

### Programmatic Integration

If you need to integrate Sentinel programmatically:

```typescript
import { createSentinelHooks } from '@sentinelseed/moltbot';

const hooks = createSentinelHooks({
  level: 'guard',
  alerts: {
    enabled: true,
    webhook: process.env.SENTINEL_WEBHOOK_URL
  }
});

// Use hooks directly
const result = await hooks.messageSending({
  sessionId: 'my-session',
  content: 'Response content'
});

if (result?.cancel) {
  console.log('Blocked:', result.cancelReason);
}
```

### Custom Validators

Access validators directly for custom logic:

```typescript
import { validateOutput, validateTool, getLevelConfig } from '@sentinelseed/moltbot';

const config = getLevelConfig('guard');

// Validate output
const outputResult = await validateOutput('content to check', config);

// Validate tool call
const toolResult = await validateTool('bash', { command: 'ls -la' }, config);
```

### Escape Manager API

Programmatically manage escape hatches:

```typescript
import { EscapeManager } from '@sentinelseed/moltbot';

const escapes = new EscapeManager();

// Grant one-time bypass
escapes.grantAllowOnce('session-id', { scope: 'output' });

// Pause protection
escapes.pauseProtection('session-id', { durationMs: 300000 });

// Trust a tool
escapes.trustTool('session-id', 'bash', { level: 'session' });
```

### Audit Log Access

Query the audit log for analysis:

```typescript
import { AuditLog } from '@sentinelseed/moltbot';

const audit = new AuditLog({ maxEntries: 1000 });

// Get recent entries
const recent = audit.getRecent(10);

// Query by session
const sessionLogs = audit.query({ sessionId: 'my-session' });

// Query blocked actions
const blocked = audit.query({ outcome: 'blocked' });

// Get statistics
const stats = audit.getStats();
```

## Troubleshooting

### Issue: Sentinel Not Loading

**Symptoms:** No "Sentinel initialized" message in logs.

**Solutions:**

1. Verify package is installed:
   ```bash
   npm list @sentinelseed/moltbot
   ```

2. Check configuration syntax:
   ```bash
   cat ~/.config/moltbot/config.json | jq .
   ```

3. Ensure plugin key is `"sentinel"` (not `"@sentinelseed/moltbot"`):
   ```json
   {
     "plugins": {
       "sentinel": { ... }
     }
   }
   ```

### Issue: False Positives

**Symptoms:** Legitimate content is being blocked.

**Solutions:**

1. Add patterns to ignore list:
   ```json
   {
     "plugins": {
       "sentinel": {
         "ignorePatterns": ["MY_SAFE_PATTERN"]
       }
     }
   }
   ```

2. Use `watch` level temporarily to identify patterns:
   ```json
   {
     "plugins": {
       "sentinel": {
         "level": "watch",
         "logLevel": "debug"
       }
     }
   }
   ```

3. Use `/sentinel allow-once` for one-time bypass.

### Issue: Tool Being Blocked Unexpectedly

**Symptoms:** A safe tool is blocked.

**Solutions:**

1. Add to trusted tools:
   ```json
   {
     "plugins": {
       "sentinel": {
         "trustedTools": ["my_tool"]
       }
     }
   }
   ```

2. Check logs for the specific reason:
   ```bash
   moltbot logs | grep sentinel
   ```

### Issue: Webhook Not Receiving Alerts

**Symptoms:** Alerts enabled but webhook not called.

**Solutions:**

1. Verify webhook URL is correct and accessible.

2. Check `minSeverity` setting (might be filtering alerts):
   ```json
   {
     "plugins": {
       "sentinel": {
         "alerts": {
           "minSeverity": "low"
         }
       }
     }
   }
   ```

3. Enable debug logging to see alert attempts:
   ```json
   {
     "plugins": {
       "sentinel": {
         "logLevel": "debug"
       }
     }
   }
   ```

### Issue: Performance Impact

**Symptoms:** Noticeable delay in responses.

**Solutions:**

1. Sentinel validation typically adds < 10ms. If slower:
   - Check network latency to webhook endpoints
   - Reduce log verbosity to `"warn"`

2. For high-throughput scenarios, consider `watch` level.

## FAQ

### Q: Does Sentinel send data externally?

**A:** No. All validation happens locally. The only external communication is optional webhook alerts that YOU configure.

### Q: Can I use Sentinel with other Moltbot plugins?

**A:** Yes. Sentinel registers at high priority (100) to run before other plugins but is designed to be compatible.

### Q: What happens if Sentinel crashes?

**A:** Sentinel follows "fail open" design. If an error occurs, the action proceeds (not blocked). Errors are logged.

### Q: Can I disable Sentinel temporarily?

**A:** Yes, multiple ways:
- Set `level: "off"` in config
- Use `/sentinel pause <duration>`
- Use `/sentinel allow-once` for single action

### Q: Does Sentinel work offline?

**A:** Yes. All validation is local. Webhooks require network but are optional.

### Q: What's the performance overhead?

**A:** Typically < 10ms per validation. Sentinel uses heuristic (pattern-based) validation by default, which is very fast.

### Q: Can I customize detection patterns?

**A:** The current version uses built-in patterns from `@sentinelseed/core`. Custom patterns are on the roadmap.

### Q: Is there a way to see what would be blocked without actually blocking?

**A:** Yes, use `level: "watch"`. It logs everything that WOULD be blocked without actually blocking.

## Reference

### CLI Commands

| Command | Description |
|---------|-------------|
| `/sentinel status` | Show current status |
| `/sentinel level [new]` | View/change protection level |
| `/sentinel log [count]` | View recent audit entries |
| `/sentinel pause <duration>` | Pause protection |
| `/sentinel resume` | Resume protection |
| `/sentinel allow-once [scope]` | One-time bypass |
| `/sentinel trust <tool>` | Trust a tool for session |
| `/sentinel untrust <tool>` | Revoke trust |
| `/sentinel help` | Show all commands |

### Detection Categories

**Input Analysis:**
- Prompt injection patterns
- Jailbreak attempts (DAN, ignore instructions)
- Role manipulation
- System prompt extraction

**Output Validation:**
- API keys (OpenAI, Anthropic, AWS, Google, etc.)
- Passwords and credentials
- Private keys and tokens
- Credit card numbers
- Social security numbers

**Tool Validation:**
- Destructive commands (rm, drop, truncate, format)
- System paths (/etc, /var, C:\Windows, C:\System32)
- Network operations to suspicious domains
- Privilege escalation patterns

### Links

- [Package README](https://github.com/sentinel-seed/sentinel/tree/main/packages/moltbot)
- [Examples](https://github.com/sentinel-seed/sentinel/tree/main/packages/moltbot/examples)
- [Sentinel Core](https://github.com/sentinel-seed/sentinel)
- [API Reference](https://github.com/sentinel-seed/sentinel/tree/main/docs/api)
- [Moltbot Documentation](https://docs.molt.bot/)

*Guide by Sentinel Team*
