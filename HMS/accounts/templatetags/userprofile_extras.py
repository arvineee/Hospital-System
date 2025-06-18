from django import template

register = template.Library()

@register.filter
def get_user_role(user):
    try:
        return user.userprofile.role
    except Exception:
        return None
