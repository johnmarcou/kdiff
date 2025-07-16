#!/usr/bin/env python3
import base64
import difflib
import glob
import os
import sys
from pprint import pprint

import click
import yaml
from colorama import Back, Fore, Style, init
from prettytable import PrettyTable

# Hack from https://github.com/yaml/pyyaml/issues/683#issuecomment-1371681056
del yaml.resolver.Resolver.yaml_implicit_resolvers["="]

# Colour management
if sys.stdout.isatty():
    _COLOURS = True
else:
    _COLOURS = False
yellow = Fore.YELLOW if _COLOURS else ""
reset = Style.RESET_ALL if _COLOURS else ""
green = Fore.GREEN if _COLOURS else ""
red = Fore.RED if _COLOURS else ""


class Resource:
    def __init__(self, res, labels):
        self.kind = res.get("kind")
        self.api = res.get("apiVersion")
        self.name = res.get("metadata", {}).get("name") or res.get("metadata", {}).get(
            "generateName"
        )
        self.annotations = res.get("metadata", {}).get("annotations", {})
        if self.annotations is None:
            self.annotations = {}

        self.hook = self.annotations.get("argocd.argoproj.io/hook", "Live")
        self.wave = self.annotations.get("argocd.argoproj.io/sync-wave", 0)

        # res = self.cleanup(res)

        self.manifest = res

        if labels:
            resLabels = res["metadata"].get("labels") or {}
            self.manifest["metadata"]["labels"] = resLabels
            for label in labels:
                key, value = label.split("=")
                self.manifest["metadata"]["labels"][key] = value

        self.id = f"{self.kind}-{self.api}-{self.name}"
        self.id = f"{self.kind}-{self.name}"

        # print(f'kubectl get -oyaml {self.kind} {self.name}')
        # print(f'echo ---')

    def cleanup(self, res):
        res["metadata"]["annotations"] = {}
        if "status" in res:
            del res["status"]
        if "creationTimestamp" in res["metadata"]:
            del res["metadata"]["creationTimestamp"]
        return res

    def __dict__(self):
        return self.manifest


class Stack:
    def __init__(self, path, labels):

        self.list = list()

        if path == "-":
            pipe = not sys.stdin.isatty()
            if not pipe:
                print("No data piped")
                sys.exit()
            data = ""
            for line in sys.stdin:
                data += line
            data = yaml.safe_load_all(data)

            for obj in data:
                if obj == None:
                    continue
                self.list.append(Resource(obj, labels))

        else:

            paths = (
                sorted(glob.glob(os.path.join(path, "*")))
                if os.path.isdir(path)
                else [path]
            )
            for path in paths:
                with open(path) as file:
                    data = yaml.safe_load_all(file)

                    for obj in data:
                        if obj == None:
                            continue
                        # Decode secret base64
                        if obj.get("kind") == "Secret":
                            stringData = obj.get("stringData", {})
                            for k, v in obj.get("data", {}).items():
                                if v is not None:
                                    try:
                                        stringData[k] = base64.b64decode(v).decode(
                                            "utf-8"
                                        )
                                    except:
                                        pass
                            obj["stringData"] = stringData
                        self.list.append(Resource(obj, labels))

    def __dict__(self):
        t = PrettyTable()
        t.field_names = ["Hook", "Kind", "Name"]
        for i in self.list:
            print(f"{i.kind}-{i.api}-{i.name}")

    @staticmethod
    def comparer(
        a,
        b,
        debug=False,
        ignore_argocd=False,
        listMode=False,
        verbose=False,
        filters=None,
        n=30000,
    ):

        A = {r.id: r.manifest for r in a.list}
        B = {r.id: r.manifest for r in b.list}

        allres = sorted(set(list(A.keys()) + list(B.keys())))

        for res in allres:
            if filters and not any(filter in res for filter in filters):
                continue

            if res in A and res in B:
                res1 = A.get(res)
                res2 = B.get(res)
                if debug:
                    print(res1)
                    print(res2)
                if ignore_argocd:
                    (res1.get("metadata", {}).get("annotations", {}) or {}).pop(
                        "argocd.argoproj.io/tracking-id", None
                    )
                    (res2.get("metadata", {}).get("annotations", {}) or {}).pop(
                        "argocd.argoproj.io/tracking-id", None
                    )
                s1 = yaml.dump(res1)
                s2 = yaml.dump(res2)
                mydiff = diff(s1, s2, n)
                mydiff = color_diff(mydiff)
                mydiff = "".join(mydiff)
                mydiff = mydiff.split("\n", 3)[-1]

                # if no diff...
                if mydiff == "":
                    verb = "Unchanged"
                    if verbose:
                        print(f"{yellow}### {verb} {res} ###{reset}")
                        if not listMode:
                            print(s1)
                            print("---")

                # if diff ...
                if mydiff != "":
                    verb = "Modified"
                    print(f"{yellow}### {verb} {res} ###{reset}")
                    if not listMode:
                        print(mydiff)
                        print("---")

            elif res in A:
                verb = "Removed"
                print(f"{yellow}### {verb} {res} ###{reset}")
                if not listMode:
                    print(f"{red}{yaml.dump(A.get(res))}{reset}")
                    print("---")

            elif res in B:
                verb = "Added"
                print(f"{yellow}### {verb} {res} ###{reset}")
                if not listMode:
                    print(f"{green}{yaml.dump(B.get(res))}{reset}")
                    print("---")


def diff(a, b, n=30000):
    a = a.splitlines(1)
    b = b.splitlines(1)
    diff = difflib.unified_diff(a, b, n=n)
    return diff


def color_diff(diff):
    for line in diff:
        if line.startswith("+"):
            yield Fore.GREEN + line + Fore.RESET
        elif line.startswith("-"):
            yield Fore.RED + line + Fore.RESET
        elif line.startswith("^"):
            yield Fore.BLUE + line + Fore.RESET
        else:
            yield line


@click.command()
@click.option("--list", "-l", is_flag=True, default=False, help="list mode")
@click.option("--debug", "-d", is_flag=True, default=False, help="debug mode")
@click.option(
    "--ignore-argocd/--no-ignore-argocd",
    "-i",
    is_flag=True,
    default=True,
    help="ignore ArgoCD tracking annotations",
)
@click.option("--verbose", "-v", is_flag=True, default=False, help="verbose mode")
@click.option(
    "--labels", "-L", multiple=True, help="add labels, e.g. -L label=value", default={}
)
@click.option("--filter", "-f", multiple=True, help="filter mode")
@click.option(
    "--number", "-n", multiple=False, help="number of lines in diff", default=30000
)
@click.argument("a", nargs=1)
@click.argument("b", nargs=1, default="", required=False)
def cli(a, b, debug, filter, ignore_argocd, list, verbose, number, labels):

    sa = Stack(a, labels)
    sb = Stack(b, labels) if b else sa

    if not b:
        verbose = True

    Stack.comparer(
        sa,
        sb,
        debug=debug,
        ignore_argocd=ignore_argocd,
        listMode=list,
        verbose=verbose,
        filters=filter,
        n=number,
    )


if __name__ == "__main__":
    cli()
