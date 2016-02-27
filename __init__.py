from flask import Flask, request, g, session, redirect, url_for, \
     render_template, flash
from flask.ext.github import GitHub
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from werkzeug.contrib.fixers import ProxyFix
from random import randint
from functools import wraps
import os
import time
import redis
import elasticsearch
import datetime

url = 'http://localhost:8080/posts/'
elastic_host = '127.0.0.1'
elastic_port = '9200'
index_devhub = 'devhub'
index_type = 'posts'
GITHUB_CLIENT_ID = os.environ['GITHUB_CLIENT_ID']
GITHUB_CLIENT_SECRET = os.environ['GITHUB_CLIENT_SECRET']
DATABASE_URI = 'sqlite:///./github-flask.db'
SECRET_KEY = 'HotmailIsWhereItsAt'

app = Flask(__name__)
app.config.from_object(__name__)
github = GitHub(app)
engine = create_engine(app.config['DATABASE_URI'])
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()
red = redis.StrictRedis('localhost', '6379', '1')
es = elasticsearch.Elasticsearch(elastic_host, port=elastic_port)

def init_db():
    Base.metadata.create_all(bind=engine)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(200))
    github_access_token = Column(String(200))

    def __init__(self, github_access_token):
        self.github_access_token = github_access_token


def random_with_N_digits(n):
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return randint(range_start, range_end)


def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('index'))
    return wrap


@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])


@app.after_request
def after_request(response):
    db_session.remove()
    return response


@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    idd = None

    if g.user:
        idd = g.user
        pic_url = github.get('user')["avatar_url"] + '&s=48'
    else:
        pic_url = None

    if request.method == 'POST':
      if request.form.get('tech'):
         tech = request.form.get('tech').lower()
         return redirect(url_for('search', tech=tech))

    recent_posts = red.lrange('recent_posts', 0, -1)

    return render_template('index.html', pic_url=pic_url, error=error, idd=idd,
                           recent_posts=recent_posts)


@app.route('/posts/<string:number>', methods=['GET'])
def posts(number):
    idd = None

    if g.user:
       idd = g.user
       user_id = red.hget(number, 'idd')
       pic_url = github.get('user')["avatar_url"] + '&s=48'
    else:
       idd = None
       pic_url = None
       user_id = None

    if red.hget(number, 'idd') != None:
        delete_button = None

        if idd:
          if str(user_id) == str(github.get('user')["id"]):
              delete_button = True

        num_incr = number + '-incr'
        red.incr(num_incr)

        post_dict = red.hgetall(number)
        print post_dict

        post_date = post_dict.get('post_date')
        link = post_dict.get('link')
        message = post_dict.get('message')
        title = post_dict.get('title')
        type_select = post_dict.get('type_select')
        picture = post_dict.get('pic')
        name = post_dict.get('name')
        incr = red.get(num_incr)

        return render_template('posts.html', message=message,
                               title=title, link=link, type_select=type_select,
                               picture=picture, pic_url=pic_url, name=name,
                               incr=incr, post_date=post_date,
                               delete_button=delete_button, number=number, idd=idd)
    else:
        return render_template('404.html', number=number, idd=idd)


@app.route('/post', methods=['GET', 'POST'])
@login_required
def post():
    if request.method == 'POST':
       if request.form.get('title'):
           date_time = datetime.datetime.strftime(datetime.datetime.now(),
                                                  '%Y-%m-%dT%H:%M:%S')
           post_date = datetime.datetime.strftime(datetime.datetime.now(),
                                                  '%m/%d/%Y')
           post_dict = {}
           post_num = str(random_with_N_digits(6))
           tags = request.form.get('tags').replace(",", ", ")
           post_url = url + post_num
           type_select = str(request.form.get('type_select'))
           title = str(request.form.get('title'))
           link = str(request.form.get('link'))
           name = github.get('user')["name"]
           message = str(request.form.get('message'))

           post_dict['idd'] = github.get('user')["id"]
           post_dict['name'] = name
           post_dict['post_date'] = post_date
           post_dict['pic'] = github.get('user')["avatar_url"] + '&s=200'
           post_dict['message'] = message
           post_dict['title'] = title
           post_dict['link'] = link
           post_dict['type_select'] = type_select
           post_dict['post_url'] = post_url

           red.hmset(post_num, post_dict)
           print post_num
           print red.hgetall(post_num)

           if type_select == 'Announcement':
               icon = 'fa-bullhorn'
           if type_select == 'Event':
               icon = 'fa-calendar-check-o'

           recent_posts = post_url+'-'+title

           red.lpush('recent_posts', recent_posts)
           if len(red.lrange('recent_posts', 0, -1)) > 10:
              red.rpop('recent_posts')

           es.indices.create(index=index_devhub, ignore=400)
           data = '{' + '"title": "' + title + '", "url": "' + post_url + \
                  '", "type": "' + type_select + '", "link": "' + link + \
                  '", "icon": "' + icon + '", "name": "' + name + \
                  '", "post_date": "' + post_date + '", "date": "' + \
                  date_time + '", "tags": "' + tags + '", "message": "' + message + '"}'

           print data
           res = es.index(index=index_devhub, doc_type=index_type, id=post_num,
                          body=data)

           print (res['created'])

           flash(post_url)
           return render_template('post.html')

    idd = g.user
    pic_url = github.get('user')["avatar_url"] + '&s=48'

    return render_template('post.html', pic_url=pic_url, idd=idd)


@app.route('/search/<string:tech>')
def search(tech):
    idd = None
    if g.user:
       idd = g.user
       pic_url = github.get('user')["avatar_url"] + '&s=48'
    else:
       pic_url = None

    return render_template('search.html', tech=tech, pic_url=pic_url, idd=idd)


@app.route('/delete/<string:number>')
def delete_post(number):

    if not g.user:
        error = 'Error: Authentication failed'
        return redirect(url_for('index', error=error))

    idd = github.get('user')["id"]
    user_id = red.hget(number, 'idd')

    if str(user_id) == str(idd):
        num_incr = number + '-incr'

        post_url = red.hget(number, 'post_url')
        title = red.hget(number, 'title')
        item = post_url+'-'+title
        recent_posts = red.lrange('recent_posts', 0, -1)

        if any(item in s for s in recent_posts):
            red.lrem('recent_posts', 1, item)

        red.delete(number)

        res = es.delete(index=index_devhub, doc_type=index_type, id=number)
        print res

        flash('Success:  Deleted Post')
        return redirect(url_for('index'))
    else:
        error = 'Error: Authentication failed'
        return redirect(url_for('index', error=error))


@github.access_token_getter
def token_getter():
    user = g.user
    if user is not None:
        return user.github_access_token


@app.route('/process')
def process():
    date_time = datetime.datetime.strftime(datetime.datetime.now(),
                                           '%Y-%m-%dT%H:%M:%S')
    post_date = datetime.datetime.strftime(datetime.datetime.now(),
                                           '%m/%d/%Y')
    langs = []
    git_login = github.get('user')["login"]
    repos_json = github.get('users/' + git_login + '/repos')

    for l in repos_json:
        if l["language"] != None:
            langs.append(l["language"])

    top_lang = 'Codes the most in ' + max(langs)
    second_lang = '& loves ' + max(langs, key=lambda x: x[1])

    es.indices.create(index=index_devhub, ignore=400)
    data = '{' + '"url": "' + github.get('user')["html_url"] + \
           '", "icon": "' + 'fa-user' + '", "title": "' + github.get('user')["name"] + \
           '", "post_date": "' + post_date + '", "email": "' + github.get('user')["email"] + \
           '", "top_lang": "' + top_lang + '", "second_lang": "' + second_lang + \
           '", "type": "user", "date": "' + date_time + '"}'

    print data
    res = es.index(index=index_devhub, doc_type=index_type, id=github.get('user')["id"],
                   body=data)

    print (res['created'])

    return redirect(url_for('index'))


@app.route('/github-callback')
@github.authorized_handler
def authorized(access_token):
    next_url = request.args.get('next') or url_for('process')
    if access_token is None:
        return redirect(next_url)

    user = User.query.filter_by(github_access_token=access_token).first()
    if user is None:
        user = User(access_token)
        db_session.add(user)
    user.github_access_token = access_token
    db_session.commit()

    session['user_id'] = user.id
    return redirect(next_url)


@app.route('/login')
def login():
    return github.authorize()
    #if session.get('user_id', None) is None:
    #    return github.authorize()
    #else:
    #    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


app.wsgi_app = ProxyFix(app.wsgi_app)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8080, debug=False)
