# Time Off: Block Late Submissions (Odoo 17)

This module adds a policy to **block late Time Off submissions** (> 2 days after the leave start date).

## Where to enable/disable
- **Employees → Configuration → Settings**: *Time Off Policy* section (checkbox).
- Also available on **Settings → Companies → (your company) → Time Off Policy**.

## How it works
- On submit (Confirm) of a Time Off request, if the start date is older than 2 days, the system raises a user-friendly validation error.
- Multi-company aware: reads the policy from the request's company (or employee's company).

## Install
1. Upload `hr_timeoff_late_block` to your addons path.
2. Apps → Update Apps List → Install.

Generated: 2025-08-27T07:25:14.360455Z