# Old-Consumer Fence Fixture

Compose an opted-in project and prove that a released legacy consumer refuses
to render rather than emitting a lossy prompt:

1. Project a fresh checkout of the template at the release tag.
2. Copy `active_roadmap.md` and `active_roadmap.slices.yaml` from this directory
   into the project's roadmap workspace.
3. Apply `layout_optin_delta.yaml`: set the layout's configured coding template
   to the contract-v1 scaffold path (the only layout change opt-in makes).
4. Run the legacy consumer's dry-run prompt generation for slice M001-S01.

Expected: the consumer refuses before writing any prompt because the v1
scaffold's slots are unconsumable by it. Emitting a legacy-shaped prompt, or
leaving any slot token in an output, fails this fixture.
