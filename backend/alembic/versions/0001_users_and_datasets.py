"""users and datasets

Revision ID: 0001
Revises:
Create Date: 2026-09-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = sa.Enum("SUPER_ADMIN", "DATA_MANAGER", "VIEWER", name="user_role")
dataset_kind = sa.Enum("CLIMATE_INDICATOR", name="dataset_kind")
dataset_format = sa.Enum(
    "JSON", "CSV", "GEOJSON", "GEOTIFF", "NETCDF", "SHAPEFILE_ZIP", name="dataset_format"
)
dataset_status = sa.Enum(
    "UPLOADED",
    "VALIDATING",
    "PROCESSING",
    "FAILED",
    "VALIDATED",
    "PUBLISHED",
    "SUPERSEDED",
    name="dataset_status",
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("email", sa.String(255), nullable=True, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "datasets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("kind", dataset_kind, nullable=False),
        sa.Column("theme", sa.String(64), nullable=True),
        sa.Column("format", dataset_format, nullable=False),
        sa.Column("status", dataset_status, nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=True),
        sa.Column("validation_errors", sa.JSON(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_datasets_theme", "datasets", ["theme"])


def downgrade() -> None:
    op.drop_index("ix_datasets_theme", table_name="datasets")
    op.drop_table("datasets")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
    for enum in (dataset_status, dataset_format, dataset_kind, user_role):
        enum.drop(op.get_bind(), checkfirst=True)
