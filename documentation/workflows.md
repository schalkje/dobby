There are different workflows

- idea (just some notes)
  - already in a pbi / issue; just a prompt
- pbi
  - refine
  - check if it's one pbi, or multiple, or maybe even a feature with pbi's
  - check under what feature it falls (Azure devops boards only)
  - grill plan for caveates
- Implementation plan (e.g. openspec plan)
  - grill-plan
  - grill-design: check and update the fit into the architecture
  - determine evidence
    - are pre-change screen shots necessary
    - what tests needs to be added or updated and reported about
    - are post-change screen shots necessary
- implement
- test
- generate test evidence and add to pbi/issue
- user validation

With user validation there might be a vibe phase; where based on user feed back the finisheing touches are created. These finishings might impact the pbi and specs; these need to be updated

- Finally new test evidence is created
- a new version is created (patch for pbi's; minor for features; mayor for epics)
- a pull request is created to merge to main (or a feature or development branch for single pbi's)