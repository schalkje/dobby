## 1. Local Evidence Storage

- [x] 1.1 Create local directory structure module for before-capture storage (`.dobby/evidence/<work-item-id>/before/`)
- [x] 1.2 Implement before-capture command that accepts a work item ID and image file paths, copies them to the local evidence directory
- [x] 1.3 Implement lookup function to retrieve before-capture images for a given work item ID

## 2. Azure DevOps Integration

- [x] 2.1 Implement Azure DevOps Attachments API client to upload image files and return attachment URLs
- [x] 2.2 Add file size validation before upload with developer warning on oversized images
- [x] 2.3 Implement Azure DevOps Work Item comments API client to post HTML/markdown comments
- [x] 2.4 Implement Work Item state update (set to Done) via the Azure DevOps API

## 3. Closing Comment Formatting

- [x] 3.1 Create markdown comment template with sections: header (ID + title), What Changed, Before images, After images, Developer Notes
- [x] 3.2 Implement template renderer that fills in the markdown template with provided text, image URLs, and notes
- [x] 3.3 Ensure the rendered markdown uses only Azure DevOps-compatible HTML/markdown elements

## 4. Interactive Closing Flow

- [x] 4.1 Implement the closing flow entry point that accepts a work item ID
- [x] 4.2 Prompt the developer for a change description (text)
- [x] 4.3 Prompt the developer to attach "after" screenshot files
- [x] 4.4 Check for existing before-capture images and inform the developer of their availability
- [x] 4.5 Allow the developer to add optional free-form notes
- [x] 4.6 Show a preview of the closing comment before posting
- [x] 4.7 Implement cancel handling — abort without changing work item state or posting comments

## 5. End-to-End Integration

- [x] 5.1 Wire up the full closing flow: gather evidence → upload images → format comment → post comment → update state
- [x] 5.2 Add error handling for API failures (upload, comment post, state update) with clear developer-facing messages
- [x] 5.3 Test the closing flow with a real Azure DevOps work item to verify markdown rendering and image embedding
