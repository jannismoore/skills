# Contributing

## Skill Structure

Each skill is a directory with a `SKILL.md` file:

```
skills/
└── my-skill/
    ├── SKILL.md           # Required: main skill file
    ├── scripts/           # Optional: helper scripts
    │   └── example.py
    ├── config.json        # Optional: default configuration
    └── references/        # Optional: detailed docs
        └── api.md
```

## SKILL.md Format

```yaml
---
name: my-skill
description: |
  What this skill does and when to use it.
  Include relevant keywords so agents know when to activate.
allowed-tools: Bash(command *), Read, Write, ...
---

# My Skill

Content, examples, and commands here.
```

## Adding New Skills

1. Create `skills/<skill-name>/SKILL.md`
2. Write a clear description of when to use the skill
3. Include practical, working examples
4. Add any helper scripts or configs the skill needs
5. Update the **Available Skills** table in `README.md`
6. Test the skill end-to-end before submitting

## Installation Syntax

Skills from this repo are installed via:

```bash
# All skills
npx skills add jannismoore/skills

# Single skill
npx skills add jannismoore/skills@<skill-name>
```

## Cross-Referencing

If your skill relates to other skills in this repo, reference them:

```markdown
## Related Skills

\`\`\`bash
npx skills add jannismoore/skills@related-skill
\`\`\`
```

## Guidelines

- **Practical over theoretical** — every skill should encode a real workflow, not abstract instructions.
- **Opinionated defaults** — pick sensible defaults so the skill works out of the box.
- **Clear triggers** — describe exactly when an agent should activate this skill.
- **Portable** — skills should work across Claude Code, Cursor, and other compatible agents.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
