from django_user_agents.utils import get_user_agent
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime

def get_login_agent(request):
    user_agent = get_user_agent(request)
    os_properties = user_agent.os.family + " " + user_agent.os.version_string
    browser_properties = user_agent.browser.family + " " + user_agent.browser.version_string
    now = datetime.now()
    username = str(request.user.username).upper()
    user_email = request.user.email
    if user_agent.is_mobile:
        device_properties = "Mobile"
    elif user_agent.is_tablet:
        device_properties = "Tablet"
    elif user_agent.is_pc:
        device_properties = "PC"
    elif user_agent.is_bot:
        device_properties = "Bot"
    else:
        device_properties = "Unknown"

    send_mail(
        f"Login Agent for {username}",
        f"Hello {username},\n\nYou have logged in from a {device_properties} "
        f"device with the following properties:\n\nOperating System: {os_properties}\nBrowser: {browser_properties}\n\n"
        f"Date {now}\n----------------------------------------------------------------------\n"
        f"If this was not you, please contact us immediately.\n\nRegards,\n\tKwetu Bank",
        settings.EMAIL_HOST_USER,
        [user_email],
        fail_silently=False,

    )
