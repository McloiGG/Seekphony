# Review Checklist

Before finalizing work, verify:

## Requirements

- [ ] The change supports `REQUIREMENTS.md`
- [ ] Mandatory components are not broken
- [ ] No bonus feature was prioritized over core requirements

## Architecture

- [ ] Data logic, AI logic, backend logic, and frontend logic remain separated
- [ ] Route handlers do not contain all business logic
- [ ] Configuration and secrets are handled safely

## AI Behavior

- [ ] AI output is structured
- [ ] AI output is validated
- [ ] Fallback behavior exists
- [ ] Invalid input is handled gracefully

## Testing

- [ ] Relevant checks were run
- [ ] Results are reported honestly
- [ ] Manual demo path is still possible

## Documentation

- [ ] README or docs were updated if behavior changed
- [ ] ExecPlan was updated if this was complex work