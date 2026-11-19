from apps.accounts.demo import is_demo_readonly_user


def demo_readonly(request):
    return {
        "is_demo_readonly": is_demo_readonly_user(getattr(request, "user", None)),
    }
