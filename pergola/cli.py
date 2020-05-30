import logging
import argparse
from argparse import RawTextHelpFormatter
from nmigen.back.pysim import Simulator
from .applets import *
from .platform.pergola import PergolaPlatform

logger = logging.getLogger(__name__)

def add_common_parsers(parser):
    parser.add_argument(
        "--timing-allow-fail", default=0, action="count",
        help="Allow timing to fail during place and route")

    parser.add_argument(
        "--dot", default=0, action="count",
        help="Generates a dot file using yosys 'show'")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", default=0, action="count",
        help="increase logging verbosity")

    subparsers = parser.add_subparsers(dest="action", metavar="COMMAND")
    subparsers.required = True

    p_run = subparsers.add_parser(
        "run",
        description="Builds and loads an applet bitstream",
        help="builds and loads an applet bitstream")
    add_common_parsers(p_run)

    p_build = subparsers.add_parser(
        "build",
        description="Builds an applet bitstream",
        help="builds an applet bitstream")
    add_common_parsers(p_build)

    for action_parser in [p_run, p_build]:
        p_action_applet = action_parser.add_subparsers(dest="applet", metavar="APPLET")
        for applet in Applet.all.values():
            subparser = p_action_applet.add_parser(
                applet.applet_name,
                description=applet.description,
                help=applet.help,
                formatter_class=RawTextHelpFormatter)
            applet.add_build_arguments(subparser)
            applet.add_run_arguments(subparser)

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(message)s')

    build_args = {
        "nextpnr_opts": "--timing-allow-fail" if args.timing_allow_fail else "",
        "ecppack_opts": "--compress",
        "yosys_opts":   "-p show" if args.dot else "",
        "do_program":   args.action == "run",
    }

    applet_cls = Applet.all[args.applet]
    platform = PergolaPlatform()
    platform.build(applet_cls(args=args), **build_args)

if __name__ == "__main__":
    main()
