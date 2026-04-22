from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.chatbot"
    label = "chatbot"

    def ready(self):
        # Workaround for Django 5.1.x running on Python 3.14 where BaseContext.__copy__ can break
        # (crashes Django admin changelist rendering).
        try:
            from django.template.context import BaseContext

            def _fixed_copy(ctx_self):
                duplicate = object.__new__(ctx_self.__class__)
                if hasattr(ctx_self, "__dict__"):
                    duplicate.__dict__ = dict(getattr(ctx_self, "__dict__", {}))
                duplicate.dicts = ctx_self.dicts[:]
                return duplicate

            BaseContext.__copy__ = _fixed_copy
        except Exception:
            return
