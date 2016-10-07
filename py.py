#!/usr/bin/env python

from flask_script import Manager, Server

from lma import create_app
from manage import *


app = create_app('config.local.py')
manager = Manager(app)


manager.add_command("runserver", Server(port=8000))
manager.add_command('recount', Recount())


if __name__ == "__main__":
    manager.run()
