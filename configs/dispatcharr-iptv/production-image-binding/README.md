# Unapplied hardened AIO binding candidate

Review only. Nothing here is an installer or an authorization to deploy.
The active native release contract outside this directory remains `aio_image: null`.

Run offline checks from the repository root:

```sh
python3 -B configs/dispatcharr-iptv/production-image-binding/verify_review.py
python3 -B -m unittest discover -s configs/dispatcharr-iptv/production-image-binding/tests -v
```

`installed-targets.proposed.json` is the complete matched 80-file installation mapping,
with explicit 28-path delta against the observed 67-file working four-service baseline.
Its sources include unchanged reviewed repository files and the separate variants under
`candidate/`. Do not install only the image or blindly overlay every candidate directory.
All targets require root:root 0644; runtime/private directory modes are separate lifecycle
requirements. `rollback-targets.json` describes the exact known-good four-service public
baseline, not the retired three-service baseline.

`compose.effective.review.yaml` is an offline merge preview, not an install target.
`review-input-pins.json` fixes the original reviewed inputs; `artifact-hashes.json` fixes
this proposal. The source-only minimal verifier inventory is not a new host target.
No secrets, provider policy, readiness records or runtime state are included.

Read `docs/dispatcharr-production-image-binding-review.md` for the conditional deployment
and rollback procedure. Both require separate explicit production authorization.
