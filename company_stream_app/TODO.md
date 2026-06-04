# TODO - Fix missing features + debug DB tables

## Step 1
- Confirm error cause: SQLite missing table `attendance`.

## Step 2
- Add/enable automatic DB table creation on app start for development (create_all) or ensure migrations are applied.

## Step 3
- Add missing/unfinished features if runtime routes/templates exist:
  - Notifications UI/endpoint wiring
  - Roles (admin/manager vs employee) + templates links
  - Analytics page/template support
  - Attendance check-in/out flow correctness

## Step 4
- Run the app and hit `/dashboard` to verify `attendance` table exists.

## Step 5
- If features are still missing, implement remaining model/route/template/controller pieces.

