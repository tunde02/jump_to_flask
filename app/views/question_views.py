from datetime import datetime
from flask import Blueprint, render_template, request, url_for, g, flash
from werkzeug.utils import redirect
from app import db
from app.models import Question, Answer, User
from app.forms import QuestionForm, AnswerForm
from app.views.auth_views import login_required


bp = Blueprint('question', __name__, url_prefix='/question')


@bp.route('/list')
def _list():
    page = request.args.get('page', type=int, default=1)
    kw = request.args.get('kw', type=str, default='')
    question_list = Question.query.order_by(Question.create_date.desc())

    if kw:
        search = '%%{}%%'.format(kw)
        subquery = db.session.query(Answer.question_id, Answer.content, User.username) \
            .join(User, Answer.user_id == User.id).subquery()
        question_list = question_list \
            .join(User) \
            .outerjoin(subquery, subquery.c.question_id == Question.id) \
            .filter(Question.subject.ilike(search) |   # 질문 제목
                    Question.content.ilike(search) |   # 질문 내용
                    User.username.ilike(search) |      # 질문 작성자
                    subquery.c.content.ilike(search) | # 답변 내용
                    subquery.c.username.ilike(search)  # 답변 작성자
                    ) \
            .distinct()

    question_list = question_list.paginate(page, per_page=10)

    return render_template('question/question_list.html', question_list=question_list, page=page, kw=kw)


@bp.route('/detail/<int:question_id>')
def detail(question_id):
    form = AnswerForm()
    question = Question.query.get_or_404(question_id)

    return render_template('question/question_detail.html', question=question, form=form)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = QuestionForm()
    if request.method == 'POST' and form.validate_on_submit():
        question = Question(subject=form.subject.data, content=form.content.data, create_date=datetime.now(), user=g.user)

        db.session.add(question)
        db.session.commit()

        return redirect(url_for('main.index'))

    return render_template('question/question_form.html', form=form)


@bp.route('/modify/<int:question_id>', methods=['GET', 'POST'])
@login_required
def modify(question_id):
    question = Question.query.get_or_404(question_id)

    if g.user != question.user:
        flash('수정 권한이 없습니다.')

        return redirect(url_for('question.detail', question_id=question_id))

    if request.method == 'POST': # POST
        form = QuestionForm()

        if form.validate_on_submit():
            form.populate_obj(question)
            question.modify_date = datetime.now()

            db.session.commit()

            return redirect(url_for('question.detail', question_id=question_id))
    else: # GET
        form = QuestionForm(obj=question)

    return render_template('question/question_form.html', form=form)


@bp.route('/delete/<int:question_id>')
@login_required
def delete(question_id):
    question = Question.query.get_or_404(question_id)

    if g.user != question.user:
        flash("삭제 권한이 없습니다.")

        return redirect(url_for('question.detail', question_id=question_id))

    db.session.delete(question)
    db.session.commit()

    return redirect(url_for('question._list'))


@bp.route('/vote/<int:question_id>')
@login_required
def vote(question_id):
    question = Question.query.get_or_404(question_id)

    if g.user == question.user:
        flash("본인이 작성한 글은 추천할 수 없습니다.")
    else:
        question.voter.append(g.user) # 동일한 사용자가 여러 번 추천해도 내부적으로 중복되지 않게끔 처리됨

        db.session.commit()

    return redirect(url_for('question.detail', question_id=question_id))
