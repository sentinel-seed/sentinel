# Publishing Guide - Sentinel AI Safety Extension

## Prerequisites

1. Microsoft account
2. Azure DevOps organization

## Steps to Publish

### 1. Create Publisher

1. Go to https://marketplace.visualstudio.com/manage
2. Click "Create Publisher"
3. Fill in:
   - **ID:** `sentinelseed` (cannot be changed later)
   - **Name:** `Sentinel Team`
4. Click Create

### 2. Create Personal Access Token (PAT)

1. Go to https://dev.azure.com/
2. Sign in with your Microsoft account
3. Click your profile icon → User settings → Personal access tokens
4. Click "New Token"
5. Configure:
   - **Name:** `vscode-marketplace`
   - **Organization:** All accessible organizations
   - **Expiration:** Custom (set longer if needed)
   - **Scopes:** Click "Custom defined" then select:
     - **Marketplace** → Check "Manage"
6. Click Create and **SAVE THE TOKEN** (you won't see it again)

### 3. Login with VSCE

```bash
cd vscode-extension
npx vsce login sentinelseed
# Paste your PAT when prompted
```

### 4. Add Icon (Optional but Recommended)

Before publishing, add an icon:
1. Create a 128x128 PNG icon
2. Save as `images/icon.png`
3. Uncomment the icon line in package.json:
   ```json
   "icon": "images/icon.png",
   ```

### 5. Publish

```bash
npx vsce publish
```

Or publish with version bump:
```bash
npx vsce publish patch   # 0.1.0 → 0.1.1
npx vsce publish minor   # 0.1.0 → 0.2.0
npx vsce publish major   # 0.1.0 → 1.0.0
```

### 6. Verify

After a few minutes, your extension will appear at:
https://marketplace.visualstudio.com/items?itemName=sentinelseed.sentinel-ai-safety

## Testing Locally Before Publishing

You can install the .vsix file locally to test:

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Click "..." menu → "Install from VSIX..."
4. Select `sentinel-ai-safety-0.1.0.vsix`

## Updating the Extension

1. Update version in package.json
2. Update CHANGELOG.md
3. Run `npx vsce publish`

## Links

- [VS Code Publishing Docs](https://code.visualstudio.com/api/working-with-extensions/publishing-extension)
- [Visual Studio Marketplace](https://marketplace.visualstudio.com/manage)
- [Azure DevOps](https://dev.azure.com/)
