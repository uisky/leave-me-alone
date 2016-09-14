#!/usr/bin/env python

from flask_script import Manager, Server

from lma import app
from manage import *


manager = Manager(app)

manager.add_command("runserver", Server(port=8000))
manager.add_command('recount', Recount())


if __name__ == "__main__":
    manager.run()
