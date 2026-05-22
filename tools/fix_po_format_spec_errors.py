from pathlib import Path
import re
import polib


BASE_DIR = Path(__file__).resolve().parent.parent

PO_FILES = [
    BASE_DIR / "locale" / "fr" / "LC_MESSAGES" / "django.po",
    BASE_DIR / "locale" / "ru" / "LC_MESSAGES" / "django.po",
]


FORMAT_RE = re.compile(
    r"%\((?P<name>[^)]+)\)"
    r"(?P<flags>[-+0 #]*)"
    r"(?P<width>\d+)?"
    r"(?P<precision>\.\d+)?"
    r"(?P<type>[diouxXeEfFgGcrs])"
)


def extract_format_names(text):
    if not text:
        return set()

    return {match.group("name") for match in FORMAT_RE.finditer(text)}


def source_placeholders(entry):
    names = extract_format_names(entry.msgid)

    if entry.msgid_plural:
        names.update(extract_format_names(entry.msgid_plural))

    return names


def target_placeholders_from_singular(entry):
    return extract_format_names(entry.msgstr)


def target_placeholders_from_plural(entry):
    names = set()

    for value in entry.msgstr_plural.values():
        names.update(extract_format_names(value))

    return names


def reset_singular_translation(entry):
    """
    Safe fallback:
    If placeholders are broken, keep the original English msgid as msgstr.
    This prevents Django from crashing. The text can be translated later.
    """
    entry.msgstr = entry.msgid


def reset_plural_translation(entry):
    """
    Safe fallback for plural forms.
    French/Russian plural rules differ, but using msgid/msgid_plural keeps
    the PO file valid and compilable.
    """
    if not entry.msgstr_plural:
        entry.msgstr_plural[0] = entry.msgid
        entry.msgstr_plural[1] = entry.msgid_plural or entry.msgid
        return

    for key in list(entry.msgstr_plural.keys()):
        if str(key) == "0":
            entry.msgstr_plural[key] = entry.msgid
        else:
            entry.msgstr_plural[key] = entry.msgid_plural or entry.msgid


def fix_file(path):
    if not path.exists():
        print(f"{path}: missing")
        return

    po = polib.pofile(str(path))
    fixed = 0

    for entry in po:
        if entry.obsolete:
            continue

        expected = source_placeholders(entry)

        if entry.msgid_plural:
            actual = target_placeholders_from_plural(entry)

            if expected != actual:
                print("-" * 80)
                print(f"Plural placeholder mismatch in {path}")
                print(f"msgid:        {entry.msgid}")
                print(f"msgid_plural: {entry.msgid_plural}")
                print(f"expected:     {sorted(expected)}")
                print(f"actual:       {sorted(actual)}")
                reset_plural_translation(entry)
                fixed += 1

        else:
            actual = target_placeholders_from_singular(entry)

            if expected != actual:
                print("-" * 80)
                print(f"Singular placeholder mismatch in {path}")
                print(f"msgid:    {entry.msgid}")
                print(f"msgstr:   {entry.msgstr}")
                print(f"expected: {sorted(expected)}")
                print(f"actual:   {sorted(actual)}")
                reset_singular_translation(entry)
                fixed += 1

        if "fuzzy" in entry.flags:
            entry.flags.remove("fuzzy")

    po.save(str(path))
    print(f"{path}: fixed {fixed} format placeholder issue(s)")


def main():
    for path in PO_FILES:
        fix_file(path)


if __name__ == "__main__":
    main()