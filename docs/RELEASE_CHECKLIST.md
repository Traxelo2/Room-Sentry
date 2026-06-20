# Release Checklist

Use this before publishing a GitHub release.

- [ ] `config.json` is not included
- [ ] No snapshots, clips, logs, events, or runtime files are included
- [ ] No webhook URLs/tokens are present
- [ ] `python -m py_compile ...` passes
- [ ] `python migrate_config.py` passes
- [ ] README quick start still works
- [ ] CHANGELOG has a new version entry
- [ ] Zip release contains source/docs only
- [ ] Release notes mention camera testing limitations if not tested
