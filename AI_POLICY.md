# Policy on the use of generative AI tools

The project welcomes contributions made with the assistance of AI coding
assistants and agents as long as they meet all the normal criteria for
correctness, clarity, formatting and so on.

While use of AI agents and other coding assistants is acceptable, this project
**requires** that any contribution created in such a manner is disclosed and that
that fact is made obvious. The easiest way to achieve this is by including an `Assisted-by`
line in your commit message, such as the following:

```
  Assisted-by: Some AI Tool <https://someai.example.com>
```

Replacing `Some AI Tool` and the address with the name and URL of whatever tool
you used. 

**Note**: This is required to be in the commit message, _not_ just the initial
PR message text.

The Assisted-by tag should immediately precede your DCO on a separate
line. This helps the maintainers to understand where the changes came from and
to track them over time. Inspect the current git logs for many prior examples of
this convention.

# Human responsibility for contributions

_A computer can never be held accountable, therefore a computer must never make a management decision._

&emsp;&emsp;IBM Training Manual, 1979


Even if an AI assistant generates the code, commit message, and opens the PR autonomously,
this project holds the human behind the contribution wholly responsible for not just the content
of the contribution, but also for meaningfully engaging with the review process and all
other communication with the project, its maintainers, and other contributors.

Do not become a proxy for an AI chatbot.

# Regarding PR volume and review process

While this project accepts AI generated and/or assisted code contributions, all
code is reviewed by humans before merge. This project does **not** rely on AI review
tools.

If you are submitting a large volume of AI-assisted PRs, please keep in mind that
code review and merge is done exclusively by humans, and as such the speed of review
and eventual merge will not match the speed of PR generation.
