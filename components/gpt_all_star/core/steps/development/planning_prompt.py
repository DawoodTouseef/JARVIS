from langchain_core.prompts import PromptTemplate

planning_prompt_template = PromptTemplate.from_template(
    """
# Instructions
---
Create a detailed and specific development plan in order to build a fully working application.

# Constraints
---
- Focus only on implementing source code that works perfectly according to the requirements.
- `working_directory` is very important, so please pay close attention!

# Requirements
---

## Application Specifications to be met

Application must be met with following specifications.

```specifications.md
{specifications}
```

## Technology requirements

Application must be built with following technology requirements.

```technologies.md
{technologies}
```

## UI Design to be implemented

Screen layout of the application must be same as following ui_design.

```ui_design.html
{ui_design}
```
"""
)
