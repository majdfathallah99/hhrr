# Time Off: Block Late Submissions (Odoo 17)

When enabled on the company, this module blocks employees from submitting a Time Off request more than **2 days** after the leave start date.

## How it works
- Adds a checkbox on *Settings → Companies → (your company) → Configuration → Time Off Policy → "Block late Time Off submissions (> 2 days)"*.
- When checked, users trying to **Submit** a request (the *Confirm* action) whose start date is more than 2 days in the past will get a clean ValidationError explaining why.

## Install
1. Upload `hr_timeoff_late_block` to your Odoo `addons` path.
2. Update Apps list and install.
3. Go to **Settings → Companies** and tick the checkbox on your company.

## Notes
- The check runs on submission (`action_confirm`), matching the moment users "send" their request.
- Uses `request_date_from` (if available) or falls back to `date_from`.