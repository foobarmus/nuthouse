SET client_encoding = 'UTF8';

CREATE PROCEDURAL LANGUAGE plpgsql;

CREATE TABLE board (
    id SERIAL PRIMARY KEY,
    short_name TEXT,
    name TEXT,
    new_topic_post INT
);


CREATE TABLE code (
    id SERIAL PRIMARY KEY,
    name TEXT,
    val TEXT,
    comment TEXT
);


CREATE TABLE dual (
    dummy TEXT
);


CREATE TABLE level (
    id SERIAL PRIMARY KEY,
    name TEXT
);


CREATE TABLE member (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE,
    password TEXT,
    email TEXT UNIQUE,
    bike TEXT,
    chapter SMALLINT,
    level SMALLINT DEFAULT 0 REFERENCES level,
    pic INT,
    terms_accepted BOOLEAN DEFAULT FALSE,
    joined TIMESTAMP DEFAULT NOW()
);


CREATE TABLE file (
    id SERIAL PRIMARY KEY,
    path TEXT,
    collection TEXT,
    uploader TEXT REFERENCES member(name)
);


CREATE TABLE level_history (
    id SERIAL PRIMARY KEY,
    member TEXT REFERENCES member(name),
    prior_level INT REFERENCES level,
    new_level INT REFERENCES level,
    effector TEXT REFERENCES member(name),
    effected TIMESTAMP DEFAULT NOW()
);


CREATE TABLE blog (
    id SERIAL PRIMARY KEY,
    title TEXT,
    content TEXT,
    member TEXT REFERENCES member(name),
    posted TIMESTAMP DEFAULT NOW()
);


CREATE TABLE page (
    id SERIAL PRIMARY KEY,
    name TEXT,
    path TEXT,
    content TEXT,
    owner TEXT REFERENCES member(name),
    modified TIMESTAMP DEFAULT NOW(),
    breadcrumbs TEXT[]
);


CREATE TABLE post (
    id SERIAL PRIMARY KEY,
    board INT REFERENCES board,
    parent INT REFERENCES post,
    subject TEXT,
    content TEXT,
    member TEXT REFERENCES member(name),
    posted TIMESTAMP DEFAULT NOW()
);


CREATE TABLE chapter (
    id SERIAL PRIMARY KEY,
    name TEXT,
    centurion TEXT REFERENCES member(name),
    board INT REFERENCES board,
    blurb TEXT,
    pic INT,
    founder TEXT REFERENCES member(name),
    founded DATE DEFAULT now()
);


CREATE TABLE session (
    session_id CHAR(128) PRIMARY KEY,
    atime TIMESTAMP DEFAULT NOW() NOT NULL,
    data TEXT
);


CREATE FUNCTION ancestors(p_id INT, p_html TEXT) RETURNS TEXT
    AS $$
DECLARE
    a RECORD;
    html TEXT:=p_html;
BEGIN
    IF has_ancestors(p_id) THEN
        IF html = '' THEN
            FOR i IN 1..num_ancestors(p_id, 0) LOOP
                html := '</ul>' || html;
            END LOOP;
        END IF;
        SELECT INTO a id, subject, member FROM post WHERE id = (SELECT parent FROM post WHERE id = p_id);
        html := '<ul class="thread"><li><a href="post?pid=' || a.id || '">' || a.subject ||
                '</a> (<a class="black" href="/profile?user=' || a.member || '">' || a.member || '</a>)</li>' || html;
        html := ancestors(a.id, html);
    END IF;
    RETURN html;
END
$$
    LANGUAGE plpgsql;


CREATE FUNCTION chlev(p_recipient TEXT, p_target_level INT, p_dispenser TEXT) RETURNS TEXT
    AS $$
DECLARE
    v_rec RECORD;
    v_old TEXT;
    v_new TEXT;
BEGIN
    SELECT INTO v_rec * FROM member WHERE name = p_recipient;
    SELECT INTO v_old name FROM level WHERE id = v_rec.level;
    SELECT INTO v_new name FROM level WHERE id = p_target_level;
    UPDATE member SET level = p_target_level WHERE name = p_recipient;
    INSERT INTO level_history VALUES (DEFAULT, v_rec.name, v_rec.level, p_target_level, p_dispenser, DEFAULT);
    RETURN v_rec.name || '''s level was changed from ' || v_old || ' to ' || v_new;
END
$$
    LANGUAGE plpgsql;


CREATE FUNCTION crumb(p_id INT) RETURNS TEXT
    AS $$
DECLARE
    p RECORD;
    html TEXT:='<a href="/">Home</a> <span class="caret">&gt;</span> ';
BEGIN
    SELECT INTO p '<a href="/forum?board=' || b.short_name || '">' || b.name || '</a> <span class="caret">&gt;</span> '
        AS board_part, subject FROM board b, post WHERE b.id = post.board AND post.id = p_id;
    html := html || p.board_part || p.subject;
    RETURN html;
END
$$
    LANGUAGE plpgsql;


CREATE FUNCTION descendants(p_id INT, p_html TEXT) RETURNS TEXT
    AS $$
DECLARE
    a RECORD;
    html TEXT:=p_html;
BEGIN
    IF has_descendants(p_id) THEN
        html := html || '<ul class="thread">';
        FOR a IN SELECT id, subject, member FROM post WHERE parent = p_id LOOP
            html := html || '<li><a href="post?pid=' || a.id || '">' || a.subject ||
                    '</a> (<a class="black" href="/profile?user=' || a.member || '">' || a.member || '</a>)</li>';
            html := descendants(a.id, html);
        END LOOP;
        html := html || '</ul>';
    END IF;
    RETURN html;
END
$$
    LANGUAGE plpgsql;


CREATE FUNCTION has_ancestors(p_id INT) RETURNS boolean
    AS $$
BEGIN
    RETURN (SELECT parent FROM post WHERE id = p_id) IS NOT NULL; 
END
$$
    LANGUAGE plpgsql;


CREATE FUNCTION has_descendants(p_id INT) RETURNS boolean
    AS $$
BEGIN
    RETURN (SELECT COUNT(*) FROM post WHERE parent = p_id) > 0;
END
$$
    LANGUAGE plpgsql;


CREATE FUNCTION new_board(p_short_name TEXT, p_name TEXT, p_welcome_message TEXT) RETURNS TEXT
    AS $$
DECLARE
    v_new_topic_post INT;
    v_new_board INT;
BEGIN
    SELECT INTO v_new_topic_post NEXTVAL('post_id_seq');
    SELECT INTO v_new_board NEXTVAL('board_id_seq');
    INSERT INTO board VALUES (v_new_board, p_short_name, p_name, v_new_topic_post);
    INSERT INTO post VALUES (v_new_topic_post, v_new_board, v_new_topic_post, 'New topic', NULL, NULL, DEFAULT);
    INSERT INTO post VALUES (DEFAULT, v_new_board, NULL, 'Welcome', p_welcome_message, 'foobarmus', DEFAULT);
    RETURN 'New topic post id = ' || v_new_topic_post;
END
$$
    LANGUAGE plpgsql;


CREATE FUNCTION num_ancestors(p_id INT, p_count INT) RETURNS INT
    AS $$
DECLARE
    a RECORD;
    count INT:=p_count;
BEGIN
    SELECT INTO a id FROM post WHERE id = (SELECT parent FROM post WHERE id = p_id);
    count := count + 1;
    count := num_comments(a.id, count);
    RETURN count;
END
$$
    LANGUAGE plpgsql;


CREATE FUNCTION num_comments(p_id INT, p_count INT) RETURNS INT
    AS $$
DECLARE
    a RECORD;
    count INT:=p_count;
BEGIN
    FOR a IN SELECT id FROM post WHERE parent = p_id LOOP
        count := count + 1;
        count := num_comments(a.id, count);
    END LOOP;
    RETURN count;
END
$$
    LANGUAGE plpgsql;


COPY code (name, val, comment) FROM stdin;
menu_item	about us	\N
menu_item	events	\N
menu_item	forum	\N
menu_item	chapters	\N
menu_item	angel request	\N
menu_item	site map	\N
\.

COPY dual (dummy) FROM stdin;
X
\.


COPY level (id, name) FROM stdin;
0	new
\.

COPY level (name) FROM stdin;
banished
legionary
champion
prefect
centurion
general
senator
founder
founder
\.

COPY page (name, path, content, modified, breadcrumbs) FROM stdin;
Search Results	search	<div id="cse-search-results"></div>\r\n<script type="text/javascript">\r\n  var googleSearchIframeName = "cse-search-results";\r\n  var googleSearchFormName = "cse-search-box";\r\n  var googleSearchFrameWidth = 600;\r\n  var googleSearchDomain = "www.google.com";\r\n  var googleSearchPath = "/cse";\r\n</script>\r\n<script type="text/javascript" src="http://www.google.com/afsonline/show_afs_search.js"></script>	2008-08-28 15:01:31.851437	\N
\.
