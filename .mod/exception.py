class Ex(Exception):
    def __str__(self):
        return self.value

class User(Ex):
    def __init__(self, user):
        self.value = "%s doesn't exist" % user

class Password(Ex):
    def __init__(self):
        self.value = 'Password incorrect'

class ConfirmPassword(Ex):
    def __init__(self):
        self.value = 'Passwords did not match'

class DuplicateHandle(Ex):
    def __init__(self, username):
        self.value = '%s is already taken' % username

class UserExists(Ex):
    def __init__(self, email):
        self.value = '%s already exists... <a href="/forgot">forgot password?</a>' % email

class Locked(Ex):
    def __init__(self):
        self.value = 'Account locked'

class Access(Ex):
    def __init__(self, action, req_level):
        self.value = '%s is restricted to %s' % (action, req_level)

class FileType(Ex):
    def __init__(self):
        self.value = 'Unacceptable file type'

class Unfinished(Ex):
    def __init__(self):
        self.values = "Oops, this isn't finished... Apologies. Please come back in a week or so."
