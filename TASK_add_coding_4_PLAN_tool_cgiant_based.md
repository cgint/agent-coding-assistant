# Plan for new Cgiant-based tools

Here are the specifications for two new tools.

## 1. GIANT_ASK_CODEBASE

This tool allows asking a question about the entire codebase.

### Command Line Invocation

```bash
codegiant.sh -F -y -t "query"
```

### Parameters

-   `query`: The question to ask about the codebase.

### Use Cases

-   Analyse the codebase to understand its structure.
-   Suggest an implementation for a new feature.
-   Find relevant parts of the code for a specific task.

## 2. GIANT_REVIEW_GIT_DIFF

This tool performs a code review on the current uncommitted changes.

### Command Line Invocation

The tool will first execute `git diff` and then construct the final command.

```bash
GIT_DIFF_OUTPUT=$(git diff)
codegiant.sh -F -y -t "do a review on severe issues on the following git diff: $GIT_DIFF_OUTPUT"
```

### Description

This command will execute `git diff`, capture its output, and inject it into the prompt for `codegiant.sh`. It will then ask for a review focusing on severe issues found in the diff. This approach ensures that the `git diff` output is correctly passed to the tool.
