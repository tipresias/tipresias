"""made_score_nullable

Revision ID: 78f15e41337c
Revises: 6430c0506353
Create Date: 2021-06-22 22:48:20.828345

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "78f15e41337c"
down_revision = "6430c0506353"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("team_matches", "score", server_default=None)


def downgrade():
    op.alter_column("team_matches", "score", server_default=0)
