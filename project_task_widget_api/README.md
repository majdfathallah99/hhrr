
# Project Task Widget API (Odoo 17)

A tiny JSON API exposing your **Project** tasks, designed for Android app widgets (or any lightweight client).

## Endpoints

- `GET /task_widget/v1/ping` — quick auth check.  
- `GET /task_widget/v1/tasks` — list tasks.  
- `GET /task_widget/v1/projects` — list visible projects.  
- `GET /task_widget/v1/stages` — list stages (optional `project_id`).

### Auth
1. As Administrator: open *Settings → Users & Companies → Users*, open the user, then click **Generate / Reset Token** under *Task Widget API*.
2. Call endpoints with either:
   - HTTP header: `Authorization: Bearer <token>`
   - Or query string: `?token=<token>`

> Treat the token like a password.

### Query params for `/task_widget/v1/tasks`
- `my` (default `1`): only tasks assigned to the token user.
- `only_open` (default `1`): exclude folded stages.
- `project_id`: integer.
- `stage_ids`: comma-separated stage IDs.
- `search`: substring to match name/description.
- `limit` (default `50`, max `200`), `offset` (default `0`).
- `order`: one of `date_deadline asc|desc`, `priority asc|desc`, `create_date asc|desc`, `write_date asc|desc`, `sequence asc|desc`.

### Example

```bash
curl -s "https://your-odoo.com/task_widget/v1/tasks?limit=10"   -H "Authorization: Bearer YOURTOKEN"
```

## Install

1. Copy the `project_task_widget_api` folder into your addons path.
2. Update apps list, search for **Project Task Widget API**, install.
3. Generate a token for any user who will use the widget.
4. Test: `GET /task_widget/v1/ping` with your token.
