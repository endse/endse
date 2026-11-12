# Fix the GitHub profile images

## Fixes
- Header is now a GIF inside this repository, not an external banner/typing service.
- GitHub Stats and Top Languages are locally generated SVGs.
- Language totals aggregate public repositories under `endse` and the `Endsett` organization.
- Activity graph from the unreliable third-party endpoint has been removed.
- Contribution snake is generated into `assets/contribution-snake.svg` on the main branch.
- Placeholder SVGs are included so no image appears broken before the first workflow run.

## Install
1. Replace `README.md` in `endse/endse`.
2. Upload the entire `assets/` directory, preserving file names.
3. Upload `scripts/generate_profile_stats.py`.
4. Upload `.github/workflows/refresh-profile-graphics.yml`.
5. In `endse/endse`, open Settings → Actions → General → Workflow permissions and select **Read and write permissions**.
6. Open Actions → **Refresh profile graphics** → Run workflow.
7. After the run succeeds, refresh your profile. The stats, language and snake assets will be updated on `main`.
8. The workflow refreshes stats and snake daily.

## Kept from your preferred design
- Skill Icons language/tool rows
- shields.io profile badges
- Tokyo Night streak card (it was rendering in your screenshot)
- six flagship project cards
