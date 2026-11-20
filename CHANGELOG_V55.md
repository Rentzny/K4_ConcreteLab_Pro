# v5.5 — User Accounts, Project Workspace, Internal Approvals

- Added email/password sign up and login with Supabase Auth, plus guest access to Service.
- Added cloud project creation, snapshot CSV storage, project membership, project-based access control.
- Added internal report revision, submission, review by other assigned member, approval and revision flow.
- Added read-only audit records from PostgreSQL triggers and admin user-role management.
- Added public verification QR certificate for approved report metadata only.
- Added SQL schema with Row Level Security policies and no service-role key in app code.
- On logout, clear previously loaded cloud CSV from local session state.
- Disabled global Streamlit caching of raw CSV/report bytes on Service to reduce cross-session retention.
- Added offline unit/regression tests and optional live two-user RLS integration test.

**Deployment is not automatic**: a Supabase project, SQL schema, Auth, Secrets and live RLS checks are required. Google SSO, PDF archival storage and formal signatures are NOT implemented.
