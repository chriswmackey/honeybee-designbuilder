"""honeybee-designbuilder translation commands."""
import sys
import json
import logging
import click

from ladybug.commandutil import process_content_to_output
from honeybee.model import Model
from honeybee_energy.simulation.parameter import SimulationParameter

import honeybee_designbuilder.writer as model_writer

_logger = logging.getLogger(__name__)


@click.group(help='Commands for translating Honeybee Model to DesignBuilder formats.')
def translate():
    pass


@translate.command('model-to-dsbxml')
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--sim-par-json', '-sp', help='Full path to a honeybee-energy SimulationParameter '
    'JSON that describes all of the settings for the simulation. If unspecified, '
    'default parameters will be generated.', default=None, show_default=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--program-name', '-p', help='Optional text to set the name of the '
    'software that will appear under under a comment in the XML to identify where '
    'it is being exported from. This can be set things like "Ladybug '
    'Tools" or "Pollination" or some other software in which this DsbXML '
    'export capability is being run. If unspecified, no comment will appear.',
    type=str, default=None, show_default=True)
@click.option(
    '--output-file', '-o', help='Optional INP file path to output the INP string '
    'of the translation. By default this will be printed out to stdout.',
    type=click.File('w'), default='-', show_default=True)
def model_to_dsbxml_cli(model_file, sim_par_json, program_name, output_file):
    """Translate a Honeybee Model to an DsbXML file.

    \b
    Args:
        model_file: Full path to a Honeybee Model file (HBJSON or HBpkl).
    """
    try:
        model_to_dsbxml(model_file, sim_par_json, program_name, output_file)
    except Exception as e:
        _logger.exception(f'Model translation failed:\n{e}')
        sys.exit(1)
    else:
        sys.exit(0)


def model_to_dsbxml(
    model_file, sim_par_json=None, program_name=None, output_file=None,
):
    """Translate a Honeybee Model to an DsbXML file.

    Args:
        model_file: Full path to a Honeybee Model file (HBJSON or HBpkl).
        sim_par_json: Full path to a honeybee-energy SimulationParameter JSON that
            describes all of the settings for the simulation. If None,
            default parameters will be generated. (Default: None).
        program_name: Optional text to set the name of the software that will
            appear under a comment in the XML to identify where it is being exported
            from. This can be set things like "Ladybug Tools" or "Pollination"
            or some other software in which this DsbXML export capability is being
            run. If None, no comment will appear. (Default: None).
        output_file: Optional INP file path to output the INP string of the
            translation. If None, the string will be returned from this function.
    """
    # load simulation parameters if specified
    sim_par = None
    if sim_par_json is not None:
        with open(sim_par_json) as json_file:
            data = json.load(json_file)
        sim_par = SimulationParameter.from_dict(data)

    # re-serialize the Model to Python
    model = Model.from_file(model_file)

    # create the DsbXML string for the model
    dsbxml_str = model_writer.model_to_dsbxml(model, sim_par, program_name)

    # write out the INP file
    return process_content_to_output(dsbxml_str, output_file)
