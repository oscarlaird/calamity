import datetime

from questionary import Validator, ValidationError


class DateValidator(Validator):
    def validate(self, document):
        try:
            datetime.datetime.strptime(document.text, "%Y-%m-%d")
        except ValueError:
            raise ValidationError(
                message="Please enter a valid date (YYYY-MM-DD)",
                cursor_position=len(document.text),
            )


class CodeValidator(Validator):
    def validate(self, document):
        if len(document.text) > 10:
            raise ValidationError(
                message="Please enter a code that is less than 10 characters",
                cursor_position=len(document.text),
            )

class TimeValidator(Validator):
    def validate(self, document):
        try:
            datetime.datetime.strptime(document.text, "%H%M")
        except ValueError:
            raise ValidationError(
                message="Please enter a valid time (HHMM)",
                cursor_position=len(document.text),
            )

class RepetitionValidator(Validator):
    def validate(self, document):
        try:
            period, n = document.text.split('+')
            int(period)
            int(n)
        except ValueError:
            raise ValidationError(
                message="Please enter a valid repetition (period+repetitions)",
                cursor_position=len(document.text),
            )