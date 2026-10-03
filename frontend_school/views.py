from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test

def is_school_admin_or_superuser(user):
    return user.is_authenticated and (user.role == 'school_admin' or user.is_superuser)

school_admin_required = user_passes_test(is_school_admin_or_superuser, login_url='login')
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Q
from django.utils.crypto import get_random_string
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import gettext as _
from django.utils import timezone
import json
import secrets
import string

from accounts.models import CustomUser
from accounts.utils import verify_dynamic_token
from books.models import Book, BookIssue, BookRequest, Category
from schools.models import School
from stats.models import ActionLog
from .models import News
from .forms import BookForm, StudentForm, TeacherForm, NewsForm

@login_required(login_url='login')
@school_admin_required
def dashboard(request):
    if request.user.role != 'school_admin' and not request.user.is_superuser:
        return redirect('frontend_user:library')
    school = request.user.school or School.objects.first()
    context = {}
    if school:
        recent_activities = BookIssue.objects.filter(book__school=school).order_by('-issued_at')[:5]
        stats = Book.objects.filter(school=school).aggregate(
            total_copies=Sum('total_count'),
            available_copies=Sum('available_count')
        )
        # Base news filter: current school's news
        news_filter = Q(school=school)
        if request.user.role == 'school_admin' or request.user.is_superuser:
            news_filter |= Q(school__isnull=True)
            
        context = {
            'student_count': CustomUser.objects.filter(school=school, role='student').count(),
            'book_count': Book.objects.filter(school=school).count(),
            'total_copies': stats['total_copies'] or 0,
            'available_copies': stats['available_copies'] or 0,
            'issued_count': BookIssue.objects.filter(book__school=school, is_returned=False).count(),
            'recent_activities': recent_activities,
            'news_count': News.objects.filter(news_filter, is_published=True).count(),
        }
    return render(request, 'school_panel/dashboard.html', context)

@login_required(login_url='login')
@school_admin_required
def students_list(request):
    school = request.user.school
    query = request.GET.get('q')
    students = CustomUser.objects.filter(school=school, role='student')
    
    if query:
        from django.db.models import Q
        students = students.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(grade__icontains=query)
        )
        
    students = students.order_by('last_name', 'first_name')
    
    from django.core.paginator import Paginator
    paginator = Paginator(students, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'school_panel/students.html', {'students': page_obj, 'page_obj': page_obj, 'query': query})

@login_required(login_url='login')
@school_admin_required
def teachers_list(request):
    school = request.user.school
    query = request.GET.get('q')
    teachers = CustomUser.objects.filter(school=school, role='teacher')
    
    if query:
        from django.db.models import Q
        teachers = teachers.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
        
    teachers = teachers.order_by('last_name', 'first_name')
    
    from django.core.paginator import Paginator
    paginator = Paginator(teachers, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'school_panel/teachers.html', {'teachers': page_obj, 'page_obj': page_obj, 'query': query})

@login_required(login_url='login')
@school_admin_required
def books_list(request):
    school = request.user.school
    query = request.GET.get('q')
    category_id = request.GET.get('category')
    no_cover = request.GET.get('no_cover')
    
    books = Book.objects.filter(school=school)
    
    if query:
        books = books.filter(title__icontains=query)
    
    if category_id:
        books = books.filter(category_id=category_id)
        
    if no_cover == '1':
        from django.db.models import Q
        books = books.filter(Q(cover='') | Q(cover__isnull=True))
        
    books = books.order_by('title')
    
    from books.models import Category
    categories = Category.objects.all().order_by('name')
    
    from django.core.paginator import Paginator
    paginator = Paginator(books, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'school_panel/books.html', {
        'books': page_obj, 
        'page_obj': page_obj,
        'categories': categories,
        'query': query,
        'selected_category': int(category_id) if category_id else None,
        'no_cover': no_cover == '1'
    })

@login_required(login_url='login')
@school_admin_required
def issued_books_list(request):
    school = request.user.school
    issues = BookIssue.objects.filter(book__school=school, is_returned=False).order_by('-issued_at')
    return render(request, 'school_panel/issued_books.html', {'issues': issues})

@login_required(login_url='login')
@school_admin_required
def history_list(request):
    school = request.user.school
    query = request.GET.get('q')
    history = BookIssue.objects.filter(book__school=school).order_by('-issued_at')
    
    if query:
        from django.db.models import Q
        history = history.filter(
            Q(book__title__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query)
        )
    
    from django.core.paginator import Paginator
    paginator = Paginator(history, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'school_panel/history.html', {'history': page_obj, 'page_obj': page_obj, 'query': query})

@login_required(login_url='login')
@school_admin_required
def news_list(request):
    school = request.user.school
    from django.db.models import Q
    # Base filter: only school's news
    query = Q(school=school)
    # Add global news only for admins
    if request.user.role == 'school_admin' or request.user.is_superuser:
        query |= Q(school__isnull=True)
        
    news = News.objects.filter(query, is_published=True).order_by('-created_at')
    return render(request, 'school_panel/news.html', {'news': news})

@login_required(login_url='login')
@school_admin_required
def qr_unified(request):
    return render(request, 'school_panel/qr_unified.html')

@csrf_exempt
def process_qr_unified(request):
    if not request.user.is_authenticated or request.user.role != 'school_admin':
        return JsonResponse({'status': 'error', 'message': 'Ruxsat etilmagan'})
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = data.get('token', '')
            
            if token.startswith('REQ_'):
                return process_qr(request)
            elif token.startswith('RET_'):
                return process_receive_qr(request)
            else:
                return JsonResponse({'status': 'error', 'message': _('Noma\'lum QR-kod turi. Iltimos, kitob berish yoki qaytarish kodini skanerlang.')})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'})



@csrf_exempt
def process_qr(request):
    if not request.user.is_authenticated or (request.user.role != 'school_admin' and not request.user.is_superuser):
        return JsonResponse({'status': 'error', 'message': 'Ruxsat etilmagan'})
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = data.get('token', '')
            
            from accounts.utils import verify_dynamic_token
            request_id = verify_dynamic_token(token, 'REQ')
            
            request_obj = None
            if request_id:
                request_obj = BookRequest.objects.filter(id=request_id, status='pending').first()
            if not request_obj:
                request_obj = BookRequest.objects.filter(qr_token=token, status='pending').first()
            
            if not request_obj:
                return JsonResponse({'status': 'error', 'message': _('Eski yoki noto\'g\'ri QR-kod. Bron topilmadi yoki allaqachon tasdiqlangan.')})
            
            # [CRITICAL CHECK] Ensure the student belongs to the librarian's school
            if request.user.school and request_obj.user.school != request.user.school and not request.user.is_superuser:
                return JsonResponse({'status': 'error', 'message': _('Xatolik: Ushbu o\'quvchi boshqa maktabga tegishli!')})
            
            # Check if book is available
            book = request_obj.book
            if book.available_count <= 0:
                return JsonResponse({'status': 'error', 'message': _('Kitob qolmagan')})
            
            # Process: update request and create issue
            request_obj.status = 'approved'
            request_obj.save()
            
            issue = BookIssue.objects.create(book=book, user=request_obj.user)
            
            book.available_count -= 1
            book.borrow_count += 1
            book.save()

            # Log action
            ActionLog.objects.create(
                user=request.user,
                action_type='ISSUE',
                message=_("{}ga '{}' kitobi berildi").format(request_obj.user.username, book.title)
            )
            
            student_name = request_obj.user.get_full_name().strip() or request_obj.user.username
            return JsonResponse({
                'status': 'success', 
                'message': _('Kitob muvaffaqiyatli berildi: {}').format(book.title),
                'student': student_name
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'})

@csrf_exempt
def process_receive_qr(request):
    if not request.user.is_authenticated or (request.user.role != 'school_admin' and not request.user.is_superuser):
        return JsonResponse({'status': 'error', 'message': 'Ruxsat etilmagan'})
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = data.get('token', '')
            
            from accounts.utils import verify_dynamic_token
            issue_id = verify_dynamic_token(token, 'RET')
            
            issue = None
            if issue_id:
                issue = BookIssue.objects.filter(id=issue_id, is_returned=False).first()
            if not issue:
                issue = BookIssue.objects.filter(qr_token=token, is_returned=False).first()
                
            if not issue:
                return JsonResponse({'status': 'error', 'message': _('Ushbu kitob uchun faol topshirish topilmadi yoki QR-kod eskirgan.')})
            
            # [CRITICAL CHECK] Ensure the student belongs to the librarian's school
            if request.user.school and issue.user.school != request.user.school and not request.user.is_superuser:
                return JsonResponse({'status': 'error', 'message': _('Xatolik: Ushbu o\'quvchi boshqa maktabga tegishli!')})
            
            book = issue.book
            user = issue.user
            
            issue.is_returned = True
            issue.returned_at = timezone.now()
            issue.save()
            
            book.available_count += 1
            book.save()
            
            # Find and complete the associated request if it exists
            request_obj = BookRequest.objects.filter(book=book, user=user, status='approved').first()
            if request_obj:
                request_obj.status = 'completed'
                request_obj.save()

            # Log action
            ActionLog.objects.create(
                user=request.user,
                action_type='RETURN',
                message=_("{}dan '{}' kitobi qabul qilindi").format(user.username, book.title)
            )
            
            student_name = user.get_full_name().strip() or user.username
            return JsonResponse({
                'status': 'success', 
                'message': _('Kitob muvaffaqiyatli qabul qilindi: {}').format(book.title),
                'student': student_name
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'})


@login_required(login_url='login')
@school_admin_required
def book_add(request):
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            book.school = request.user.school
            book.save()
            return redirect('frontend_school:books_list')
    else:
        form = BookForm()
    return render(request, 'school_panel/book_form.html', {'form': form, 'title': _('Yangi kitob qo\'shish')})

@login_required(login_url='login')
@school_admin_required
def book_edit(request, pk):
    book = get_object_or_404(Book, pk=pk, school=request.user.school)
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            return redirect('frontend_school:books_list')
    else:
        form = BookForm(instance=book)
    return render(request, 'school_panel/book_form.html', {'form': form, 'title': _('Kitobni tahrirlash')})

@login_required(login_url='login')
@school_admin_required
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk, school=request.user.school)
    if request.method == 'POST':
        book.delete()
        return redirect('frontend_school:books_list')
    return render(request, 'school_panel/confirm_delete.html', {'object': book, 'type': _('kitobni')})

@login_required(login_url='login')
@school_admin_required
def student_add(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.school = request.user.school
            student.role = 'student'
            
            # 1. Save initially to get ID
            student.username = f"temp_{secrets.token_hex(4)}"
            student.save()
            
            # 2. Generate Smart Login: {district}_{school}_{id}
            def clean_name(name):
                return "".join(c for c in name.lower() if c.isalnum() or c == '_').strip('_')
            
            district_part = clean_name(student.school.district.name if student.school and student.school.district else "no")
            school_part = clean_name(student.school.name if student.school else "school")
            
            username = f"{district_part}_{school_part}_{student.id}"
            student.username = username
            
            # 3. Generate Random Password (12 chars)
            password = form.cleaned_data.get('password')
            if not password:
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for i in range(12))
            
            student.set_password(password)
            student.raw_password = password # Visible to admin
            student.save()
            
            messages.success(request, _("Yangi o'quvchi qo'shildi! Login: {}, Parol: {}").format(username, password))
            return redirect('frontend_school:students_list')
    else:
        form = StudentForm()
    return render(request, 'school_panel/student_form.html', {'form': form, 'title': _('Yangi o\'quvchi qo\'shish')})

@login_required(login_url='login')
@school_admin_required
def student_edit(request, pk):
    student = get_object_or_404(CustomUser, pk=pk, school=request.user.school, role='student')
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            return redirect('frontend_school:students_list')
    else:
        form = StudentForm(instance=student)
    return render(request, 'school_panel/student_form.html', {'form': form, 'title': _('O\'quvchi ma\'lumotlarini tahrirlash')})

@login_required(login_url='login')
@school_admin_required
def student_delete(request, pk):
    student = get_object_or_404(CustomUser, pk=pk, school=request.user.school, role='student')
    if request.method == 'POST':
        student.delete()
        return redirect('frontend_school:students_list')
    return render(request, 'school_panel/confirm_delete.html', {'object': student, 'type': _('o\'quvchini')})

@login_required(login_url='login')
@school_admin_required
def teacher_add(request):
    if request.method == 'POST':
        form = TeacherForm(request.POST)
        if form.is_valid():
            teacher = form.save(commit=False)
            teacher.school = request.user.school
            teacher.role = 'teacher'
            
            # 1. Save initially to get ID
            teacher.username = f"temp_t_{secrets.token_hex(4)}"
            teacher.save()
            
            # 2. Generate Smart Login: {district}_{school}_{id}
            def clean_name(name):
                return "".join(c for c in name.lower() if c.isalnum() or c == '_').strip('_')
            
            district_part = clean_name(teacher.school.district.name if teacher.school and teacher.school.district else "no")
            school_part = clean_name(teacher.school.name if teacher.school else "school")
            
            username = f"{district_part}_{school_part}_{teacher.id}"
            teacher.username = username
            
            # 3. Generate Random Password (12 chars)
            password = form.cleaned_data.get('password')
            if not password:
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for i in range(12))
            
            teacher.set_password(password)
            teacher.raw_password = password
            teacher.save()
            
            messages.success(request, _(f"Yangi o'qituvchi qo'shildi! Login: {username}, Parol: {password}"))
            return redirect('frontend_school:teachers_list')
    else:
        form = TeacherForm()
    return render(request, 'school_panel/teacher_form.html', {'form': form, 'title': _('Yangi o\'qituvchi qo\'shish')})

@login_required(login_url='login')
@school_admin_required
def teacher_edit(request, pk):
    teacher = get_object_or_404(CustomUser, pk=pk, school=request.user.school, role='teacher')
    if request.method == 'POST':
        form = TeacherForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            return redirect('frontend_school:teachers_list')
    else:
        form = TeacherForm(instance=teacher)
    return render(request, 'school_panel/teacher_form.html', {'form': form, 'title': _('O\'qituvchi ma\'lumotlarini tahrirlash')})

@login_required(login_url='login')
@school_admin_required
def teacher_delete(request, pk):
    teacher = get_object_or_404(CustomUser, pk=pk, school=request.user.school, role='teacher')
    if request.method == 'POST':
        teacher.delete()
        return redirect('frontend_school:teachers_list')
    return render(request, 'school_panel/confirm_delete.html', {'object': teacher, 'type': _('o\'qituvchini')})

@login_required(login_url='login')
@school_admin_required
def news_add(request):
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES)
        if form.is_valid():
            news = form.save(commit=False)
            news.school = request.user.school
            news.save()
            return redirect('frontend_school:news_list')
    else:
        form = NewsForm()
    return render(request, 'school_panel/news_form.html', {'form': form, 'title': _('Yangi yangilik qo\'shish')})

@login_required(login_url='login')
@school_admin_required
def news_edit(request, pk):
    news = get_object_or_404(News, pk=pk, school=request.user.school)
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES, instance=news)
        if form.is_valid():
            form.save()
            return redirect('frontend_school:news_list')
    else:
        form = NewsForm(instance=news)
    return render(request, 'school_panel/news_form.html', {'form': form, 'title': _('Yangilikni tahrirlash')})

@login_required(login_url='login')
@school_admin_required
def news_delete(request, pk):
    news = get_object_or_404(News, pk=pk, school=request.user.school)
    if request.method == 'POST':
        news.delete()
        return redirect('frontend_school:news_list')
    return render(request, 'school_panel/confirm_delete.html', {'object': news, 'type': _('yangilikni')})

@login_required(login_url='login')
@school_admin_required
def profile(request):
    if request.user.role != 'school_admin':
        return redirect('frontend_user:library')
    return render(request, 'school_panel/profile.html')

@login_required(login_url='login')
@school_admin_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.raw_password = form.cleaned_data.get('new_password1')
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, _('Parolingiz muvaffaqiyatli o\'zgartirildi!'))
            return redirect('frontend_school:profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'school_panel/password_change.html', {'form': form})
