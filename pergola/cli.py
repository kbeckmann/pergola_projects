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

    for action in ["run", "build", "dot", "test"]:
        p_action = subparsers.add_parser(
            action,
            description="Builds and loads an applet bitstream",
            help="builds and loads an applet bitstream")
        p_action_applet = p_action.add_subparsers(dest="applet", metavar="APPLET")
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
