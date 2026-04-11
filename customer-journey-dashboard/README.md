# Customer Journey Path Optimization — Dashboard

**AT70.02 · Algorithm Design & Analysis — The Two Y's · AIT 2026**

Interactive visualization of Probability-Pruned Dijkstra on customer journey graphs.

## Quick start (local)

```bash
npm install
npm run dev
```

Opens at http://localhost:5173

## Build

```bash
npm run build
```

Output goes to `dist/` — that folder is what you deploy.

---

## Deploy to Vercel (recommended — easiest)

### Option A: From GitHub (auto-deploys on every push)

1. Push this folder to a GitHub repo (or add to your existing repo as a subfolder)
2. Go to https://vercel.com → Sign in with GitHub
3. Click **"Add New Project"** → Select your repo
4. If the dashboard is in a subfolder (like `dashboard/`), set **Root Directory** to `dashboard`
5. Vercel auto-detects Vite. Click **Deploy**
6. Done. URL: `https://your-project.vercel.app`

Every `git push` auto-redeploys. No CI/CD setup needed.

### Option B: CLI (one command)

```bash
npx vercel
```

Follow prompts. First deploy creates the project. Subsequent runs update it.

---

## Deploy to Render

1. Push to GitHub
2. Go to https://render.com → **New** → **Static Site**
3. Connect your GitHub repo
4. Settings:
   - **Build Command:** `npm install && npm run build`
   - **Publish Directory:** `dist`
   - **Root Directory:** (set if in a subfolder)
5. Click **Create Static Site**

Auto-deploys on push. Free tier available.

---

## Deploy to AWS S3

```bash
# 1. Build
npm run build

# 2. Create bucket (pick your region)
aws s3 mb s3://journey-dashboard-twoy --region ap-southeast-1

# 3. Enable static hosting
aws s3 website s3://journey-dashboard-twoy \
  --index-document index.html \
  --error-document index.html

# 4. Upload
aws s3 sync dist/ s3://journey-dashboard-twoy --delete

# 5. Make public
aws s3api put-bucket-policy --bucket journey-dashboard-twoy --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::journey-dashboard-twoy/*"
  }]
}'
```

URL: `http://journey-dashboard-twoy.s3-website-ap-southeast-1.amazonaws.com`

For HTTPS, add CloudFront in front of S3.

---

## Deploy to GitHub Pages (free)

Add to `package.json` scripts:
```json
"deploy": "npm run build && npx gh-pages -d dist"
```

Then:
```bash
npm install gh-pages --save-dev
npm run deploy
```

---

## Do I need CI/CD?

**For Vercel or Render: No.** They have built-in CI/CD — push to GitHub and it auto-builds and deploys.

**For AWS S3:** You'd need to run the `aws s3 sync` command manually after each change, OR set up a GitHub Action:

Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy to S3
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm install && npm run build
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-southeast-1
      - run: aws s3 sync dist/ s3://journey-dashboard-twoy --delete
```

Add your AWS credentials as GitHub Secrets.

**For GitHub Pages:** Same idea — `gh-pages` package handles it, or use the official GitHub Pages Action.

---

## Adding to your existing repo

If you want this inside your `Customer-Journey-Path-Optimization` repo:

```bash
# From your repo root
mkdir dashboard
# Copy these files into dashboard/
cp package.json vite.config.js index.html dashboard/
cp -r src/ dashboard/src/

# Then deploy from the dashboard/ subfolder
# On Vercel: set Root Directory to "dashboard"
# On Render: set Root Directory to "dashboard"
```

Or keep it as a separate repo — either works.

## File structure

```
├── index.html          ← Entry point
├── package.json        ← Dependencies (React 18 + Vite 6)
├── vite.config.js      ← Build config
├── src/
│   ├── main.jsx        ← React mount point
│   └── App.jsx         ← Entire dashboard (single file, ~700 lines)
└── dist/               ← Build output (created by npm run build)
```

## Data is hardcoded

All numbers come from your experiment CSVs. To update after re-running experiments, edit these constants in `src/App.jsx`:

- `SD` (line ~60) — Speedup by τ table
- `MD` (line ~67) — Memory data
- `AD` (line ~68) — Adaptive τ results
- KPI values near line ~636
