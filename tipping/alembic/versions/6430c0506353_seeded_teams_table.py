"""seeded_teams_table

Revision ID: 6430c0506353
Revises: e6d9a7e24d0f
Create Date: 2021-06-21 10:58:18.288629

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "6430c0506353"
down_revision = "e6d9a7e24d0f"
branch_labels = None
depends_on = None


TEAM_NAMES = [
    "Richmond",
    "Carlton",
    "Melbourne",
    "Essendon",
    "Collingwood",
    "North Melbourne",
    "Fremantle",
    "Brisbane",
    "Hawthorn",
    "Adelaide",
    "Geelong",
    "Sydney",
    "GWS",
    "Western Bulldogs",
    "Port Adelaide",
    "Gold Coast",
    "St Kilda",
    "West Coast",
    "Fitzroy",
    "University",
]


def upgrade():
    for name in TEAM_NAMES:
        op.execute(f"INSERT INTO teams (name) VALUES ('{name}')")


def downgrade():
    pass
