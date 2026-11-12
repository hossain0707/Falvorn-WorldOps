> **Public showcase:** https://falvorn-worldops-showcase.vercel.app/ — a static, simulated UX preview, not a hosted backend. This Vercel deployment was published independently via the deployment API; it is **not linked to GitHub for automatic redeployment**. Redeploy the updated `docs/showcase/index.html` after future visual changes.

# Interactive showcase — accuracy & publishing guide

The source in [showcase/index.html](showcase/index.html) is a **standalone, responsive product demonstration** with no external packages or API dependency. It features animated illustrative agents, a six-zone isometric world, town/workplace scenarios, run/pause/reset/step controls, and fabricated but explicitly labeled demonstration event data.

It is **not** an authentic recording of the running backend, a live hosted multi-agent simulation, a benchmark, or a real LLM inference endpoint. Do not describe demo metrics as observed experimental results.

## Local preview

From the repository root:

```bash
python -m http.server 8088 --directory docs/showcase
```

Open http://127.0.0.1:8088/ and use the controls. The standalone HTML also works by opening the file directly in a modern browser.

## Publish only the static showcase

Deploy the contents of \`docs/showcase/\` to a trusted static hosting provider (GitHub Pages, Vercel, Cloudflare Pages, etc.), using \`index.html\` as the entry point. Do not expose the FastAPI service or its API keys to host this preview.

GitHub Pages (manual setup): in the repository's **Settings → Pages**, publish from the \`main\` branch and \`/docs\` folder. With this approach, the showcase becomes available under \`/Falvorn-WorldOps/showcase/\`, and \`/docs/index.html\` should be added if a landing page is desired. This repository **does not claim Pages is enabled**.

For Vercel, import the repository and configure the root directory as \`docs/showcase\`, framework preset **Other**, and no build command. Confirm deployment and URL before advertising it in the README.

## Public-release publishing checklist

- [ ] Verify the demo is clearly labeled simulated on desktop and mobile
- [ ] Ensure no real credentials, tokens, personal data or internal URLs are included
- [ ] Check the README's SVG animations on desktop and mobile GitHub viewers
- [ ] Prefer reduced-motion behavior where supported and preserve meaningful alt descriptions
- [ ] Verify every badge, link and diagram against the current code
- [ ] Confirm project/license terms and research independence
- [ ] Add a real app screen recording later **only after** capturing the locally running backend, redacting access keys
- [ ] Do not market a public SaaS launch until the release checklist is complete

The SVG architecture and workflow diagrams under \`docs/assets\` describe the implementation at a conceptual level, not live telemetry. They are independently authored visual assets.
