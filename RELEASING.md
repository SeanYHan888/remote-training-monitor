# Releasing

## Prepare

1. Update the version in `.claude-plugin/plugin.json` and add the matching
   entry to `CHANGELOG.md`.
2. Run `bash scripts/validate-release.sh` from the repository root.
   For workflow changes, also run the simulated cases in `evals/README.md`
   and record results and limitations. Package validation alone does not prove
   runtime behavior. Set the changelog date when the release is actually made.
3. Review the complete diff and confirm that no credentials, private hostnames,
   personal paths, or generated monitoring state are present.

## Publish

1. Commit and push the release candidate to `main`.
2. Wait for the `Validate distribution` GitHub Actions workflow to pass.
3. Create and push the matching `v<version>` tag, then create a GitHub release
   from the changelog entry.
4. Trigger skills.sh indexing by installing the public repository:

   ```bash
   npx skills@latest add SeanYHan888/remote-training-monitor --skill '*'
   ```

5. After the cache refreshes, verify the repository page and all four skill
   pages on skills.sh. Confirm that the install command shown there resolves
   the expected repository and skill names.
6. Verify the Claude Code marketplace install in a clean profile or isolated
   test environment.

## Announce

Publish launch copy only after the GitHub release, skills.sh pages, and both
installation paths have been verified from their public sources.
