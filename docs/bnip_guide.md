# BNIP Guide

This guide explains how to edit `config/default.bnip` safely and predictably.

## What BNIP Does

BNIP rules decide which items Botty keeps.
Each line is a filter expression evaluated against detected item data.

## Rule Shape

Typical rule format:

```text
[Name] == Ring && [Quality] == Rare # [Fcr] >= 10 && [Allres] >= 15
```

- Left side (`[Name]`, `[Type]`, `[Quality]`, etc.) narrows item identity.
- Right side after `#` checks stats/rolls.

## Enable or Disable Rules

- Enabled: line starts with `[...`
- Disabled: line starts with `//`

Example:

```text
//[Name] == Lemrune
[Name] == Pulrune
```

## Safe Editing Workflow

1. Copy an existing nearby rule.
2. Keep your new rule commented out initially (`//`).
3. Enable one new rule at a time.
4. Run a few games and verify behavior before adding more.

## Rule Ordering

BNIP files are easier to maintain when ordered from specific to broad.

- Put strict high-value rules first.
- Put broad catch-all rules later.
- Avoid duplicated broad rules in multiple sections.

## Common Fields You Will Use

- `[Name]`
- `[Type]`
- `[Quality]`
- `[Flag]` (for ethereal/sockets behavior)
- Stat aliases like `[Fcr]`, `[Allres]`, `[Enhanceddefense]`, `[Enhanceddamage]`

## Troubleshooting

If a desired item is not kept:

1. Confirm the rule is enabled (no `//`).
2. Relax one condition at a time.
3. Check for typos in stat aliases.
4. Ensure no local BNIP file in `config/bnip/` is overriding expectations.

If too much junk is kept:

1. Tighten broad rules.
2. Disable catch-all rules first.
3. Add stricter stat thresholds.

## Recommended Local Customization

Keep `config/default.bnip` as the team baseline.
Put personal experiments in separate local `.bnip` files under `config/bnip/` and test there first.
