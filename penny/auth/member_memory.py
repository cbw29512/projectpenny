"""Token-only interface intended for a future authenticated HTTP adapter."""
from penny.memory import member_consent, member_preferences


class MemberMemoryService:
    def __init__(self, dsn):
        self.dsn = dsn

    @staticmethod
    def _require(token):
        # None must not silently select the trusted raw-UUID path.
        if type(token) is not str:
            raise PermissionError("invalid session")
        return token

    def opt_in(self, token, *, accepted_version):
        return member_consent.opt_in(self.dsn,None,accepted_version=accepted_version,
                                     _session_token=self._require(token))

    def withdraw(self, token):
        return member_consent.withdraw(self.dsn,None,_session_token=self._require(token))

    def save(self, token, epoch, preference):
        return member_preferences.save_preference(self.dsn,None,epoch,preference,
                                                  _session_token=self._require(token))

    def list(self, token):
        return member_preferences.list_preferences(self.dsn,None,
                                                   _session_token=self._require(token))

    def delete(self, token, memory_id):
        return member_preferences.delete_preference(self.dsn,None,memory_id,
                                                    _session_token=self._require(token))
