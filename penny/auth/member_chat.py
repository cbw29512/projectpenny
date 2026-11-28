"""Token-only private task admission; no public endpoint or reply delivery."""
class MemberChatService:
    def __init__(self, store):
        self.store = store

    def submit(self, token, key, payload, *, use_personal_memory=False):
        if type(token) is not str:
            raise PermissionError("invalid session")
        return self.store.submit(None,key,payload,_session_token=token,
                                 use_personal_memory=use_personal_memory)
