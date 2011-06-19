import sys
import urllib
import urlparse
import os

import web
import markdown


# local webpy mods

class TemplateString(web.template.Template):

    def __call__(self, *a, **kw):
        out = self.t(*a, **kw)
        return str(self._join_output(out))
        
class StringRender(web.template.Render):
        
    def _load_template(self, name):
        path = os.path.join(self._loc, name)
        if os.path.isdir(path):
            return StringRender(path, **self._keywords)
        else:
            path = self._findfile(path)
            if path:
                return TemplateString(open(path).read(), filename=path, **self._keywords)
            else:
                raise AttributeError, 'No template named ' + name            


# app init

base_path = os.path.abspath(os.path.dirname(__file__)) + '/'
sys.path += [base_path + dir for dir in ['.conf', '.mod']]
if not os.path.exists(base_path + '.conf/basic_setup.py'):
    urls = ('/system_status', 'system_status',
            '/.*', 'setup')
    app = web.application(urls, globals())
    application = app.wsgifunc()
    render = web.template.render(base_path + 'templates/')
    s = None
else:

    from basic_setup import *
    from exception import *

    web.config.smtp_server = mail['server']
    web.config.smtp_port = mail['port']
    web.config.smtp_username = mail['username']
    web.config.smtp_password = mail['password']
    web.config.smtp_starttls = mail['starttls']

    urls = ('/login', 'login',
            '/auth', 'auth',
            '/register', 'register',
            '/confirm_email', 'confirm_email',
            '/forgot', 'forgot',
            '/profile', 'profile',
            '/forum.*', 'bbs',
            '/post', 'post',
            '/site index', 'site_index',
            '/error', 'error',
            '/create', 'create',
            '/edit', 'edit',
            '/blog_create', 'blog_create',
            '/blog_edit', 'blog_edit',
            '/upload_profile_pic', 'upload_profile_pic',
            '/level_up', 'chlev',
            '/troglify', 'chlev',
            '/lock', 'chlev',
            '/sitemap.txt', 'sitemap4google',
            '/(.*)', 'wiki')
    app = web.application(urls, globals())
    application = app.wsgifunc()
    db = web.database(**db_info)
    stow = web.utils.storage
    s = web.session.Session(app, web.session.DBStore(db, 'session'), initializer={'user':None})
    render = web.template.render(base_path + 'templates/')
    strender = StringRender(base_path + 'templates/')

    logo = db.select('file',
                     {'f':int(db.select('code', {'n':'logo_file_id'}, where='name = $n')[0].val)},
                     where='id = $f',
                     order='id')[0].path
    menu = [code.val for code in db.select('code', {'n':'menu_item'}, where='name = $n', order='id')]


# main app code

class setup:
    def GET(self):
        return render.setup()

    def POST(self):
        f = web.input()
        bs = open(base_path + '.conf/basic_setup.py', 'w')
        bs.write(str(render.basic_setup(f)).replace('~', "'''"))
        bs.close()

        import basic_setup as bs

        db = web.database(**bs.db_info)
        db.insert('member', **bs.consul)
        db.insert('board', **bs.board)
        db.insert('post', **bs.welcome)
        db.insert('post', **bs.ntp)
        db.update('page', where='id = 1', owner=bs.consul['name'])
        web.seeother('/system_status')

class system_status:
    def GET(self):
        return render.system_status()

class login:
    def POST(self):
        try:
            f = web.input()
            user = db.select('member', {'u':f.user, 'p':f.password}, where='name = $u AND password = $p')
            redirect_to = f.has_key('redirect_to') and f.redirect_to or '/'
            if not user:
                user = db.select('member', {'u':f.user}, where='name = $u')
                if not user:
                    raise User(f.user)
                else:
                    raise Password
            if user[0].level < 2:
                raise Locked(f.user)
            s.user = f.user
            return web.seeother(redirect_to)
        except (User, Password, Locked), e:
            web.seeother('/auth?page=%s&amp;broadcast=%s' % (redirect_to, e.value))
        except:
            web.seeother('/auth?page=%s' % redirect_to)

class auth:
    def GET(self):
        f = web.input()
        page = f.has_key('page') and f.page or None
        broadcast = f.has_key('broadcast') and f.broadcast or None
        return render.auth(site['name'], page, broadcast)

class register:
    def GET(self):
        f = web.input()
        broadcast = f.has_key('broadcast') and f.broadcast or None
        user = f.has_key('user') and f.user or None
        email = f.has_key('email') and f.email or None
        return render.register(broadcast, user, email)

    def POST(self):
            import random
#        try:
            f=web.input()
            if f.password != f.confirm:
                raise ConfirmPassword
            exists = db.select('member', {'u':f.user}, where='name = $u')
            if exists:
                raise DuplicateHandle(f.user)
            exists = db.select('member', {'e':f.email}, where='email = $e')
            if exists:
                raise UserExists(f.email)
            db.insert('member',
                      name=f.user,
                      password=f.password,
                      email=f.email,
                      terms_accepted=f.terms)
            user_id = db.select('member', {'u':f.user}, where='name = $u')[0].id
            code = str(random.randint(111,999)) + str(user_id)
            message = render.confirm_email(web.ctx.host, f.user, code)
            web.sendmail('Nuthouse admin <%s>' % web.config.smtp_username, f.email, 'email address confirmation', message)
            web.seeother('/?broadcast=Thank you for registering. To complete the process please confirm your email address.')
#        except ConfirmPassword, e:
#            web.seeother('/register?broadcast=%s&amp;user=%s&amp;email=%s'
#                         % (e.value, f.user, urllib.quote(f.email)))
#        except DuplicateHandle, e:
#            web.seeother('/register?broadcast=%s&amp;email=%s'
#                         % (e.value, urllib.quote(f.email)))
#        except UserExists, e:
#            web.seeother('/register?broadcast=%s&amp;user=%s'
#                         % (e.value, f.user))
#        except:
#            web.seeother('/error?error=%s' % urllib.quote('Unknown error, apologies'))

class confirm_email:
    def GET(self):
        try:
            f = web.input()
            db.update('member',
                      where="name = '%s' AND id = %s" % (f.user, f.code[3:]),
                      level=3)
            email = db.select('member', {'u':f.user}, where="name = $u")[0].email
            message = render.welcome(f.user, web.ctx.host)
            web.sendmail('Nuthouse admin <%s>' % web.config.smtp_username, email, 'thank you for registering',
                         message, headers=({'Content-Type':'text/html; charset=UTF-8'}))
            web.seeother('/auth?broadcast=Registration complete')
        except:
            web.seeother('/error?error=%s' % urllib.quote('Unknown error, apologies'))

class forgot:
    def GET(self):
        try:
            raise Unfinished
        except Unfinished, e:
            web.seeother('/error?error=%s' % urllib.quote(e.value))

class profile:
    def GET(self):
        f = web.input()
        vars = {'u':f.user}
        user = db.select('member m LEFT JOIN file f ON m.pic = f.id, level l', vars,
                         what='joined, l.id AS level, l.name AS level_name, path AS pic',
                         where='m.level = l.id AND m.name = $u')[0]
        if f.has_key('expand_blog') and f.expand_blog == 't':
            blog = None
            expand_blog_iter = db.select('blog', vars,
                                         what="id, title, content, TO_CHAR(posted, 'YYYY-MM-DD') AS posted",
                                         where='member = $u',
                                         order='posted DESC', limit=10)
            expand_blog = [stow({'id':b.id,
                                 'title':b.title,
                                 'posted':b.posted,
                                 'content':markdown.markdown(b.content.encode('ascii', 'replace'))})
                           for b in expand_blog_iter]
        else:
            if db.select('blog', vars, what='count(*)', where='member = $u')[0].count > 1:
                expand_blog = False
            else:
                expand_blog = None
            blog = db.select('blog', vars,
                              what="id, title, content, TO_CHAR(posted, 'YYYY-MM-DD') AS posted",
                              where='member = $u',
                              order='posted DESC', limit=1)
            if blog:
                blog = blog[0]
                blog.content = markdown.markdown(blog.content.encode('ascii', 'replace'))
        recent_posts = db.select('post', vars,
                                 what="id, subject",
                                 where="member = $u AND posted > (NOW() - interval '3 months')",
                                 order='posted DESC', limit=5)
        pages = db.select('page', vars, where='owner = $u', order='path')
        slevel = db.select('member', {'m':s.user}, where='name = $m')
        slevel = slevel and slevel[0].level or 0
        show = stow({'blog_link':(f.user == s.user) and slevel > 3,
                     'patrician_controls':(f.user != s.user) and user.level > 2 and slevel > max(4, user.level),
                     'consular_controls':(f.user != s.user) and user.level < 5 and slevel > 6})
        content = render.profile(f.user, str(user.joined).split()[0], user.level_name,
                                 blog, expand_blog, recent_posts, pages, show, user.pic)
        return render.site(site,
                           s.user,
                           web.ctx.fullpath.strip('/'),
                           logo,
                           str(render.breadcrumb('Member profile: %s' % (f.user))),
                           menu,
                           f.has_key('broadcast') and f.broadcast or None,
                           content)

class bbs:
    def GET(self):
        f = web.input()
        vars = {'current':f.has_key('board') and f.board or 'main'}
        other_boards = db.select('board', vars, where='short_name != $current')
        vars = {'board':db.select('board', vars, where='short_name = $current')[0]}
        posts = db.select('post p', vars,
                          where='board = $board.id AND parent IS NULL',
                          what='''id, board, parent, subject, member,
                                  TO_CHAR(posted, 'YYYY-MM-DD HH:MI') AS posted,
                                  num_comments(id, 0) AS comments''',
                          order='posted DESC', limit=10)
        content = render.bbs(vars['board'], posts, s.user, other_boards)
        return render.site(site,
                           s.user,
                           web.ctx.fullpath.strip('/'),
                           logo,
                           str(render.breadcrumb(vars['board'].name)),
                           menu,
                           f.has_key('broadcast') and f.broadcast or None,
                           content)

class post:
    def GET(self):
        try:
            f = web.input()
            user = s.user and db.select('member', {'m':s.user}, where="name = $m") or None
            pid = f.has_key('pid') and int(f.pid) or 0
            vars = {'p':pid}
            if pid in [b.new_topic_post for b in db.select('board')]:
                if not user:
                    raise Access('Posting', 'plebeians and above. You must log in first')
                create_access = user[0].level > 2
                if not create_access:
                    raise Access('Posting', 'plebeians and above')
            find_post = db.select('post',
                                  vars,
                                  where='id = $p')
            find_post = find_post and find_post[0] or None
            post = find_post.subject != 'New topic' and find_post or None
            if post:
                post.content = markdown.markdown(post.content.encode('ascii', 'replace'))
            ancestors = post and db.select('dual', vars, what="ancestors($p,'') AS html")[0].html or None
            descendants = post and db.select('dual', vars, what="descendants($p,'') AS html")[0].html or None
            content = render.post(s.user, post, ancestors, descendants, f.has_key('board') and f.board or None)
            return render.site(site,
                               s.user,
                               web.ctx.fullpath.strip('/'),
                               logo,
                               db.select('dual', vars, what='crumb($p)')[0].crumb,
                               menu,
                               f.has_key('broadcast') and f.broadcast or None,
                               content)
        except Access, e:
            web.seeother(('/auth?broadcast=%s&page=' % e.value) + urllib.quote('post?pid=%s' % pid))
        except:
            web.seeother('/error?error=%s' % urllib.quote('Unknown error, apologies'))

    def POST(self):
        f = web.input()
        parent = f.has_key('parent') and int(f.parent) or None
        db.insert('post',
                  board=int(f.board),
                  parent=parent,
                  subject=f.subject,
                  content=f.content,
                  member=s.user)
        return web.seeother('/forum?board=%s' % db.select('board', {'b':int(f.board)}, where='id = $b')[0]['short_name'])

class wiki:
    def GET(self, uri):
        f = web.input()
        path = web.ctx.path.split('/')
        crumbs = path[1:-1]
        path = path and path[-1] or 'index'
        find_page = db.select('page',
                              {'p':path},
                              where='path = $p')
        page = find_page and find_page[0] or None
        try:
            try:
                if crumbs:
                    assert page.breadcrumbs == crumbs
                    raise CanonicalUrl
                else:
                    # still need to generate an attribute error if there is no page, so...
                    crumbs = page.breadcrumbs
            except AssertionError:
                raise PathMismatch('/'.join(crumbs), path)
            except AttributeError:
                if not crumbs:
                    referer = urlparse.urlparse(web.ctx.env.get('HTTP_REFERER', web.ctx.home))[2]
                    parent_page = (referer and referer != 'auth') and db.select('page', {'r':referer}, where='path = $r')[0] or None
                    crumbs = parent_page and parent_page.breadcrumbs or []
                    crumbs.append(referer.strip('/'))
                content = render.big_fat_404(path, '/'.join(crumbs))
            else:
                user = s.user and db.select('member', {'m':s.user}, where="name = $m") or None
                editable = user and (user[0].level > 4 or s.user == page.owner)
                content = render.wiki_page(markdown.markdown(page.content.encode('ascii', 'replace')),
                                           page and page.owner or None,
                                           path,
                                           editable,
                                           page and str(page.modified).split()[0] or None)
        except (PathMismatch, CanonicalUrl), e:
            web.seeother('/%s%s' % (path, e.value and '?broadcast=%s' % urllib.quote(e.value) or ''))
        else:
            return render.site(site,
                               s.user,
                               web.ctx.fullpath.strip('/'),
                               logo,
                               db.select('dual', {'p':path}, what='crumb($p)')[0].crumb,
                               menu,
                               f.has_key('broadcast') and f.broadcast or None,
                           content)


class create:
    def GET(self):
        try:
            f = web.input()
            user = s.user and db.select('member', {'m':s.user}, where="name = $m") or None
            if not user:
                raise Access('Creating pages', 'plebeians and above. You must log in first')
            create_access = user[0].level > 2
            if not create_access:
                raise Access('Creating pages', 'plebeians and above')
            crumbs = f.crumbs and f.crumbs.split('/') or []
            crumbs.append('Create page /%s' % f.path)
            crumbstring = f.crumbs and f.crumbs.replace('/', ' > ') or ''
            content = render.wiki_form(None, f.path, crumbstring, 'create', '', False)
            return render.site(site,
                               s.user,
                               web.ctx.fullpath.strip('/'),
                               logo,
                               str(render.breadcrumb(crumbs)),
                               menu,
                               f.has_key('broadcast') and f.broadcast or None,
                               content)
        except Access, e:
            web.seeother(('/auth?broadcast=%s&page=' % e.value) + urllib.quote(web.ctx.fullpath.strip('/')))
        except:
            web.seeother('/error?error=%s' % urllib.quote('Unknown error, apologies'))

    def POST(self):
        f = web.input()
        crumbs = [b.strip() for b in f.crumbs.split('>') if b != '']
        bread = crumbs and 'breadcrumbs=crumbs,' or ''
        insert_str = '''db.insert('page',
                                  name=f.name,
                                  path = f.path,
                                  %s
                                  content=f.content_field,
                                  owner=s.user)''' % bread
        eval(insert_str)
        return web.seeother('/%s' % f.path)


class edit:
    def GET(self):
        try:
            f = web.input()
            page = db.select('page', {'p':f.path}, where='path = $p')[0]
            user = s.user and db.select('member', {'m':s.user}, where="name = $m") or None
            if not user:
                raise Access('Editing pages', 'plebeians and above. You must log in first')
            edit_access = user and (user[0].level > 4 or s.user == page.owner)
            if not edit_access:
                raise Access('Editing pages owned by others', 'patricians and above')
            can_take = edit_access and s.user != page.owner
            breadcrumbs = page.breadcrumbs and ' > '.join(page.breadcrumbs) or ''
            content = render.wiki_form(page.name, f.path, breadcrumbs, 'edit', page.content, can_take)
            return render.site(site,
                               s.user,
                               web.ctx.fullpath.strip('/'),
                               logo,
                               str(render.breadcrumb('Edit page /%s' % f.path)),
                               menu,
                               f.has_key('broadcast') and f.broadcast or None,
                               content)
        except Access, e:
            web.seeother(('/auth?broadcast=%s&page=' % e.value) + urllib.quote(web.ctx.fullpath.strip('/')))
        except:
            web.seeother('/error?error=%s' % urllib.quote('Unknown error, apologies'))

    def POST(self):
        f = web.input()
        crumbs = f.crumbs and [b.strip() for b in f.crumbs.split('>') if b != ''] or None
        own = (f.has_key('own') and f.own == 't') and 'owner=s.user,' or ''
        update_str = '''db.update('page',
                                  where="path = '%s'",
                                  name=f.name,
                                  breadcrumbs=crumbs,
                                  content=f.content_field,
                                  %s
                                  modified='NOW')''' % (f.path, own)
        eval(update_str)
        return web.seeother('/%s' % f.path)


class blog_create:
    def GET(self):
        try:
            f = web.input()
            user = s.user and db.select('member', {'m':s.user}, where="name = $m") or None
            if not user:
                raise Access('Blogging', 'tribunes and above. You must log in first')
            create_access = user[0].level > 3
            if not create_access:
                raise Access('Blogging', 'tribunes and above')
            content = render.blog('create', None, '', '')
            return render.site(site,
                               s.user,
                               web.ctx.fullpath.strip('/'),
                               logo,
                               str(render.breadcrumb('New blog post')),
                               menu,
                               f.has_key('broadcast') and f.broadcast or None,
                               content)
        except Access, e:
            web.seeother(('/auth?broadcast=%s&page=' % e.value) + urllib.quote(web.ctx.fullpath.strip('/')))
        except:
            web.seeother('/error?error=%s' % urllib.quote('Unknown error, apologies'))

    def POST(self):
        f = web.input()
        db.insert('blog',
                  title=f.title,
                  content=f.content_field,
                  member=s.user)
        return web.seeother('/profile?user=%s' % s.user)


class blog_edit:
    def GET(self):
        try:
            f = web.input()
            user = s.user and db.select('member', {'m':s.user}, where="name = $m") or None
            if not user:
                raise Access('Blogging', 'tribunes and above. You must log in first')
            create_access = user[0].level > 3
            if not create_access:
                raise Access('Blogging', 'tribunes and above')
            blog = db.select('blog', {'b':f.bid}, where='id = $b')[0]
            if blog.member != s.user and user.level < 6:
                raise Access("Editing someone else's blog is a rarely used admin function, and",
                             'senators and above')
            content = render.blog('edit', f.bid, blog.title, blog.content)
            return render.site(site,
                               s.user,
                               web.ctx.fullpath.strip('/'),
                               logo,
                               str(render.breadcrumb('Edit blog: %s' % blog.title)),
                               menu,
                               f.has_key('broadcast') and f.broadcast or None,
                               content)
        except Access, e:
            web.seeother(('/auth?broadcast=%s&page=' % e.value) + urllib.quote(web.ctx.fullpath.strip('/')))
        except:
            web.seeother('/error?error=%s' % urllib.quote('Unknown error, apologies'))

    def POST(self):
        f = web.input()
        db.update('blog', where='id = %s' % f.bid,
                  title=f.title,
                  content=f.content_field)
        return web.seeother('/profile?user=%s' % s.user)


class upload_profile_pic:
    def GET(self):
        try:
            f = web.input()
            user = s.user and db.select('member', {'m':s.user}, where="name = $m") or None
            if not user:
                raise Access('Uploading a profile picture', 'tribunes and above. You must log in first')
            create_access = user[0].level > 3
            if not create_access:
                raise Access('Uploading a profile picture', 'tribunes and above')
            content = render.upload_profile_pic()
            return render.site(site,
                               s.user,
                               web.ctx.fullpath.strip('/'),
                               logo,
                               str(render.breadcrumb('Upload profile pic')),
                               menu,
                               f.has_key('broadcast') and f.broadcast or None,
                               content)
        except Access, e:
            web.seeother(('/auth?broadcast=%s&page=' % e.value) + urllib.quote(web.ctx.fullpath.strip('/')))
        except:
            web.seeother('/error?error=%s' % urllib.quote('Unknown error, apologies'))

    def POST(self):
        try:
            f = web.input(file={})
            if f.file.type not in ['image/jpeg', 'image/png', 'image/gif']:
                raise FileType
            filename = db.select('dual', what="nextval('file_id_seq') AS id")[0].id
            ext = f.file.filename.rsplit('.', 1)[1]
            file = open(base_path + 'static/upload/%s.%s' % (filename, ext), 'w')
            file.write(f.file.file.read())
            file.close()
            db.insert('file',
                      id=filename,
                      path='%s.%s' % (filename, ext))
            db.update('member',
                      where="name = '%s'" % s.user,
                      pic=filename)
            return web.seeother('/profile?user=%s' % s.user)
        except FileType, e:
            web.seeother('/upload_profile_pic?broadcast=%s' % e.value)
        except:
            web.seeother('/error?error=%s' % urllib.quote('Unknown error, apologies'))


class chlev:
    def GET(self):
        try:
            f = web.input()
            user = s.user and db.select('member', {'m':s.user}, where="name = $m") or None
            recipient = db.select('member', {'u':f.user},
                                  where='name = $u')[0]
            if web.ctx.path == '/level_up':
                check = stow({'level':6,
                              'action':'Promoting members',
                              'msg':'consuls'})
                target_level = recipient.level + 1
            else:
                check = stow({'level':max(4, recipient.level),
                              'action':'Dispensing punishment',
                              'msg':'patricians and above. You must be a higher level<br />than the recipient'})
                if web.ctx.path == '/lock':
                    target_level = 1
                else:
                    target_level = 2
            if not user:
                raise Access(check.action, '$s. You must log in first' % check.msg)
            access = user[0].level > check.level
            if not access:
                raise Access(check.action, check.msg)
            broadcast = db.select('dual', {'r':f.user, 't':target_level, 'u':s.user}, what='chlev($r, $t, $u)')[0].chlev
            return web.seeother('/profile?user=%s&broadcast=%s' % (f.user, broadcast))
        except Access, e:
            web.seeother(('/auth?broadcast=%s&page=' % e.value) + urllib.quote(web.ctx.fullpath.strip('/')))
        except:
            web.seeother('/error?error=%s' % urllib.quote('Unknown error, apologies'))


class site_index:
    def GET(self):
        f = web.input()
        pages = db.select('page',
                          what="path, name, TO_CHAR(modified, 'YYYY-MM-DD HH:MI') as modified",
                          order='path')
        content = render.site_index(pages)
        return render.site(site,
                           s.user,
                           web.ctx.fullpath.strip('/'),
                           logo,
                           str(render.breadcrumb('Site index')),
                           menu,
                           f.has_key('broadcast') and f.broadcast or None,
                           content)


class error:
    def GET(self):
        f = web.input()
        return render.error((f.has_key('error') and urllib.unquote(f.error) or 'Undefined error'))


class sitemap4google:
    def GET(self):
        pages = db.select('page', order='path')
        file = open(base_path + 'static/sitemap.txt', 'w')
        lines = ['%s/%s\r\n' % (web.ctx.home, p) for p in ['source', 'forum', 'site index']]
        for page in pages:
            lines.append('%s/%s\r\n' % (web.ctx.home, page.path))
        file.writelines(lines)
        file.close()
        return web.seeother('/static/sitemap.txt')


if __name__ == '__main__': app.run()
