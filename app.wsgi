import sys
import urllib
import urlparse
import os
import Image
import StringIO
import datetime

import web
import markdown


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

    urls = ('/login', 'login',
            '/auth', 'auth',
            '/register', 'register',
            '/confirm_email', 'confirm_email',
            '/forgot', 'forgot',
            '/profile', 'profile',
            '/gallery', 'gallery',
            '/forum.*', 'bbs',
            '/post', 'post',
            '/post_comment_form', 'post_comment_form',
            '/chapter/(.+)', 'chapter',
            '/join', 'join',
            '/event/(.+)', 'event',
            '/site map', 'site_map',
            '/error', 'error',
            '/create', 'create',
            '/wiki_form_advanced_options', 'wiki_form_advanced_options',
            '/edit', 'edit',
            '/blog_create', 'blog_create',
            '/blog_edit', 'blog_edit',
            '/upload_pic', 'upload_pic',
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
    menu = [code.val for code in db.select('code', {'n':'menu_item'}, where='name = $n', order='id')]

def fix_broken(crumbs):
    try:
        crumbs.remove('ignore_referer')
    except ValueError:
        pass
    except:
        crumbs = []
    for i in range(len(crumbs)):
        # add explicit crumbs payload for non-existant pages in breadcrumb list
        if not db.select('page', {'c':crumbs[i]}, where='path = $c'):
            crumbs[i] = (crumbs[i], crumbs[:i] and '/'.join(isinstance(c, tuple) and c[0] or c for c in crumbs[:i]) or 'ignore_referer')
    return crumbs

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
        try:
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
            web.sendmail('%s <%s>' % (site['name'], mail['username']), f.email, 'email address confirmation', message)
            web.seeother('/?broadcast=Thank you for registering. To complete the process please confirm your email address.')
        except ConfirmPassword, e:
            web.seeother('/register?broadcast=%s&amp;user=%s&amp;email=%s'
                         % (e.value, f.user, urllib.quote(f.email)))
        except DuplicateHandle, e:
            web.seeother('/register?broadcast=%s&amp;email=%s'
                         % (e.value, urllib.quote(f.email)))
        except UserExists, e:
            web.seeother('/register?broadcast=%s&amp;user=%s'
                         % (e.value, f.user))

class confirm_email:
    def GET(self):
        f = web.input()
        db.update('member',
                  where="name = '%s' AND id = %s" % (f.user, f.code[3:]),
                  level=2)
        email = db.select('member', {'u':f.user}, where="name = $u")[0].email
        message = render.welcome(f.user, web.ctx.host)
        web.sendmail('%s <%s>' % (site['name'], mail['username']), email, 'thank you for registering',
                     message, headers=({'Content-Type':'text/html; charset=UTF-8'}))
        web.seeother('/auth?broadcast=Registration complete')

class forgot:
    def GET(self):
        try:
            raise Unfinished
        except Unfinished, e:
            web.seeother('/error?error=%s' % urllib.quote(e.value))

class profile:
    def GET(self):
        f = web.input()
        vars_ = {'u':f.user}
        user = db.select('member m LEFT JOIN file f ON m.pic = f.id, level l', vars_,
                         what='joined, l.id AS level, l.name AS level_name, path AS pic',
                         where='m.level = l.id AND m.name = $u')[0]
        if f.has_key('expand_blog') and f.expand_blog == 't':
            blog = None
            expand_blog = list(db.select('blog', vars_,
                                          what="id, title, content, TO_CHAR(posted, 'YYYY-MM-DD') AS posted",
                                          where='member = $u',
                                          order='posted DESC', limit=10))
            for i in range(len(expand_blog)):
                expand_blog[i].content = markdown.markdown(expand_blog[i].content.encode('ascii', 'replace'))
        else:
            if db.select('blog', vars_, what='count(*)', where='member = $u')[0].count > 1:
                expand_blog = False
            else:
                expand_blog = None
            blog = db.select('blog', vars_,
                              what="id, title, content, TO_CHAR(posted, 'YYYY-MM-DD') AS posted",
                              where='member = $u',
                              order='posted DESC', limit=1)
            if blog:
                blog = blog[0]
                blog.content = markdown.markdown(blog.content.encode('ascii', 'replace'))
        recent_posts = db.select('post', vars_,
                                 what="id, subject",
                                 where="member = $u AND posted > (NOW() - interval '3 months')",
                                 order='posted DESC', limit=5)
        pages = db.select('page', vars_, where='owner = $u', order='path')
        slevel = db.select('member', {'m':s.user}, where='name = $m')
        slevel = slevel and slevel[0].level or 0
        show = stow({'blog_link':(f.user == s.user) and slevel > 2,
                     'prefect_controls':(f.user != s.user) and user.level > 1 and slevel > max(3, user.level),
                     'presidential_controls':(f.user != s.user) and user.level < 6 and slevel > 7,
                     'gallery':True})
        content = render.profile(f.user, str(user.joined).split()[0], user.level_name,
                                 blog, expand_blog, recent_posts, pages, show, user.pic)
        return render.site(site,
                           s.user,
                           web.ctx.fullpath.strip('/'),
                           str(render.breadcrumb(['Member profile: %s' % (f.user)])),
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
                           str(render.breadcrumb([vars['board'].name.lower()])),
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
                    raise Access('Posting', 'legionaries and above. You must log in first')
                create_access = user[0].level > 1
                if not create_access:
                    raise Access('Posting', 'legionaries and above')
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
                               db.select('dual', vars, what='crumb($p)')[0].crumb,
                               menu,
                               f.has_key('broadcast') and f.broadcast or None,
                               content)
        except Access, e:
            web.seeother(('/auth?broadcast=%s&page=' % e.value) + urllib.quote('post?pid=%s' % pid))

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

class post_comment_form:
    def GET(self):
        f = web.input()
        find_post = db.select('post',
                              {'p':int(f.pid)},
                              where='id = $p')
        post = find_post[0]
        return str(render.post_comment_form(post, f.has_key('board') and f.board or None))

class chapter:
    def GET(self, uri):
        f = web.input()
        chapter = db.select('chapter c LEFT JOIN file f ON c.pic = f.id',
                            {'c':uri.lower()},
                            what='c.id, name, founder, founded, centurion, blurb, path AS pic',
                            where='lower(name) = $c')[0]
        chapter.founded = chapter.founded.strftime('%B %Y')
        chapter.blurb = markdown.markdown(chapter.blurb.encode('ascii', 'replace'))
        bikes = list(db.select('member', {'c':chapter.id}, what='bike, count(bike)', where='chapter = $c', order='bike', group='bike'))
        vars_ = {'u':chapter.centurion}
        if f.has_key('expand_blog') and f.expand_blog == 't':
            blog = None
            expand_blog = list(db.select('blog', vars_,
                                          what="id, title, content, TO_CHAR(posted, 'YYYY-MM-DD') AS posted",
                                          where='member = $u',
                                          order='posted DESC', limit=10))
            for i in range(len(expand_blog)):
                expand_blog[i].content = markdown.markdown(expand_blog[i].content.encode('ascii', 'replace'))
        else:
            if db.select('blog', vars_, what='count(*)', where='member = $u')[0].count > 1:
                expand_blog = False
            else:
                expand_blog = None
            blog = db.select('blog', vars_,
                              what="id, title, content, TO_CHAR(posted, 'YYYY-MM-DD') AS posted",
                              where='member = $u',
                              order='posted DESC', limit=1)
            if blog:
                blog = blog[0]
                blog.content = markdown.markdown(blog.content.encode('ascii', 'replace'))
        user = db.select('member', {'u':s.user}, where='name = $u')
        if user:
            user = user[0]
            can_join = not user.chapter
        else:
            can_join = False
        controls = stow({'centurion':s.user == chapter.centurion,
                         'prefect':user and (user.chapter == chapter.id and user.level > 3) or False})
        recent_events = list(db.select('event',{'c':chapter.id},
                                       where='chapter = $c AND begins < CURRENT_DATE',
                                       order='begins DESC',
                                       limit=3))
        for e in recent_events:
            e.teaser = markdown.markdown(e.teaser.encode('ascii', 'replace'))
            e.wrapup = markdown.markdown(e.wrapup.encode('ascii', 'replace'))
        content = render.chapter(chapter,
                                 sum(b.count for b in bikes),
                                 bikes,
                                 blog,
                                 expand_blog,
                                 recent_events,
                                 controls,
                                 can_join)
        return render.site(site,
                           s.user,
                           web.ctx.fullpath.strip('/'),
                           str(render.breadcrumb(['chapters', chapter.name])),
                           menu,
                           f.has_key('broadcast') and f.broadcast or None,
                           content)


class wiki:
    def GET(self, uri):
        f = web.input()
        path = web.ctx.path.split('/')
        crumbs = path[1:-1]
        path = path and path[-1] or 'index'
        vars_ = {'p':path}
        find_page = db.select('page',
                              vars_,
                              where='path = $p')
        page = find_page and find_page[0] or None
        try:
            try:
                if crumbs:
                    assert page.breadcrumbs == crumbs
                    raise CanonicalUrl
                else:
                    crumbs = (f.has_key('crumbs') and f.crumbs) and f.crumbs.split('/') or page.breadcrumbs
                    if not page:
                        raise AttributeError
            except AssertionError:
                raise PathMismatch('/'.join(crumbs), path)
            except AttributeError:
                member = db.select('member', vars_, where='name = $p')
                if member:
                    return web.seeother('/profile?user=%s' % member[0].name)
                else:
                    if not crumbs:
                        referer = urllib.unquote_plus(urlparse.urlparse(web.ctx.env.get('HTTP_REFERER', web.ctx.home))[2]).strip('/')
                        actual = db.select('page', {'r':referer}, where='path = $r')
                        if referer and actual:
                            parent_page = referer != 'auth' and actual[0] or None
                            crumbs = parent_page and parent_page.breadcrumbs or []
                            crumbs.append(referer.strip('/'))
                        else:
                            crumbs = []
                    crumbs = fix_broken(crumbs)
                    content = render.big_fat_404(path, '/'.join(isinstance(c, tuple) and c[0] or c for c in crumbs))
            else:
                crumbs = fix_broken(crumbs)
                user = s.user and db.select('member', {'m':s.user}, where="name = $m") or None
                editable = user and (user[0].level > 3 or s.user == page.owner)
                content = render.wiki_page(page.name,
                                           markdown.markdown(page.content.encode('ascii', 'replace')),
                                           page.owner,
                                           path,
                                           editable,
                                           str(page.modified).split()[0])
        except (PathMismatch, CanonicalUrl), e:
            web.seeother('/%s%s' % (path, e.value and '?broadcast=%s' % urllib.quote(e.value) or ''))
        else:
            breadcrumbs = crumbs and crumbs + [path] or [path]
            return render.site(site,
                               s.user,
                               web.ctx.fullpath.strip('/'),
                               path == 'index' and 'Home' or str(render.breadcrumb(breadcrumbs)),
                               menu,
                               f.has_key('broadcast') and f.broadcast or None,
                               content)


class create:
    def GET(self):
        try:
            f = web.input()
            user = s.user and db.select('member', {'m':s.user}, where="name = $m") or None
            if not user:
                raise Access('Creating pages', 'legionaries and above. You must log in first')
            create_access = user[0].level > 1
            if not create_access:
                raise Access('Creating pages', 'legionaries and above')
            crumbs = f.crumbs and f.crumbs.split('/') or []
            crumbs.append('Create page /%s' % f.path)
            crumbstring = f.crumbs and f.crumbs.replace('/', ' > ') or ''
            content = render.wiki_form(None, f.path, crumbstring, 'create', '', False)
            return render.site(site,
                               s.user,
                               web.ctx.fullpath.strip('/'),
                               str(render.breadcrumb(crumbs)),
                               menu,
                               f.has_key('broadcast') and f.broadcast or None,
                               content)
        except Access, e:
            web.seeother(('/auth?broadcast=%s&page=' % e.value) + urllib.quote(web.ctx.fullpath.strip('/')))

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


class wiki_form_advanced_options:
    def GET(self):
        f = web.input()
        return str(render.wiki_form_advanced_options(f.name, f.crumbstring))


class edit:
    def GET(self):
        try:
            f = web.input()
            page = db.select('page', {'p':f.path}, where='path = $p')[0]
            user = s.user and db.select('member', {'m':s.user}, where="name = $m") or None
            if not user:
                raise Access('Editing pages', 'legionaries and above. You must log in first')
            edit_access = user and (user[0].level > 3 or s.user == page.owner)
            if not edit_access:
                raise Access('Editing pages owned by others', 'prefects and above')
            can_take = edit_access and s.user != page.owner
            breadcrumbs = page.breadcrumbs and ' > '.join(page.breadcrumbs) or ''
            content = render.wiki_form(page.name, f.path, breadcrumbs, 'edit', page.content, can_take)
            return render.site(site,
                               s.user,
                               web.ctx.fullpath.strip('/'),
                               str(render.breadcrumb(['Edit page /%s' % f.path])),
                               menu,
                               f.has_key('broadcast') and f.broadcast or None,
                               content)
        except Access, e:
            web.seeother(('/auth?broadcast=%s&page=' % e.value) + urllib.quote(web.ctx.fullpath.strip('/')))

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
                raise Access('Blogging', 'champions and above. You must log in first')
            create_access = user[0].level > 2
            if not create_access:
                raise Access('Blogging', 'champions and above')
            content = render.blog('create', None, '', '')
            return render.site(site,
                               s.user,
                               web.ctx.fullpath.strip('/'),
                               str(render.breadcrumb(['New blog post'])),
                               menu,
                               f.has_key('broadcast') and f.broadcast or None,
                               content)
        except Access, e:
            web.seeother(('/auth?broadcast=%s&page=' % e.value) + urllib.quote(web.ctx.fullpath.strip('/')))

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
                raise Access('Blogging', 'champions and above. You must log in first')
            create_access = user[0].level > 2
            if not create_access:
                raise Access('Blogging', 'champions and above')
            blog = db.select('blog', {'b':f.bid}, where='id = $b')[0]
            if blog.member != s.user and user.level < 7:
                raise Access("Editing someone else's blog is a rarely used admin function, and",
                             'senators and above')
            content = render.blog('edit', f.bid, blog.title, blog.content)
            return render.site(site,
                               s.user,
                               web.ctx.fullpath.strip('/'),
                               str(render.breadcrumb(['Edit blog: %s' % blog.title])),
                               menu,
                               f.has_key('broadcast') and f.broadcast or None,
                               content)
        except Access, e:
            web.seeother(('/auth?broadcast=%s&page=' % e.value) + urllib.quote(web.ctx.fullpath.strip('/')))

    def POST(self):
        f = web.input()
        db.update('blog', where='id = %s' % f.bid,
                  title=f.title,
                  content=f.content_field)
        return web.seeother('/profile?user=%s' % s.user)


class upload_pic:
    def GET(self):
        try:
            f = web.input()
            user = s.user and db.select('member', {'m':s.user}, where="name = $m") or None
            if not user:
                raise Access('Uploading pictures', 'champions and above. You must log in first')
            create_access = user[0].level > 2
            if not create_access:
                raise Access('Uploading pictures', 'champions and above')
            referer = urllib.unquote_plus(urlparse.urlparse(web.ctx.env.get('HTTP_REFERER', web.ctx.home))[2]).strip('/').split('/')
            collection = referer[0]
            help_text = blurb = ''
            if referer[0] == 'profile':
                help_text =  'Square pics work best.'
            elif referer[0] in ['chapter', 'event']:
                if referer[0] == 'chapter':
                    help_text = 'Leave blank to keep current picture.'
                    referer[1] = db.select('chapter', {'c':referer[1].lower()}, where='lower(name) = $c')[0].id
                    obj = db.select(referer[0], {'id':referer[1]}, where='id = $id')[0]
                    blurb = obj.blurb
                collection += '#%s' % referer[1]
            return render.upload_pic(collection, help_text, blurb)
        except Access, e:
            web.seeother(('/auth?broadcast=%s&page=' % e.value) + urllib.quote('/'.join(referer)))

    def POST(self):
        try:
            f = web.input(file={})
            if f.file.filename: #TODO: should also actually fire when there is no file, but the collection is something other than chapter
                if f.file.type not in ['image/jpeg', 'image/png', 'image/gif']:
                    raise FileType
                filename = db.select('dual', what="nextval('file_id_seq') AS id")[0].id
                ext = f.file.filename.rsplit('.', 1)[1]
                img = Image.open(StringIO.StringIO(f.file.file.read()))
                size = f.collection == 'profile' and (300, 300) or (600,600)
                img.thumbnail(size, Image.ANTIALIAS)
                img.save('%sstatic/upload/%s.%s' % (base_path, filename, ext))
                db.insert('file',
                          id=filename,
                          path='%s.%s' % (filename, ext),
                          collection=f.collection,
                          uploader=s.user)
            if f.collection == 'profile':
                db.update('member',
                          where="name = '%s'" % s.user,
                          pic=filename)
                redirect_to = '/profile?user=%s' % s.user
            elif f.collection == 'gallery':
                redirect_to = '/gallery?user=%s' % s.user
            else:
                type_, id_ = f.collection.split('#', 1)
                if type_ == 'chapter':
                    vars_ = {'id':id_}
                    updates = {'blurb':f.blurb}
                    if f.file.filename:
                        updates['pic'] = filename
                    db.update('chapter',
                              where='id = $id',
                              vars=vars_,
                              **updates)
                    chapter = db.select('chapter', vars_, where='id = $id')[0]
                    redirect_to = '/chapter/%s' % chapter.name
                else:
                    redirect_to = '/%s/%s' % (type_, id_)
            return web.seeother(redirect_to)
        except FileType, e:
            web.seeother('/upload_pic?broadcast=%s' % e.value) #TODO: needs to redirect to referer and preserve new blurb (in the case of chapter edits)


class join:
    def GET(self):
        f = web.input()
        content = render.join(f.chapter)
        return render.site(site,
                           s.user,
                           web.ctx.fullpath.strip('/'),
                           str(render.breadcrumb(['chapters', [f.chapter, '/chapter/%s' % f.chapter], 'join'])),
                           menu,
                           f.has_key('broadcast') and f.broadcast or None,
                           content)

    def POST(self):
        f = web.input()
        chapter = db.select('chapter', f, where='name = $chapter')[0]
        db.update('member',
                  where="name = '%s'" % s.user,
                  bike=f.bike,
                  chapter=chapter.id)
        return web.seeother('/chapter/%s' % f.chapter)

class gallery:
    def GET(self):
        f = web.input()
        if f.user:
            user = db.select('member', f, where='name = $user')[0]
            profile_pics = [p.path for p in
                            db.select('file', f,
                                      where="collection = 'profile' AND uploader = $user",
                                      order='id DESC',
                                      limit=3)]
            gallery = [p.path for p in
                       db.select('file', f,
                                 where="collection = 'gallery' AND uploader = $user",
                                 order='id DESC',
                                 limit=10)]
        content = render.gallery(f.user, None, profile_pics, gallery, [], True) # unfinished, also check gallery link image logic on profile
        return render.site(site,
                           s.user,
                           web.ctx.fullpath.strip('/'),
                           str(render.breadcrumb([[f.user, '/profile?user=%s' % f.user], 'gallery'])),
                           menu,
                           f.has_key('broadcast') and f.broadcast or None,
                           content)

class event:
    def GET(self, uri):
        f = web.input()
        vars_ = {'e':uri}
        event = db.select('event', vars_, where='id = $e')[0]
        event.teaser = markdown.markdown(event.teaser.encode('ascii', 'replace'))
        event.wrapup = markdown.markdown(event.wrapup.encode('ascii', 'replace'))
        chapter = db.select('chapter', {'c':event.chapter}, where='id = $c')[0]
        editable = s.user in [event.organiser, chapter.centurion]
        attendees = [a.member for a in db.select('attendance', vars_, where='event = $e')]
        user = s.user and db.select('member', {'m':s.user}, where="name = $m") or None
        can_attend = (user and user[0].chapter == event.chapter) and datetime.datetime.now() < event.begins - datetime.timedelta(days=1)
        gallery = [p.path for p in
                   db.select('file', {'c':'event#%s' % uri},
                             where='collection = $c',
                             order='id DESC',
                             limit=10)]
        content = render.event(event, attendees, gallery, editable, can_attend)
        return render.site(site,
                           s.user,
                           web.ctx.fullpath.strip('/'),
                           str(render.breadcrumb(['events', event.id])),
                           menu,
                           f.has_key('broadcast') and f.broadcast or None,
                           content)

class chlev:
    def GET(self):
        try:
            f = web.input()
            user = s.user and db.select('member', {'m':s.user}, where="name = $m") or None
            recipient = db.select('member', {'u':f.user},
                                  where='name = $u')[0]
            if web.ctx.path == '/level_up':
                check = stow({'level':7,
                              'action':'Promoting members',
                              'msg':'presidents'})
                target_level = recipient.level + 1
            else:
                check = stow({'level':max(3, recipient.level),
                              'action':'Demoting members',
                              'msg':'prefects and above. You must be a higher level<br />than the recipient'})
                if web.ctx.path == '/lock':
                    target_level = 1
                else:
                    target_level = recipient.level - 1
            if not user:
                raise Access(check.action, '$s. You must log in first' % check.msg)
            access = user[0].level > check.level
            if not access:
                raise Access(check.action, check.msg)
            broadcast = db.select('dual', {'r':f.user, 't':target_level, 'u':s.user}, what='chlev($r, $t, $u)')[0].chlev
            return web.seeother('/profile?user=%s&broadcast=%s' % (f.user, broadcast))
        except Access, e:
            web.seeother(('/auth?broadcast=%s&page=' % e.value) + urllib.quote(web.ctx.fullpath.strip('/')))


class site_map:
    def GET(self):
        f = web.input()
        pages = db.select('page',
                          what="path, name, TO_CHAR(modified, 'YYYY-MM-DD HH:MI') as modified",
                          order='path')
        content = render.site_map(pages)
        return render.site(site,
                           s.user,
                           web.ctx.fullpath.strip('/'),
                           str(render.breadcrumb(['site map'])),
                           menu,
                           f.has_key('broadcast') and f.broadcast or None,
                           content)


class error:
    def GET(self):
        f = web.input()
        return render.error((f.has_key('error') and urllib.unquote(f.error) or 'Undefined error'))


class sitemap4google:
    def GET(self):
        pages = db.select('page', {'s':'search'}, where="path != $s", order='path')
        file = open(base_path + 'static/sitemap.txt', 'w')
        lines = ['%s/%s\r\n' % (web.ctx.home, p) for p in ['forum']]
        for page in pages:
            lines.append('%s/%s\r\n' % (web.ctx.home, page.path))
        file.writelines(lines)
        file.close()
        return web.seeother('/static/sitemap.txt')


if __name__ == '__main__': app.run()
