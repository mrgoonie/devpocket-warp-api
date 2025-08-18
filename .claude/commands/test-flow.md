---
description: Run test flows and fix issues
---

Run code linting and all tests (similar to GitHub Actions test) to test all the flows of this project and fix any issues that arise follow the workflow below:

 $ARGUMENTS

## Notes
- The test might take a long time to finish, set your command timeout to at least 15 minutes

## Workflow
You must follow this workflow strictly:
- start with the `project-orchestrator` agent to review the issues and provide a fix plan
- proceed to implement with `backend-system-architect` agent, when the implementation is finished, test again to make sure everything work properly
- if there are any other issues, use `expert-debugger` agent to debug and fix them.
- when everything is done, use `project-orchestrator` agent to review the implementation, run the tests again to make sure everything work properly
- if everything is good to go, use `api-docs-specialist` agent to update the API documentation if needed, it will report to `project-orchestrator` agent to close the task
- finally use `project-orchestrator` agent to commit and push all the code
