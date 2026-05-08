import re


def extract_decor_code(name):
    for token in name.split():
        if re.match(r'^[A-Za-z].*\d', token):
            return token
    return ""


def extract_structure(name):
    tokens = name.split()
    for i, token in enumerate(tokens):
        if re.match(r'^[A-Za-z].*\d', token):
            if i + 1 < len(tokens) and re.match(r'^ST\d', tokens[i + 1], re.IGNORECASE):
                return tokens[i + 1]
    return ""


def derive_all(root_name):
    decor  = extract_decor_code(root_name)
    struct = extract_structure(root_name)
    group  = "KF-{}-{}".format(decor, struct) if struct else "KF-{}".format(decor)
    group_label = "{} {}".format(decor, struct).strip() if struct else decor
    return {
        "item_no":     group,
        "supplier_id": group,
        "group":       group,
        "group_label": group_label,
        "description": root_name.strip(),
        "decor":       decor,
    }


def derive_group(item_no):
    p = item_no.rsplit("-", 1)
    return p[0] if len(p) == 2 else item_no


def replace_thickness_in_name(name, t):
    result = re.sub(r'\d+mm\s*$', '{}mm'.format(t), name.rstrip())
    if result == name.rstrip():
        result = "{} {}mm".format(name.strip(), t)
    return result


def replace_thickness_in_item_no(item_no, t):
    if re.search(r'-[0-9]{1,2}$', item_no):
        p = item_no.rsplit('-', 1)
        return p[0] + '-' + str(t).zfill(2)
    return item_no + '-' + str(t).zfill(2)


def make_edge_item_no(base_item_no, width, thickness):
    group = derive_group(base_item_no)
    parts = group.split("-", 1)
    core  = parts[1] if len(parts) == 2 else group
    ts    = str(int(thickness)) if thickness == int(thickness) else str(thickness)
    return "Ka-{}-{}x{}".format(core, width, ts)


def make_edge_description(board_desc, width, thickness):
    name = re.sub(r'^Dekorspanplatte\s+', 'Sicherheitskante ABS ', board_desc)
    ts   = str(int(thickness)) if thickness == int(thickness) else str(thickness)
    ts   = ts.replace(".", ",")
    return re.sub(r'\d+mm\s*$', "{}x{}mm".format(width, ts), name.rstrip())
