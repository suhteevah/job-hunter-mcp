# LinkedIn Automation Skill

## Overview
Automate LinkedIn profile updates and Easy Apply job applications using browser automation tools (Kapture Browser Automation + Claude in Chrome).

## Critical: LinkedIn's Shadow DOM
LinkedIn uses web components with heavy shadow DOM. Standard CSS selectors and XPath queries **DO NOT WORK** for most elements. You must use one of these workarounds:

### Pattern 1: elementsFromPoint (PROVEN WORKING)
```
Kapture Browser Automation:elementsFromPoint(tabId, x, y)
```
This returns all elements at a viewport coordinate. Use screenshot coordinates to target elements. LinkedIn assigns `#kapture-N` IDs to found elements which can be clicked via `Kapture Browser Automation:click(selector="#kapture-N")`.

### Pattern 2: Clipboard Paste (PROVEN WORKING for text input)
LinkedIn form fields are ProseMirror/tiptap `contenteditable` divs, NOT regular `<input>` elements. To fill them:
1. Click on the field using elementsFromPoint → `#kapture-N`
2. `Control+a` to select all existing text
3. `Backspace` to delete
4. Use PowerShell `Set-Clipboard -Value "your text"` via Desktop Commander
5. `Control+v` to paste

### Pattern 3: Tab Key Navigation
Tab key moves between form fields inside LinkedIn modals. Useful when you can't find a field via elementsFromPoint.

### Pattern 4: Direct URL Navigation
LinkedIn edit forms have predictable URLs:
- Edit intro: `https://www.linkedin.com/in/{slug}/edit/intro/`
- Edit about: `https://www.linkedin.com/in/{slug}/edit/forms/summary/new`
- Edit experience: `https://www.linkedin.com/in/{slug}/edit/forms/position/new/`

## Profile: Matt Michels
- URL: `https://www.linkedin.com/in/matt-michels-b836b260/`
- Headline: "AI/LLM Infrastructure Engineer | MCP Server Builder | Python & Rust | DevOps & QA Automation"
- About: Full professional summary (saved 2026-03-17)

## Workflow: Update Headline

1. Navigate to `https://www.linkedin.com/in/matt-michels-b836b260/edit/intro/`
2. Wait for "Edit intro" modal to appear
3. Tab through fields: First name → Last name → Additional name → Pronouns → **Headline**
4. The Headline field is a ProseMirror editor. Use elementsFromPoint at approximately (650, 496) to find it
5. Click the field, `Control+a`, `Backspace` to clear
6. `Set-Clipboard` + `Control+v` to paste new headline
7. Find Save button via elementsFromPoint at approximately (1285, 755) → `#kapture-N`
8. Click Save

## Workflow: Update About Section

1. Navigate to `https://www.linkedin.com/in/matt-michels-b836b260/edit/forms/summary/new`
2. The About text area is a ProseMirror editor
3. Use elementsFromPoint at approximately (700, 280) to find the editor div
4. Click it, `Control+a`, `Backspace`, then clipboard paste
5. Save button is at the bottom-right of the dialog footer (~1285, 755)

## Workflow: LinkedIn Easy Apply

1. Navigate to LinkedIn job URL (e.g., `https://www.linkedin.com/jobs/view/{jobId}/`)
2. Find "Easy Apply" button — use elementsFromPoint or screenshot
3. Click Easy Apply to open the application modal
4. Modal has multiple steps — fill each with Tab navigation + clipboard paste
5. Common fields: Phone, Resume (already uploaded), Cover letter, Additional questions
6. Submit button at the bottom of the modal

## Known Issues
- LinkedIn's DOM changes class names frequently — never rely on CSS classes
- elementsFromPoint IDs (`#kapture-N`) are only stable within a single page session
- Claude in Chrome:navigate often times out on LinkedIn — use Kapture:navigate instead
- LinkedIn modals don't scroll with PageDown — use Tab to navigate between fields
- After saving, LinkedIn shows upsell dialogs — dismiss with Escape

## Tab Management
- Kapture tabs are separate from Claude in Chrome tabs
- Use `Kapture Browser Automation:list_tabs` to see Kapture tabs
- Use `Claude in Chrome:tabs_context_mcp` to see Chrome extension tabs
- LinkedIn works better in Kapture due to timeout issues with Claude in Chrome
