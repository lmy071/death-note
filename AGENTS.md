# Repository instructions

## Project overview

- This is a Vue 3 single-page application written in TypeScript and built with Vite.
- Use pnpm 11.22.0. Preserve `pnpm-lock.yaml` and do not introduce another package manager.
- Styling uses UnoCSS with `presetUno`, `presetAttributify`, project shortcuts in `vite.config.ts`, and global foundations in `src/styles/uno.css`.
- Routing uses Vue Router. Application source belongs under `src/`; static assets belong under `public/`.
- The project is deployed with OpenAI Sites. Keep `.openai/hosting.json` limited to Sites metadata and never commit deployment credentials.

## Working rules

- Preserve unrelated user changes in the working tree.
- Do not edit generated output in `dist/`, dependencies in `node_modules/`, or the historical `death-note/` output directory.
- Prefer focused changes that follow the existing component, router, UnoCSS, ESLint, and Prettier conventions.
- Reuse existing UnoCSS shortcuts and theme values before adding near-duplicates.
- Keep Vue components accessible and responsive. Add labels for interactive controls and preserve keyboard behavior.
- Avoid adding dependencies when the existing stack can implement the requested behavior.
- Use `apply_patch` for hand-written source changes. Let pnpm update dependency metadata and the lockfile.

## Validation

Run checks appropriate to the change before handing it off:

```bash
pnpm run lint
pnpm run type-check
pnpm run build
```

- Run `pnpm run format:check` when changing formatting configuration or many text files.
- A production build must retain `dist/server/index.js` and `dist/.openai/hosting.json` for Sites deployment.
- Do not publish or change Sites access unless the user explicitly requests it.

## Git conventions

- Follow the repository commit convention documented in `.github/commit-convention.md`.
- Use `<type>(optional-scope): <description>` with an allowed type such as `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `build`, `ci`, or `chore`.
- Stage only files that belong to the requested change. Never include unrelated working-tree changes.
- Commits are allowed upon request, but do not push, merge, or deploy unless the user explicitly authorizes that action.
