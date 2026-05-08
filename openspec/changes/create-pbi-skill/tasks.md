## 1. Skill Scaffolding

- [ ] 1.1 Create the skill directory at `.github/skills/create-pbi/`
- [ ] 1.2 Create the skill instruction file (`skill.md` or equivalent) with name, description, and trigger metadata
- [ ] 1.3 Define the skill's prerequisite documentation (Azure CLI + azure-devops extension)

## 2. Prerequisite Validation

- [ ] 2.1 Implement check for `az` CLI availability on PATH
- [ ] 2.2 Implement check for `azure-devops` extension installation (`az extension list`)
- [ ] 2.3 Implement authentication validation (test with `az account show`)
- [ ] 2.4 Provide actionable error messages with install/login commands for each failure case

## 3. Interactive Field Collection

- [ ] 3.1 Implement project listing and selection via `az devops project list`
- [ ] 3.2 Implement area path listing and selection via `az boards area team list`
- [ ] 3.3 Implement iteration listing and selection via `az boards iteration team list`
- [ ] 3.4 Implement parent work item search via `az boards query` (by ID or title keywords)
- [ ] 3.5 Add logic to skip prompts for fields already provided by the user

## 4. PBI Creation

- [ ] 4.1 Construct and execute `az boards work-item create` with collected fields (title, description, area path, iteration)
- [ ] 4.2 Add parent relation via `--relations` flag or `az boards work-item relation add`
- [ ] 4.3 Parse command output to extract work item ID and URL
- [ ] 4.4 Display formatted creation result (ID, title, area path, iteration, URL)

## 5. Error Handling

- [ ] 5.1 Handle and surface Azure DevOps API errors (permissions, invalid paths, etc.)
- [ ] 5.2 Handle authentication expiry mid-flow with re-auth prompt
- [ ] 5.3 Validate area path and iteration exist before attempting creation

## 6. Documentation & Testing

- [ ] 6.1 Write skill description and usage examples in the skill instruction file
- [ ] 6.2 Test end-to-end: create a PBI with all fields specified
- [ ] 6.3 Test interactive flow: create a PBI with no fields pre-specified
- [ ] 6.4 Update project README with skill usage information
