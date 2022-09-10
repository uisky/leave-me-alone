#!/usr/bin/env python

import click

from lma import create_app
from manage import *


if __name__ == "__main__":
    app = create_app('config.local.py')

    @app.cli.command()
    def recalc():
        Recount().run()
