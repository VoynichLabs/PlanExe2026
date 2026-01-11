# database_api agent instructions

Scope: this package defines shared SQLAlchemy models used by multiple services
(`frontend_multi_user`, `worker_plan_database`). Keep changes compatible across
consumers.

## Guidelines
- Use the shared `db` from `database_api/planexe_db_singleton.py`; do not create
  new `SQLAlchemy()` instances or engine/session objects here.
- Models must subclass `db.Model` and use `db.Column`/`db.Enum`/`db.relationship`
  to stay aligned with Flask-SQLAlchemy expectations.
- Favor backward-compatible schema changes: new columns should be nullable and
  have safe defaults; avoid renames/drops unless all consumers are updated.
- If a new model/column is added, update any dependent service bootstrap or
  migration helpers (e.g. `worker_plan_database/app.py` or
  `frontend_multi_user/src/app.py`) and related docs.
- Allowed imports: stdlib, `sqlalchemy`, `sqlalchemy_utils`, and
  `database_api.planexe_db_singleton`.
- Forbidden imports: `worker_plan*`, `frontend_*`, `worker_plan_database`,
  `open_dir_server` (keep this package service-agnostic).
- Use UTC timestamps for defaults (`datetime.now(UTC)`), matching existing models.
- Foreign keys: this package currently avoids `ForeignKey` constraints. Do not
  add them unless explicitly instructed.
- Migrations: there is no Alembic pipeline here. Schema changes are applied via
  `db.create_all()` at service startup plus explicit ALTER helpers in
  `frontend_multi_user/src/app.py` and `worker_plan_database/app.py`. Update
  those helpers when adding columns that need backfill/ALTER.

## Example: adding a column
```python
# correct (backward compatible)
extra_notes = db.Column(db.String(256), nullable=True, default=None)

# incorrect (breaks existing rows)
extra_notes = db.Column(db.String(256), nullable=False)
```

## Testing
- Smoke-check model imports and table creation with an in-memory SQLite DB
  (run from a venv that has `flask-sqlalchemy` + `sqlalchemy-utils`, e.g.
  `frontend_multi_user`):
```bash
python - <<'PY'
from flask import Flask
from database_api.planexe_db_singleton import db
import database_api.model_event  # noqa: F401
import database_api.model_nonce  # noqa: F401
import database_api.model_taskitem  # noqa: F401
import database_api.model_worker  # noqa: F401

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
with app.app_context():
    db.create_all()
print("ok")
PY
```
