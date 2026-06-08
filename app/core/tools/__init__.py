from app.config import settings

if settings.MOCK_GOOGLE:
    from app.core.tools.mock_gmail import mock_gmail_tool as _gmail
    from app.core.tools.mock_calendar import mock_calendar_tool as _calendar
    from app.core.tools.mock_crm import mock_crm_tool as _crm

    gmail_tool = _gmail
    calendar_tool = _calendar
    crm_tool = _crm
else:
    from app.core.tools.gmail_actions import gmail_tool as _gmail
    from app.core.tools.calendar import calendar_tool as _calendar
    from app.core.tools.crm import crm_tool as _crm

    gmail_tool = _gmail
    calendar_tool = _calendar
    crm_tool = _crm

__all__ = ["gmail_tool", "calendar_tool", "crm_tool"]
