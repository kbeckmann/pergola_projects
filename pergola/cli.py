import logging
import argparse
from argparse import RawTextHelpFormatter
from nmigen.back.pysim import Simulator
from .applets import *
from .platform.pergola import PergolaPlatform

logger = logging.getLogger(__name__)

def run_test(applet_cls, args):
    logger.debug("Running test for '{}'".format(applet_cls.applet_name))
    applet = applet_cls.test_class(args=args)
    sim = Simulator(applet)
    applet.testbench(sim)
    gtkwave = hasattr(args, "gtkwave") and args.gtkwave
    vcd = hasattr(args, "vcd") and args.vcd

    if vcd or gtkwave:
        with sim.write_vcd("{}.vcd".format(args.applet), "{}.gtkw".format(args.applet)):
            sim.run()
    else:
        sim.run()

    if gtkwave:
        import subprocess
        subprocess.run(["gtkwave", "{}.gtkw".format(args.applet)])
        print("done")

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

    p_build = subparsers.add_parser(
        "build",
        description="Builds an applet bitstream",
        help="builds an applet bitstream")

    p_dot = subparsers.add_parser(
        "dot",
        description="Builds an applet bitstream and shows a graph of the design",
        help="builds an applet bitstream and shows a graph of the design")

    for action_parser in [p_run, p_build, p_dot]:
        p_action_applet = action_parser.add_subparsers(dest="applet", metavar="APPLET")
        for applet in Applet.all.values():
            subparser = p_action_applet.add_parser(
                applet.applet_name,
                description=applet.description,
                help=applet.help,
                formatter_class=RawTextHelpFormatter)
            applet.add_build_arguments(subparser)
            applet.add_run_arguments(subparser)

    p_test = subparsers.add_parser(
        "test",
        description="Tests an applet",
        help="tests an applet")
    p_test_applet = p_test.add_subparsers(dest="applet", metavar="APPLET")
    for applet in Applet.all.values():
        subparser = p_test_applet.add_parser(
            applet.applet_name,
            description=applet.description,
            help=applet.help,
            formatter_class=RawTextHelpFormatter)
        subparser.add_argument(
            "--vcd", default=0, action="count",
            help="Creates a .vcd and .gtkw file for waveform analysis")
        subparser.add_argument(
            "--gtkwave", default=0, action="count",
            help="Opens gtkwave after the test has run")
        applet.add_test_arguments(subparser)

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(message)s')

    if args.action == "run":
        applet_cls = Applet.all[args.applet]
        platform = PergolaPlatform()
        platform.build(applet_cls(args=args), do_program=True)
    if args.action == "build":
        applet_cls = Applet.all[args.applet]
        platform = PergolaPlatform()
        platform.build(applet_cls(args=args), do_program=False)
    if args.action == "dot":
        applet_cls = Applet.all[args.applet]
        platform = PergolaPlatform()
        platform.build(applet_cls(args=args), do_program=False, yosys_opts="-p show")
    elif args.action == "test":
        if not args.applet:
            for applet in Applet.all:
                applet_cls = Applet.all[applet]
                if hasattr(applet_cls, "test_class"):
                    run_test(applet_cls, args)
                else:
                    logger.warn("'{}' is missing a test class.".format(applet))
        else:
            applet_cls = Applet.all[args.applet]
            run_test(applet_cls, args)

if __name__ == "__main__":
    main()
