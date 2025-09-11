"""honeybee-designbuilder commands which will be added to the honeybee cli"""
import click
from honeybee.cli import main

from .translate import translate


@click.group(help='honeybee designbuilder commands.')
@click.version_option()
def designbuilder():
    pass


designbuilder.add_command(translate)

# add designbuilder sub-commands
main.add_command(designbuilder)
