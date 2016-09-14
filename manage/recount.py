import logging

from flask_script import Command

from lma.projects.models import Project
from lma import db


log = logging.getLogger(__name__)
log.setLevel(logging.WARNING)


class Recount(Command):
    def run(self):
        print('Обновляем счётчики во всех таблицах.')

        # users
        print('Обновляется tasks.cnt_comments...')
        db.session.execute("""UPDATE tasks SET cnt_comments = 0""")
        db.session.execute("""
            WITH stats AS (SELECT task_id, count(*) n FROM task_comments GROUP BY task_id)
            UPDATE tasks SET cnt_comments = stats.n FROM stats WHERE tasks.id = stats.task_id
        """)

        db.session.commit()
