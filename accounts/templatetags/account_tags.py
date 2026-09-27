from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def topbar_user_data(context):
    request = context["request"]
    user = request.user
    if not user.is_authenticated:
        return {}

    profile = getattr(user, "profile", None)

    first_name = profile.first_name if profile and profile.first_name else ""
    last_name = profile.last_name if profile and profile.last_name else ""
    name_parts = [name for name in (first_name, last_name) if name]
    username = user.get_username()

    return {
        "first_name": first_name or username,
        "full_name": " ".join(name_parts) or username,
        "initials": "".join(name[0].upper() for name in name_parts) or username[:1].upper() or "?",
        "tier": f"{user.get_account_type_display()} account",
    }