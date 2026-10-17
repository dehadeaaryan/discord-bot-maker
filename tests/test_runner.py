from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from apps.api.db import Base, Project
from apps.runner.main import claim
from discord_bot_maker.templates import template


def test_only_one_runner_owns_a_live_lease(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'runner.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        project = Project(owner_id="owner", name="test", draft=template().model_dump_json(), desired_state="running")
        session.add(project)
        session.commit()
        project_id = project.id
        assert claim(session, project_id, "runner-a", 100)
        assert not claim(session, project_id, "runner-b", 101)
        assert claim(session, project_id, "runner-a", 110)
        assert not claim(session, project_id, "runner-b", 135)
        assert claim(session, project_id, "runner-b", 141)
        project = session.get(Project, project_id)
        project.desired_state = "stopped"
        session.commit()
        assert not claim(session, project_id, "runner-a", 200)
