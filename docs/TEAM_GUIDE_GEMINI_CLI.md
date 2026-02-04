# Building with Gemini CLI: A Guide for Google Workspace Admins

> **Your First AI-Assisted Development Project**
> 
> This guide teaches you how to work *with* Gemini CLI to build tools - not how to code them yourself. Think of Gemini as a senior developer pair-programming with you. Your job is to give clear direction; Gemini handles the implementation.

---

## What You'll Build

By the end of this guide, you'll have created a **GWS Admin MCP** - a tool that lets you (or an AI assistant) manage Google Workspace through natural language. Your first feature: **Gmail inbox delegation**.

But more importantly, you'll learn *how to ask* Gemini to build things for you.

---

## Part 1: The Mindset Shift

### You Are the Product Manager, Gemini Is the Engineer

Traditional learning: "I need to understand Python, OAuth, APIs, then build something."

AI-assisted building: "I need to clearly describe *what* I want. Gemini figures out *how*."

**Your superpowers as a GWS Admin:**
- You know the Google Admin Console inside-out
- You understand what workflows are painful
- You know what APIs exist (even if you've never called them)
- You can verify if something works by checking the Admin Console

**Gemini's superpowers:**
- Writes code in any language
- Knows API documentation
- Handles boilerplate and error handling
- Remembers context within a session

### The 80/20 of Working with AI

| What matters most | What matters less |
|-------------------|-------------------|
| Clear problem description | Perfect technical vocabulary |
| Concrete examples | Knowing the "right" way to ask |
| Verifying outputs work | Understanding every line of code |
| Iterating on failures | Getting it right first try |

---

## Part 2: Setting Up Gemini CLI

### Installation (One-Time Setup)

```bash
# Install Gemini CLI
npm install -g @google/gemini-cli

# Or if you prefer npx (no install)
npx @google/gemini-cli
```

### Configuring AGENTS.md (Recommended)

By default, Gemini CLI looks for a `GEMINI.md` file for context. However, our team follows the industry standard of using `AGENTS.md`. You should configure your CLI to look for `AGENTS.md` automatically.

1. Create or open your global settings file at `~/.gemini/settings.json`.
2. Add the following configuration:

```json
{
  "context": {
    "fileName": ["AGENTS.md", "GEMINI.md"]
  }
}
```

This ensures that whenever you start a `gemini` session in a folder, it will automatically load the project-specific `AGENTS.md` instructions we've created.

### Your First Conversation

Open terminal in any folder and type:

```bash
gemini
```

You're now in an interactive session. Try:

```
What can you help me build?
```

Gemini will explain its capabilities. Notice how it responds to natural language - no special syntax needed.

---

## Part 3: The Art of Giving Context

### Why Context Matters

Gemini is smart but has no memory between sessions and doesn't know your specific situation. The more relevant context you provide upfront, the better the output.

### The Context Sandwich

Structure your requests like this:

```
[WHO YOU ARE + WHAT YOU HAVE]
I'm a Google Workspace administrator. I have access to the Admin SDK 
and understand OAuth. I'm working in Python.

[WHAT YOU WANT TO BUILD]
I want to create an MCP server that can manage Gmail delegation - 
specifically, allowing one user to access another user's inbox.

[WHAT SUCCESS LOOKS LIKE]
When done, I should be able to ask an AI assistant "Give john@company.com 
access to jane@company.com's inbox" and have it actually happen.

[CONSTRAINTS]
- Use the official Google Admin SDK
- Follow Google's OAuth best practices
- Make it work with service account authentication
```

### Context You Should Always Provide

| Context Type | Example |
|--------------|---------|
| Your role | "I'm a GWS admin with super admin access" |
| Your environment | "I'm on macOS, using Python 3.11" |
| Existing code/tools | "I'm basing this on the gws-mcp-advanced repo" |
| Authentication method | "I'll use a service account with domain-wide delegation" |
| Success criteria | "It should work when I test it in the Admin Console" |

---

## Part 4: The Conversation Patterns

### Pattern 1: Start with "Explain Before Building"

**Don't:** "Build me an MCP for Gmail delegation"

**Do:** 
```
Before we build anything, explain:
1. What API endpoints handle Gmail delegation?
2. What permissions/scopes are needed?
3. What's the typical flow for this operation?

I want to understand the landscape before we write code.
```

This gives you knowledge to verify Gemini's work later.

### Pattern 2: Build Incrementally

**Don't:** "Build the complete MCP server with all features"

**Do:**
```
Let's build this step by step:

Step 1: Create a minimal Python script that authenticates 
with the Admin SDK using a service account.

Just this first. I'll test it before we continue.
```

Then after testing:
```
Step 1 works. Now Step 2: Add a function that lists 
current delegates for a given user's Gmail.
```

### Pattern 3: Show, Don't Just Tell

**Don't:** "It's not working"

**Do:**
```
I ran the script and got this error:

```
googleapiclient.errors.HttpError: <HttpError 403 
"Insufficient Permission: Request had insufficient 
authentication scopes.">
```

The service account has these scopes enabled in the 
Admin Console: [list them]

What am I missing?
```

### Pattern 4: Reference Existing Code

**Do:**
```
I'm looking at the gws-mcp-advanced repo. Here's how they 
structure their tools:

[paste a small example from the codebase]

I want my Gmail delegation tool to follow this same pattern. 
Can you show me how?
```

### Pattern 5: Ask for Verification Steps

**Do:**
```
After implementing this, how can I verify it works? 
Give me:
1. A test command to run
2. What to check in the Admin Console
3. How to confirm the delegation is active
```

---

## Part 5: Your First Build - Gmail Delegation MCP

### Step 1: Set the Stage

Start a new Gemini session and paste this context:

```
I'm a Google Workspace administrator building my first MCP server.

GOAL: Create a tool that manages Gmail inbox delegation through 
the Admin SDK. This will let AI assistants grant/revoke inbox 
access between users.

CONTEXT:
- I have super admin access to our Google Workspace
- I can create service accounts with domain-wide delegation
- I'm comfortable with Python basics
- I've seen the gws-mcp-advanced repo as a reference

WHAT I NEED FROM YOU:
1. First, explain what Gmail delegation is at the API level
2. Then, walk me through setting up authentication
3. Finally, help me build a minimal MCP with one tool: 
   "add_gmail_delegate"

Let's start with #1 - explain the API.
```

### Step 2: Understand Before Building

Gemini will explain the Gmail delegation API. Read it. Ask follow-up questions:

```
What's the difference between delegate access and 
"access to data" in the Admin Console?
```

```
What happens if the delegate already exists? 
Does the API error or succeed silently?
```

### Step 3: Set Up Authentication

```
Now let's set up authentication. I need:
1. Steps to create a service account in Google Cloud Console
2. How to enable domain-wide delegation
3. The exact scopes needed for Gmail delegation
4. A Python script that tests the authentication works

Give me the Google Cloud Console steps first.
```

Follow the steps. Then:

```
Done. Now give me the Python test script.
```

### Step 4: Build the First Tool

```
Authentication works. Now let's build the MCP.

I want a single file that:
1. Sets up an MCP server (use the mcp library)
2. Has one tool: add_gmail_delegate(delegator_email, delegate_email)
3. Returns a success/failure message

Keep it minimal. I'll add more tools later.
```

### Step 5: Test and Iterate

Run what Gemini gives you. If it fails:

```
Got this error when running the server:
[paste error]

The relevant code section is:
[paste the function that failed]

What's wrong?
```

If it works:

```
It works! I tested by adding myself as a delegate to 
a test account, and I can see it in the Admin Console.

Now let's add a second tool: list_gmail_delegates(user_email)
that shows all current delegates for a user.
```

---

## Part 6: When Things Go Wrong

### "It's not working" - The Debugging Conversation

```
The add_gmail_delegate function returns success, but when 
I check the Admin Console, no delegate appears.

Here's what I tried:
1. Called add_gmail_delegate("user1@company.com", "user2@company.com")
2. Got response: "Delegate added successfully"
3. Checked Admin Console > Users > user1 > Gmail > Delegation
4. No delegates listed

The API response was:
[paste full response if available]

What could cause this?
```

### "I'm stuck" - The Unstuck Conversation

```
I've been trying to get authentication working for an hour.
Here's everything I've tried:
1. Created service account with domain-wide delegation
2. Added scopes: https://www.googleapis.com/auth/gmail.settings.sharing
3. Downloaded JSON key file
4. Running this code: [paste code]
5. Getting this error: [paste error]

I've verified:
- The service account email is authorized in Admin Console
- The scopes match exactly
- The JSON key file path is correct

What am I missing? Give me a systematic debugging approach.
```

### "I don't understand" - The Learning Conversation

```
You mentioned "impersonation" in the context of service accounts.
I don't fully understand this concept.

Can you explain:
1. What impersonation means technically
2. Why it's needed for admin operations
3. How it's different from regular OAuth
4. A simple analogy that makes it click

I want to understand this, not just copy code.
```

---

## Part 7: Ideas for Your GWS Admin MCP

Once you've built Gmail delegation, consider these next features:

| Feature | Admin SDK Endpoint | Complexity |
|---------|-------------------|------------|
| List all users | Directory API | Easy |
| Suspend/unsuspend user | Directory API | Easy |
| Reset user password | Directory API | Easy |
| Get user's groups | Directory API | Medium |
| Create Google Group | Groups API | Medium |
| Manage group members | Groups API | Medium |
| Get login audit logs | Reports API | Medium |
| Manage org units | Directory API | Medium |
| Configure 2FA policies | Admin Settings | Hard |

### Prompt to Explore New Features

```
I want to add [FEATURE] to my GWS Admin MCP.

Before writing code, tell me:
1. Which Google API handles this?
2. What scopes are needed?
3. Are there any gotchas or limitations?
4. Show me the API request/response format

Then we'll implement it.
```

---

## Part 8: Leveling Up

### From Consumer to Creator

You've now experienced AI-assisted development. Some reflections:

1. **You didn't need to be a developer** - You needed to be clear about what you wanted
2. **Iteration is normal** - First attempts rarely work perfectly
3. **Your domain knowledge is valuable** - Knowing GWS made you effective
4. **AI amplifies, not replaces** - You still made all the decisions

### Next Steps

1. **Share your MCP** with the team
2. **Add features** that solve your daily pain points
3. **Document what you built** (ask Gemini to help write docs)
4. **Teach others** this approach

### The Meta-Skill

The real skill you learned isn't "how to build an MCP" - it's **how to collaborate with AI to build anything**. This pattern works for:

- Automating repetitive tasks
- Building internal tools
- Analyzing data
- Writing documentation
- And much more

---

## Quick Reference: Prompt Templates

### Starting a New Feature
```
I want to add [FEATURE] to my MCP.

Context:
- Current codebase: [describe or paste relevant parts]
- Authentication: [how you're authenticating]
- Goal: [what success looks like]

First, explain the approach. Then we'll implement.
```

### Debugging
```
[WHAT I EXPECTED]
[WHAT ACTUALLY HAPPENED]
[ERROR MESSAGE if any]
[CODE that's failing]
[WHAT I'VE ALREADY TRIED]

Help me debug this systematically.
```

### Learning a Concept
```
Explain [CONCEPT] to me.
- What is it?
- Why does it exist?
- When would I use it?
- Give me a simple example
- What are common mistakes?
```

### Code Review
```
Review this code I wrote:
[paste code]

Check for:
- Security issues
- Error handling
- Edge cases
- Best practices

Be direct about what's wrong.
```

---

## Appendix: Resources

- **gws-mcp-advanced repo**: Reference implementation for GWS MCP
- **Google Admin SDK docs**: https://developers.google.com/admin-sdk
- **MCP specification**: https://modelcontextprotocol.io
- **Gemini CLI docs**: https://github.com/google-gemini/gemini-cli

---

*Built by the IT Services team. Questions? Reach out to David.*
