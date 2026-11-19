from django.conf import settings


DEMO_READONLY_GROUP = "demo_readonly"


def demo_readonly_group_name():
    return getattr(settings, "DEMO_READONLY_GROUP", None) or DEMO_READONLY_GROUP


def is_demo_readonly_user(user):
    if user is None or not getattr(user, "is_authenticated", False):
        return False

    group_name = demo_readonly_group_name()
    if user.groups.filter(name=group_name).exists():
        return True

    demo_username = getattr(settings, "DEMO_USERNAME", "") or ""
    return bool(demo_username) and user.username == demo_username
