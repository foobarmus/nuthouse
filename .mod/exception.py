class Ex(Exception):

    value = ''

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
        self.value = "Oops, this isn't finished... Apologies. Please come back in a week or so."

class PathMismatch(Ex):
    def __init__(self, crumbs, path):
        self.value = '''If you wanted to create something under '%s',
                        pick a different page identifier.<br />
                        As you can see, '%s' is already in use.''' %  (crumbs, path)

class CanonicalUrl(Ex):
    pass
