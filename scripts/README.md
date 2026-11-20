# Profile graphics scripts

Everything on the profile README that isn't plain markdown is generated here.
They use only the Python standard library, so there's nothing to install.

| Script | Output | Data |
|---|---|---|
| `generate_hero.py` | `assets/hero.svg` | Static config at the top of the file (name, roles, tagline, status) |
| `generate_profile_stats.py` | `assets/github-stats.svg`, `assets/top-languages.svg` | GitHub REST API (user + org repos) |
| `generate_snake.py` | `assets/contribution-snake.svg` | Public contribution calendar (GraphQL fallback) |
| `github_api.py` | | Shared HTTP / contribution helpers |

```bash
python scripts/generate_hero.py
GH_TOKEN=... python scripts/generate_profile_stats.py   # token optional, raises rate limit
python scripts/generate_snake.py                        # add --demo for offline random data
```

`.github/workflows/refresh-profile-graphics.yml` runs all three every day, and whenever a script changes, then commits the updated SVGs.
It needs **Settings → Actions → General → Workflow permissions → Read and write**.

Change the user or org with the `PROFILE_USER` / `PROFILE_ORG` environment variables.

## How the snake grows

The snake starts as a single head and uses BFS to go after the nearest uneaten square, avoiding its own body.
Each square adds growth based on its level (1 to 4). Growth is added one segment per step, so the tail visibly stays in place while the snake gets longer.
Growth is scaled so the snake keeps growing for the whole run and reaches `MAX_LENGTH` at the end.
Every body segment uses the head's keyframes, delayed by `i × step`, which keeps the SVG small (around 70 KB).
