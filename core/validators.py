import re
from datetime import datetime
from django.core.exceptions import ValidationError


def validate_date(value):
    regex = r'(?P<year>\d\d\d\d)-(?P<month>\d\d)-(?P<day>\d\d)'
    m = re.match(regex, value)
    if m:
        elements = m.groupdict()
        try:
            return datetime(int(elements['year']), int(elements['month']),
                            int(elements['day']))
        except Exception as e:
            raise ValidationError(str(e))
    else:
        raise ValidationError('Invalid date pattern')
