```python
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.db.models import Sum
import logging

from .models import (
    Course,
    Enrollment,
    Question,
    Choice,
    Submission,
)

logger = logging.getLogger(__name__)


def registration_request(request):
    context = {}

    if request.method == 'GET':
        return render(
            request,
            'onlinecourse/user_registration_bootstrap.html',
            context
        )

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']

        if User.objects.filter(username=username).exists():
            context['message'] = "User already exists."
            return render(
                request,
                'onlinecourse/user_registration_bootstrap.html',
                context
            )

        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password
        )
        login(request, user)
        return redirect("onlinecourse:index")


def login_request(request):
    context = {}

    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')

        context['message'] = "Invalid username or password."

    return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    if not user.is_authenticated:
        return False

    return Enrollment.objects.filter(user=user, course=course).exists()


class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]

        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)

        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    if user.is_authenticated and not check_if_enrolled(user, course):
        Enrollment.objects.create(
            user=user,
            course=course,
            mode='honor'
        )
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(
        reverse('onlinecourse:course_details', args=(course.id,))
    )


def extract_answers(request):
    submitted_answers = []

    for key in request.POST:
        if key.startswith('choice'):
            try:
                submitted_answers.append(int(request.POST[key]))
            except (ValueError, TypeError):
                continue

    return submitted_answers


def submit(request, course_id):
    if request.method != 'POST':
        return redirect('onlinecourse:course_details', pk=course_id)

    course = get_object_or_404(Course, pk=course_id)

    if not request.user.is_authenticated:
        return redirect('onlinecourse:login')

    enrollment = get_object_or_404(
        Enrollment,
        user=request.user,
        course=course
    )

    submission = Submission.objects.create(enrollment=enrollment)

    for choice_id in extract_answers(request):
        choice = get_object_or_404(
            Choice,
            pk=choice_id,
            question__course=course
        )
        submission.choices.add(choice)

    return redirect(
        'onlinecourse:show_exam_result',
        course_id=course.id,
        submission_id=submission.id
    )


def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)

    submission = get_object_or_404(
        Submission,
        pk=submission_id,
        enrollment__course=course
    )

    questions = Question.objects.filter(course=course)
    selected_choices = submission.choices.all()

    total_score = 0
    max_score = sum(question.grade for question in questions)
    question_results = []

    for question in questions:
        choices = question.choice_set.all()
        selected_for_question = selected_choices.filter(
            question=question
        )

        is_correct = (
            selected_for_question.filter(is_correct=True).exists()
        )

        if is_correct:
            total_score += question.grade

        question_results.append({
            'question': question,
            'choices': choices,
            'selected_choices': selected_for_question,
            'is_correct': is_correct,
        })

    passed = max_score > 0 and total_score >= max_score * 0.5

    context = {
        'course': course,
        'submission': submission,
        'question_results': question_results,
        'total_score': total_score,
        'max_score': max_score,
        'passed': passed,
    }

    return render(
        request,
        'onlinecourse/exam_result_bootstrap.html',
        context
    )
```
