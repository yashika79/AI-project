import pytest
from app.db.base import Base
from app.db.session import engine
from scripts.seed_demo import seed_database


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield

