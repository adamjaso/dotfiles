#!/usr/bin/env python3
import os, sys, re, argparse, json, subprocess

pam_dir = "/etc/pam.d"


def read_man_doc(module):
    module = re.sub(r"\.so", "", module)
    res = subprocess.run(
        f"man -c {module} | col -b", text=True, stdout=subprocess.PIPE, shell=True
    )
    return res.stdout.strip().split("\n")


def parse_man_section(lines, section):
    found = False
    section_lines = []
    for line in lines:
        if found and re.match(r"^[A-Z\s]{2,}\s*$", line):
            break
        elif line.strip() == section:
            found = True
        elif found:
            section_lines.append(line)
    return section_lines


def join_man_paragraphs(lines):
    paragraphs = []
    paragraph = ""
    for line in lines:
        if line == "" and paragraph:
            paragraphs.append(paragraph)
            paragraph = ""
        else:
            paragraph += line + "\n"
    return paragraphs


def match_man_paragraph(lines, mat):
    found = False
    paragraph = []
    for line in lines:
        if found and line == "":
            break
        elif re.match("^" + mat, line.strip()):
            found = True
        elif found:
            paragraph.append(line)
    return paragraph


def get_man_module_doc(man_lines):
    module_name = parse_man_section(man_lines, "NAME")
    desc_lines = parse_man_section(man_lines, "DESCRIPTION")
    desc_para = join_man_paragraphs(desc_lines)
    options_ = parse_man_section(man_lines, "OPTIONS")
    options_ = join_man_paragraphs(options_)
    options = {}
    for option in options_:
        name = option.strip().split(" ")[0]
        name = name.strip().split("=")[0]
        if re.match("^[a-z0-9_]+$", name):
            options[name] = option
    return {
        "name": "\n".join(module_name[:1]),
        "desc": "\n".join(desc_para[:1]).rstrip(),
        "options": options,
        "desc_para": desc_para,
    }


def get_desc_para(module_doc, match):
    desc = []
    for p in module_doc["desc_para"]:
        if match.lower() in p.lower():
            desc.append(p)
    if not desc:
        desc = module_doc["desc_para"][:1]
    return "\n".join(desc)


def build_man_docs(man_docs, pam_conf):
    modules = set([i["module"] for i in pam_conf if i["control"] != "include"])
    for module in modules:
        man_lines = read_man_doc(module)
        man_docs[module] = get_man_module_doc(man_lines)
    man_lines = read_man_doc("pam.conf")
    desc_lines = parse_man_section(man_lines, "DESCRIPTION")
    desc_para = join_man_paragraphs(desc_lines)
    options = [
        "account",
        "auth",
        "password",
        "session",
        "required",
        "requisite",
        "sufficient",
        "optional",
        "include",
        "substack",
    ]
    control = {}
    for p in desc_para:
        control_name = p.split("\n", 1)[0].strip()
        if control_name in options and control_name not in control:
            control[control_name] = p.rstrip()
    man_docs["control"] = control


def read_pam_conf(fn, level, stype=""):
    prefix = ">" * level
    with open(fn) as f:
        items = []
        for line in f:
            line = line.strip()
            parts = re.split(r"\s+", line)
            if not parts[0] or parts[0][0] == "#":
                continue
            elif len(parts) < 3:
                print("unsupported", parts)
                continue
            stype_, control, module = parts[:3]
            dash = stype_[0] == "-"
            if dash:
                stype_ = stype_[1:]
            if stype and stype not in [stype_, "include"]:
                continue
            module_args = parts[3:]
            module_arg_names = [n.split("=")[0] for n in module_args]
            item = {
                "fn": os.path.basename(fn),
                "prefix": prefix,
                "line": line,
                "stype": stype_,
                "control": control,
                "dash": dash,
            }
            if control != "include":
                item["module"] = module
                item["module_args"] = module_args
                item["module_arg_names"] = module_arg_names
            items.append(item)
            if control == "include":
                lines = read_pam_conf(os.path.join(pam_dir, module), level + 1, stype_)
                items.extend(lines)
    return items


help_description = """
pamtree.py is a tool for studying and troubleshooting PAM module configuration on a system

It expects an input PAM configuration file, usually from `/etc/pam.d` and evaluates the PAM syntax
in the file and outputs the evaluation order of all entries, recursing through `include` directives
and displaying their directives. It supports filtering by PAM types, such as `auth`, `session`, etc.

It also provides flags that extract relevant PAM documentation from the PAM man pages regarding
the basic directives and PAM modules. This enables a user troubleshooting PAM,

1. to start with an entrypoint config file,
2. visualize the order of evaluation of PAM directives,
3. read documentation inline on each directive and module as it's evaluated

Hopefully, this tool enables a better understanding of what the PAM system is doing and speeds
a system administrator along in the esoteric quest that is PAM configuration.
"""

p = argparse.ArgumentParser(
    description=help_description,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
p.add_argument(
    "--conf", required=True, help="a PAM configuration file, i.e. /etc/pam.d/..."
)
p.add_argument("--type", default="", help="a PAM service type")
p.add_argument(
    "--json", action="store_true", help="output JSON tree of the PAM evaluation"
)
p.add_argument(
    "--annotate",
    action="store_true",
    help="annotates each directive from all recursed files with appropriate man page documentation",
)
p.add_argument(
    "--header",
    action="store_true",
    help="when --annotate is enabled, outputs an explanatory header of output",
)
p.add_argument(
    "--no-name",
    action="store_true",
    help="when --annotate is enabled, this excludes the man page NAME from output",
)
p.add_argument(
    "--no-desc",
    action="store_true",
    help="when --annotate is enabled, this excludes the man page MODULE DESCRIPTION documentation",
)
p.add_argument(
    "--no-control",
    action="store_true",
    help="when --annotate is enabled, this excludes the man page CONTROL options documentation",
)
p.add_argument(
    "--no-module-args",
    action="store_true",
    help="when --annotate is enabled, this excludes the man page MODULE arguments documentation",
)
p.add_argument(
    "--desc-stype",
    action="store_true",
    help="when --annotate is enabled, this will only document the service type; mutually exclusive with --desc-full",
)
p.add_argument(
    "--desc-full",
    action="store_true",
    help="when --annotate is enabled, this will include full man page documentation for the MODULE",
)
args = p.parse_args()
pam_conf = read_pam_conf(args.conf, 1, args.type)
if args.json:
    print(json.dumps(pam_conf, indent=2))
else:
    man_docs = {}
    if args.annotate:
        if args.header:
            print("SERVICE_TYPE  CONTROL_OPTION  MODULE_NAME  [MODULE_ARGS...]")
        build_man_docs(man_docs, pam_conf)
    for i in pam_conf:
        print(i["prefix"] + " " + i["line"])
        if args.annotate:
            if i["control"] == "include":
                continue
            mod_doc = man_docs[i["module"]]
            if not args.no_name:
                if mod_doc["name"]:
                    print("\n" + mod_doc["name"])
            if not args.no_desc:
                if args.desc_stype:
                    print("\n" + get_desc_para(mod_doc, i["stype"]))
                elif args.desc_full:
                    print("\n" + "\n".join(mod_doc["desc_para"]))
                elif mod_doc["desc"]:
                    print("\n" + mod_doc["desc"])
            if not args.no_control:
                stype_default = f"""<{i["stype"]} not found>"""
                control_default = f"""<i["control"] not found>"""
                print("\n" + man_docs["control"].get(i["stype"], stype_default))
                print("\n" + man_docs["control"].get(i["control"], control_default))
            if not args.no_module_args:
                print()
                for n in i["module_arg_names"]:
                    print(
                        mod_doc["options"].get(n, f"       {n}: <not found>"),
                    )
                # if not i["module_arg_names"]:
                #    print()
