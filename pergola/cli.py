import argparse
from argparse import RawTextHelpFormatter
from .applets import *
from .platform.pergola import PergolaPlatform


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", default=0, action="count",
        help="increase logging verbosity")

    parser.add_argument(
        "--skip-prog", default=0, action="count",
        help="skips the building and programming of gateware")


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

    p_test = subparsers.add_parser(
        "test",
        description="Builds and loads an applet bitstream",
        help="builds and loads an applet bitstream")

    for action_parser in [p_run, p_build, p_dot, p_test]:
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

    applet_cls = Applet.all[args.applet]
    platform = PergolaPlatform()
    if args.action == "run":
        platform.build(applet_cls(args=args), do_program=True)
    if args.action == "build":
        platform.build(applet_cls(args=args), do_program=False)
    if args.action == "dot":
        platform.build(applet_cls(args=args), do_program=False, yosys_opts="-p show")
    elif args.action == "test":
        print("Not implemented.")

if __name__ == "__main__":
    main()
