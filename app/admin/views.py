# coding:utf8
from . import admin
from flask import render_template, redirect, url_for, flash, session, request
from app.admin.forms import LoginForm, TagForm, MovieForm, PreviewForm
from app.models import Admin, Tag, Movie, Preview
from functools import wraps
from app import db, app
from werkzeug.utils import secure_filename
import os
import uuid
import datetime


# 登录装饰器
def admin_login_req(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin" not in session:
            return redirect(url_for("admin.login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


# 修改文件名称
def change_filename(filename):
    fileinfo = os.path.splitext(filename)
    filename = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4().hex) + fileinfo[-1]
    return filename


# 后台首页
@admin.route("/")
@admin_login_req
def index():
    return render_template('admin/index.html')


# 登录页面
@admin.route("/login/", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        data = form.data
        admin = Admin.query.filter_by(name=data['account']).first()
        if not admin.check_pwd(data['pwd']):
            flash('密码错误！')
            return redirect(url_for('admin.login'))
        session['admin'] = data['account']
        return redirect(request.args.get("next") or url_for("admin.index"))
    return render_template('admin/login.html', form=form)


# 退出登录
@admin.route("/logout/")
@admin_login_req
def logout():
    session.pop("admin", None)
    return redirect(url_for('admin.login'))


# 修改密码页面
@admin.route("/pwd/")
@admin_login_req
def pwd():
    return render_template('admin/pwd.html')


# 添加标签页面
@admin.route("/tag/add/", methods=["GET", "POST"])
@admin_login_req
def tag_add():
    form = TagForm()
    if form.validate_on_submit():
        data = form.data
        tag = Tag.query.filter_by(name=data['name']).count()
        if tag == 1:
            flash("名称已经存在", "err")
            return redirect(url_for('admin.tag_add'))
        tag = Tag(
            name=data['name']
        )
        db.session.add(tag)
        db.session.commit()
        flash('添加成功', 'ok')
        return redirect(url_for('admin.tag_add'))
    return render_template('admin/tag_add.html', form=form)


# 标签列表页面
@admin.route("/tag/list/<int:page>/", methods=['GET'])
@admin_login_req
def tag_list(page=None):
    if page == None:
        page = 1
    page_data = Tag.query.order_by(
        Tag.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/tag_list.html', page_data=page_data)


# 标签删除
@admin.route("/tag/del/<int:id>/", methods=['GET'])
@admin_login_req
def tag_del(id=None):
    tag = Tag.query.filter_by(id=id).first_or_404()
    db.session.delete(tag)
    db.session.commit()
    flash('删除标签成功！', 'ok')
    return redirect(url_for('admin.tag_list', page=1))


# 标签编辑
@admin.route("/tag/edit/<int:id>/", methods=['GET', 'POST'])
@admin_login_req
def tag_edit(id=None):
    form = TagForm()
    tag = Tag.query.get_or_404(id)
    if form.validate_on_submit():
        data = form.data
        tag_count = Tag.query.filter_by(name=data['name']).count()
        if tag.name != data['name'] and tag_count == 1:
            flash("名称已经存在", "err")
            return redirect(url_for('admin.tag_add', id=id))
        tag.name = data['name']
        db.session.add(tag)
        db.session.commit()
        flash('修改标签成功', 'ok')
        return redirect(url_for('admin.tag_edit', id=id))
    return render_template('admin/tag_edit.html', form=form, tag=tag)


# 添加电影页面
@admin.route("/movie/add/", methods=['GET', 'POST'])
@admin_login_req
def movie_add():
    form = MovieForm()
    if form.validate_on_submit():
        data = form.data
        file_url = secure_filename(form.url.data.filename)
        file_logo = secure_filename(form.logo.data.filename)
        if not os.path.exists((app.config['UP_DIR'])):
            os.makedirs(app.config['UP_DIR'])
            os.chmod(app.config['UP_DIR'], "rw")
        url = change_filename(file_url)
        logo = change_filename(file_logo)
        form.url.data.save(app.config['UP_DIR'] + url)
        form.logo.data.save(app.config['UP_DIR'] + logo)
        movie = Movie(
            title=data["title"],
            url=url,
            info=data["info"],
            logo=logo,
            star=int(data["star"]),
            playnum=0,
            commentnum=0,
            tag_id=int(data["tag_id"]),
            area=data["area"],
            release_time=data["release_time"],
            length=data["length"],
        )
        db.session.add(movie)
        db.session.commit()
        flash("添加电影成功", "ok")
        return redirect(url_for('admin.movie_add'))
    return render_template('admin/movie_add.html', form=form)


# 电影列表页面
@admin.route("/movie/list/<int:page>", methods=["GET"])
@admin_login_req
def movie_list(page=None):
    if page == None:
        page = 1
    page_data = Movie.query.join(Tag).filter(
        Tag.id == Movie.tag_id
    ).order_by(
        Movie.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/movie_list.html', page_data=page_data)


# 电影删除
@admin.route("/movie/del/<int:id>", methods=["GET"])
@admin_login_req
def movie_del(id=None):
    movie = Movie.query.get_or_404(int(id))
    db.session.delete(movie)
    db.session.commit()
    flash("删除电影成功", "ok")
    return redirect(url_for('admin.movie_list', page=1))


# 电影编辑
@admin.route("/movie/edit/<int:id>/", methods=['GET', 'POST'])
@admin_login_req
def movie_edit(id=None):
    form = MovieForm()
    form.url.validators = []
    form.logo.validators = []
    movie = Movie.query.get_or_404(int(id))
    if request.method == 'GET':
        form.info.data = movie.info
        form.tag_id.data = movie.tag_id
        form.star.data = movie.star
    if form.validate_on_submit():
        data = form.data
        # 判断片名是否存在
        movie_count = Movie.query.filter_by(title=data['title']).count()
        if movie_count == 1 and movie.title == data['title']:
            flash('片名已经存在', 'err')
            return redirect(url_for('admin.movie_edit', id=int(id)))
        # 判断文件是否存在
        if not os.path.exists((app.config['UP_DIR'])):
            os.makedirs(app.config['UP_DIR'])
            os.chmod(app.config['UP_DIR'], "rw")
        # 判断是否含有属性filename，及判断是否重新上传了视频
        if hasattr(form.url.data, 'filename'):
            file_url = secure_filename(form.url.data.filename)
            movie.url = change_filename(file_url)
            form.url.data.save(app.config['UP_DIR'] + movie.url)

        # 判断是否含有属性filename，及判断是否重新上传了封面
        if hasattr(form.logo.data, 'filename'):
            file_logo = secure_filename(form.logo.data.filename)
            movie.logo = change_filename(file_logo)
            form.logo.data.save(app.config['UP_DIR'] + movie.logo)

        movie.title = data['title']
        movie.info = data['info']
        movie.star = data['star']
        movie.tag_id = data['tag_id']
        movie.area = data['area']
        movie.length = data['length']
        movie.release_time = data['release_time']
        db.session.add(movie)
        db.session.commit()
        flash('修改电影成功', 'ok')
        return redirect(url_for('admin.movie_edit', id=int(id)))
    return render_template('admin/movie_edit.html', form=form, movie=movie)


# 添加上映电影页面
@admin.route("/preview/add/", methods=['GET', 'POST'])
@admin_login_req
def preview_add():
    form = PreviewForm()
    if form.validate_on_submit():
        data = form.data
        file_logo = secure_filename(form.logo.data.filename)
        if not os.path.exists((app.config['UP_DIR'])):
            os.makedirs(app.config['UP_DIR'])
            os.chmod(app.config['UP_DIR'], "rw")
        logo = change_filename(file_logo)
        form.logo.data.save(app.config['UP_DIR'] + logo)
        preview = Preview(
            title=data['title'],
            logo=logo
        )
        db.session.add(preview)
        db.session.commit()
        flash("添加预告成功", "ok")
        return redirect(url_for('admin.preview_add'))
    return render_template('admin/preview_add.html', form=form)


# 上映列表页面
@admin.route("/preview/list/<int:page>", methods=['GET'])
@admin_login_req
def preview_list(page=None):
    if page == None:
        page = 1
    page_data = Preview.query.order_by(
        Preview.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/preview_list.html', page_data=page_data)


# 删除上映
@admin.route("/preview/del/<int:id>", methods=['GET'])
@admin_login_req
def preview_del(id=None):
    preview = Preview.query.filter_by(id=id).first_or_404()
    db.session.delete(preview)
    db.session.commit()
    flash('删除上映成功！', 'ok')
    return redirect(url_for('admin.preview_list', page=1))


# 编辑上映
@admin.route("/preview/edit/<int:id>", methods=['GET', 'POST'])
@admin_login_req
def preview_edit(id=None):
    form = PreviewForm()
    form.logo.validators = []
    preview = Preview.query.get_or_404(int(id))
    if request.method == 'GET':
        form.title.data = preview.title
    if form.validate_on_submit():
        data = form.data
        if hasattr(form.logo.data, 'filename'):
            file_logo = secure_filename(form.logo.data.filename)
            preview.logo = change_filename(file_logo)
            form.logo.data.save(app.config['UP_DIR'] + preview.logo)
        preview.title = data['title']
        db.session.add(preview)
        db.session.commit()
        flash("修改预告成功", "ok")
        return redirect(url_for('admin.preview_edit', id=id))
    return render_template('admin/preview_edit.html', form=form, preview=preview)


# 会员列表页面
@admin.route("/user/list/")
@admin_login_req
def user_list():
    return render_template('admin/user_list.html')


# 会员详情页面
@admin.route("/user/view/")
@admin_login_req
def user_view():
    return render_template('admin/user_view.html')


# 评论列表页面
@admin.route("/comment/list/")
@admin_login_req
def comment_list():
    return render_template('admin/comment_list.html')


# 电影收藏列表页面
@admin.route("/moviecol/list/")
@admin_login_req
def moviecol_list():
    return render_template('admin/moviecol_list.html')


# 操作日志列表页面
@admin.route("/oplog/list/")
@admin_login_req
def oplog_list():
    return render_template('admin/oplog_list.html')


# 管理员登录日志列表页面
@admin.route("/adminloginlog/list/")
@admin_login_req
def adminloginlog_list():
    return render_template('admin/adminloginlog_list.html')


# 会员登录日志列表页面
@admin.route("/userloginlog/list/")
@admin_login_req
def userloginlog_list():
    return render_template('admin/userloginlog_list.html')


# 角色添加页面
@admin.route("/role/add/")
@admin_login_req
def role_add():
    return render_template('admin/role_add.html')


# 角色列表页面
@admin.route("/role/list/")
@admin_login_req
def role_list():
    return render_template('admin/role_list.html')


# 添加权限页面
@admin.route("/auth/add/")
@admin_login_req
def auth_add():
    return render_template('admin/auth_add.html')


# 权限列表页面
@admin.route("/auth/list/")
@admin_login_req
def auth_list():
    return render_template('admin/auth_list.html')


# 添加管理员页面
@admin.route("/admin/add/")
@admin_login_req
def admin_add():
    return render_template('admin/admin_add.html')


# 管理员列表页面
@admin.route("/admin/list/")
@admin_login_req
def admin_list():
    return render_template('admin/admin_list.html')
