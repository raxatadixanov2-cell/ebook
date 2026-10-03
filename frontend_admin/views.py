from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

superuser_required = user_passes_test(lambda u: u.is_superuser, login_url='login')

from frontend_school.models import News
from frontend_school.forms import NewsForm
from schools.models import School, Institution, District
from accounts.models import CustomUser
from books.models import Book, BookIssue
from django.utils.translation import gettext as _
import secrets
import string

@login_required(login_url='login')
@superuser_required
def dashboard(request):
    from stats.models import ActionLog
    from django.db.models import Exists, OuterRef
    from accounts.models import CustomUser
    
    active_schools_query = School.objects.annotate(
        has_admin=Exists(CustomUser.objects.filter(school=OuterRef('pk'), role='school_admin'))
    ).filter(has_admin=True)

    context = {
        'school_count': active_schools_query.count(),
        'user_count': CustomUser.objects.count(),
        'total_books': Book.objects.count(),
        'active_loans': BookIssue.objects.filter(is_returned=False).count(),
        'schools': active_schools_query.order_by('-id')[:5],
        'institutions_count': Institution.objects.count(),
        'recent_logs': ActionLog.objects.all().order_by('-created_at')[:10],
    }
    return render(request, 'admin_panel/dashboard.html', context)

@login_required(login_url='login')
@superuser_required
def schools_list(request):
    from django.db.models import Count, Q, Exists, OuterRef
    district_id = request.GET.get('district')
    
    # Only show schools that have an admin (fully configured)
    from accounts.models import CustomUser
    schools = School.objects.annotate(
        has_admin=Exists(CustomUser.objects.filter(school=OuterRef('pk'), role='school_admin')),
        student_count=Count('customuser', filter=Q(customuser__role='student')),
        book_count=Count('book', distinct=True),
        category_count=Count('book__category', distinct=True)
    ).filter(has_admin=True)
    
    if district_id:
        schools = schools.filter(district_id=district_id)
        
    schools = schools.order_by('-id')
    districts = District.objects.annotate(school_count=Count('schools', filter=Q(schools__customuser__role='school_admin'))).order_by('name')
    
    return render(request, 'admin_panel/schools.html', {
        'schools': schools,
        'districts': districts,
        'current_district': district_id
    })

from django.http import JsonResponse

@login_required(login_url='login')
@superuser_required
def check_username(request):
    username = request.GET.get('username', '').strip()
    if not username:
        return JsonResponse({'available': False, 'error': _('Login kiriting')})
    
    exists = CustomUser.objects.filter(username=username).exists()
    return JsonResponse({'available': not exists})

@login_required(login_url='login')
@superuser_required
def muassasalar_list(request):
    institutions = Institution.objects.all().order_by('-id')
    return render(request, 'admin_panel/muassasalar.html', {'institutions': institutions})

@login_required(login_url='login')
@superuser_required
def districts_list(request):
    from django.db.models import Count, Q
    districts = District.objects.annotate(
        school_count=Count('schools', filter=Q(schools__customuser__role='school_admin'))
    ).order_by('name')
    return render(request, 'admin_panel/districts.html', {'districts': districts})

@login_required(login_url='login')
@superuser_required
def statistics(request):
    from django.db.models import Count, Q
    from django.utils import timezone
    import datetime
    from books.models import Category, Book, BookIssue
    
    # Category stats
    category_stats = Category.objects.annotate(count=Count('book')).values('name', 'count')
    
    # Usage dynamics (last 7 days)
    today = timezone.now().date()
    days = []
    issue_counts = []
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        days.append(day.strftime('%d.%m'))
        count = BookIssue.objects.filter(issued_at__date=day).count()
        issue_counts.append(count)
        
    # Top schools
    from django.db.models import Count as DBCount
    top_schools = School.objects.annotate(
        reader_count=DBCount('customuser', filter=Q(customuser__role='student'))
    ).order_by('-reader_count')[:5]

    context = {
        'category_labels': [item['name'] for item in category_stats],
        'category_data': [item['count'] for item in category_stats],
        'usage_labels': days,
        'usage_data': issue_counts,
        'top_schools': top_schools,
    }
    return render(request, 'admin_panel/statistics.html', context)

@login_required(login_url='login')
@superuser_required
def system_logs(request):
    from stats.models import ActionLog
    logs = ActionLog.objects.all().order_by('-created_at')[:20]
    return render(request, 'admin_panel/logs.html', {'logs': logs})

@login_required(login_url='login')
@superuser_required
def all_users_list(request):
    users = CustomUser.objects.all().select_related('school').order_by('-date_joined')
    
    from django.core.paginator import Paginator
    paginator = Paginator(users, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'admin_panel/all_users.html', {'users': page_obj, 'page_obj': page_obj})

@login_required(login_url='login')
@superuser_required
def all_books_list(request):
    books = Book.objects.all().select_related('school', 'category').order_by('-id')
    
    from django.core.paginator import Paginator
    paginator = Paginator(books, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'admin_panel/all_books.html', {'books': page_obj, 'page_obj': page_obj})

@login_required(login_url='login')
@superuser_required
def all_active_loans_list(request):
    active_loans = BookIssue.objects.filter(is_returned=False).select_related('book__school', 'user').order_by('-issued_at')
    
    from django.core.paginator import Paginator
    paginator = Paginator(active_loans, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'admin_panel/all_active_loans.html', {'active_loans': page_obj, 'page_obj': page_obj})

@login_required(login_url='login')
@superuser_required
def school_detail(request, pk):
    school = get_object_or_404(School, pk=pk)
    context = {
        'school': school,
        'student_count': CustomUser.objects.filter(school=school, role='student').count(),
        'book_count': Book.objects.filter(school=school).count(),
        'issued_count': BookIssue.objects.filter(book__school=school, is_returned=False).count(),
        'school_admin': CustomUser.objects.filter(school=school, role='school_admin').first(),
        'students': CustomUser.objects.filter(school=school, role='student').order_by('-date_joined')[:20],
        'books': Book.objects.filter(school=school).order_by('-id')[:20],
    }
    return render(request, 'admin_panel/school_detail.html', context)

from .forms import SchoolForm, InstitutionForm, UnifiedSchoolForm

@login_required(login_url='login')
@superuser_required
def muassasa_add(request):
    if request.method == 'POST':
        form = InstitutionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('frontend_admin:muassasalar_list')
    else:
        form = InstitutionForm()
    return render(request, 'admin_panel/muassasa_form.html', {'form': form, 'title': _('Yangi muassasa qo\'shish')})

@login_required(login_url='login')
@superuser_required
def muassasa_edit(request, pk):
    inst = get_object_or_404(Institution, pk=pk)
    if request.method == 'POST':
        form = InstitutionForm(request.POST, instance=inst)
        if form.is_valid():
            form.save()
            return redirect('frontend_admin:muassasalar_list')
    else:
        form = InstitutionForm(instance=inst)
    return render(request, 'admin_panel/muassasa_form.html', {'form': form, 'title': _('Muassasa ma\'lumotlarini tahrirlash')})

@login_required(login_url='login')
@superuser_required
def muassasa_delete(request, pk):
    inst = get_object_or_404(Institution, pk=pk)
    if request.method == 'POST':
        inst.delete()
        return redirect('frontend_admin:muassasalar_list')
    return render(request, 'admin_panel/confirm_delete.html', {'object': inst, 'type': _('muassasani')})

from .forms import DistrictForm, SchoolFormSet

@login_required(login_url='login')
@superuser_required
def district_add(request):
    if request.method == 'POST':
        form = DistrictForm(request.POST)
        if form.is_valid():
            district = form.save()
            
            # Bulk Create Schools
            bulk_count = form.cleaned_data.get('bulk_schools_count')
            if bulk_count:
                existing_count = district.schools.count()
                new_schools = []
                for i in range(1, bulk_count + 1):
                    new_schools.append(School(
                        district=district,
                        name=f"{district.name} {existing_count + i}-sonli maktab",
                        address=f"{district.name} tumani",
                        contact="Aloqa kiritilmagan"
                    ))
                School.objects.bulk_create(new_schools)
                
            return redirect('frontend_admin:districts_list')
    else:
        form = DistrictForm()
    return render(request, 'admin_panel/district_form.html', {'form': form, 'title': _('Yangi tuman qo\'shish')})

@login_required(login_url='login')
@superuser_required
def district_edit(request, pk):
    district = get_object_or_404(District, pk=pk)
    if request.method == 'POST':
        form = DistrictForm(request.POST, instance=district)
        if form.is_valid():
            form.save()
            
            # Bulk Create Schools
            bulk_count = form.cleaned_data.get('bulk_schools_count')
            if bulk_count:
                existing_count = district.schools.count()
                new_schools = []
                for i in range(1, bulk_count + 1):
                    new_schools.append(School(
                        district=district,
                        name=f"{district.name} {existing_count + i}-sonli maktab",
                        address=f"{district.name} tumani",
                        contact="Aloqa kiritilmagan"
                    ))
                School.objects.bulk_create(new_schools)
                
            return redirect('frontend_admin:districts_list')
    else:
        form = DistrictForm(instance=district)
    return render(request, 'admin_panel/district_form.html', {'form': form, 'title': _('Tuman ma\'lumotlarini tahrirlash')})

@login_required(login_url='login')
@superuser_required
def district_delete(request, pk):
    district = get_object_or_404(District, pk=pk)
    if request.method == 'POST':
        district.delete()
        return redirect('frontend_admin:districts_list')
    return render(request, 'admin_panel/confirm_delete.html', {'object': district, 'type': _('tumanni')})

@login_required(login_url='login')
@superuser_required
def school_add(request):
    if request.method == 'POST':
        school_id = request.POST.get('existing_school_id')
        school_name = request.POST.get('name')
        district_id = request.POST.get('district')
        
        instance = None
        if school_id and school_id.isdigit():
            instance = School.objects.filter(pk=school_id).first()
        
        # Fallback: if no ID but name and district match an existing school, use that instance
        if not instance and school_name and district_id:
            instance = School.objects.filter(name=school_name, district_id=district_id).first()
        
        form = UnifiedSchoolForm(request.POST, instance=instance)
        if form.is_valid():
            school = form.save(commit=False)
            
            # If it's an existing school, check if it already has an admin
            if instance and CustomUser.objects.filter(school=instance, role='school_admin').exists():
                messages.error(request, f"'{instance.name}' maktabi uchun allaqachon admin biriktirilgan.")

                return redirect('frontend_admin:school_add')

            school.save()
            
            # 2. Create Admin User
            admin_username = form.cleaned_data.get('admin_username')
            admin_password = form.cleaned_data.get('admin_password')

            if admin_username and admin_password:
                admin_user = CustomUser.objects.create_user(
                    username=admin_username,
                    password=admin_password,
                    role='school_admin',
                    school=school,
                    first_name='Admin',
                    last_name=school.name
                )
                admin_user.raw_password = admin_password
                admin_user.save()
                
                # Log action
                from stats.models import ActionLog
                ActionLog.objects.create(
                    user=request.user,
                    action_type='CREATE',
                    message=_("Yangi maktab ({}) va uning admini ({}) yaratildi.").format(school.name, admin_user.username)
                )
                messages.success(request, _("Maktab va admin yaratildi! Login: {}").format(admin_user.username))
            else:
                messages.success(request, _("Maktab yaratildi (admin biriktirilmadi)."))
            
            return redirect('frontend_admin:schools_list')

    else:
        form = UnifiedSchoolForm()
    # Fetch Districts and Schools for the selection UI
    from django.db.models import Prefetch
    districts = District.objects.prefetch_related(
        Prefetch('schools', queryset=School.objects.all().order_by('name'))
    ).order_by('name')

    # Pass which schools already have admins
    schools_with_admins = CustomUser.objects.filter(role='school_admin').values_list('school_id', flat=True)

    return render(request, 'admin_panel/school_form.html', {
        'form': form, 
        'title': _('Yangi maktab qo\'shish'),
        'districts': districts,
        'schools_with_admins': list(schools_with_admins)
    })

@login_required(login_url='login')
@superuser_required
def school_edit(request, pk):
    school = get_object_or_404(School, pk=pk)
    admin = CustomUser.objects.filter(school=school, role='school_admin').first()
    
    if request.method == 'POST':
        form = UnifiedSchoolForm(request.POST, instance=school, current_admin_id=admin.pk if admin else None)
        if form.is_valid():
            school = form.save()
            
            # Logic for updating or creating admin details
            if admin:
                admin_username = form.cleaned_data.get('admin_username')
                admin_password = form.cleaned_data.get('admin_password')
                
                updated = False
                if admin_username and admin.username != admin_username:
                    admin.username = admin_username
                    updated = True
                
                # Check if password changed from what we knew (raw_password)
                if admin_password and admin_password != admin.raw_password:
                    admin.set_password(admin_password)
                    admin.raw_password = admin_password
                    updated = True
                    
                if updated:
                    admin.save()
                    messages.success(request, _("Maktab va admin ma'lumotlari yangilandi!"))
                else:
                    messages.success(request, _("Maktab ma'lumotlari yangilandi!"))
            else:
                # Create NEW admin
                admin_username = form.cleaned_data.get('admin_username')
                admin_password = form.cleaned_data.get('admin_password')
                
                if admin_username and admin_password:
                    new_admin = CustomUser.objects.create_user(
                        username=admin_username,
                        password=admin_password,
                        role='school_admin',
                        school=school,
                        first_name='Admin',
                        last_name=school.name
                    )
                    new_admin.raw_password = admin_password
                    new_admin.save()
                    messages.success(request, f"Maktab uchun yangi admin yaratildi! Login: {admin_username}")



            return redirect('frontend_admin:schools_list')

    else:
        initial = {}
        if admin:
            initial['admin_username'] = admin.username
            if admin.raw_password:
                initial['admin_password'] = admin.raw_password
                initial['admin_password_confirm'] = admin.raw_password

        
        form = UnifiedSchoolForm(instance=school, initial=initial, current_admin_id=admin.pk if admin else None)
    
    # Fetch Districts and Schools for consistent template behavior
    from django.db.models import Prefetch
    districts = District.objects.prefetch_related(
        Prefetch('schools', queryset=School.objects.all().order_by('name'))
    ).order_by('name')
    schools_with_admins = CustomUser.objects.filter(role='school_admin').values_list('school_id', flat=True)

    return render(request, 'admin_panel/school_form.html', {
        'form': form, 
        'title': _('Maktab ma\'lumotlarini tahrirlash'),
        'districts': districts,
        'schools_with_admins': list(schools_with_admins)
    })

@login_required(login_url='login')
@superuser_required
def school_delete(request, pk):
    school = get_object_or_404(School, pk=pk)
    if request.method == 'POST':
        school.delete()
        return redirect('frontend_admin:schools_list')
    return render(request, 'admin_panel/confirm_delete.html', {'object': school, 'type': _('maktabni')})

from .forms import SchoolAdminForm

@login_required(login_url='login')
@superuser_required
def admin_add(request):
    if request.method == 'POST':
        form = SchoolAdminForm(request.POST)
        if form.is_valid():
            admin = form.save(commit=False)
            admin.role = 'school_admin'
            
            # Initial save to get ID
            admin.username = f"temp_adm_{secrets.token_hex(4)}"
            admin.save()
            
            # Smart credentials
            def clean_name(name):
                return "".join(c for c in name.lower() if c.isalnum() or c == '_').strip('_')
            
            district_part = clean_name(admin.school.district.name if admin.school and admin.school.district else "no")
            school_part = clean_name(admin.school.name if admin.school else "school")
            
            username = f"{district_part}_{school_part}_adm_{admin.id}"
            admin.username = username
            
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alphabet) for i in range(12))
            admin.set_password(password)
            admin.raw_password = password
            admin.save()
            
            from django.contrib import messages
            messages.success(request, f"Admin yaratildi! Login: {username}, Parol: {password}")
            
            return redirect('frontend_admin:all_users_list')
    else:
        form = SchoolAdminForm()
    from django.urls import reverse
    return render(request, 'admin_panel/muassasa_form.html', {'form': form, 'title': _('Yangi maktab admini qo\'shish'), 'cancel_url': reverse('frontend_admin:all_users_list')})

@login_required(login_url='login')
@superuser_required
def admin_edit(request, pk):
    admin = get_object_or_404(CustomUser, pk=pk, role='school_admin')
    
    if admin.school:
        return redirect('frontend_admin:school_edit', pk=admin.school.pk)
        
    if request.method == 'POST':
        form = SchoolAdminForm(request.POST, instance=admin)
        if form.is_valid():
            form.save()
            return redirect('frontend_admin:all_users_list')
    else:
        form = SchoolAdminForm(instance=admin)
    from django.urls import reverse
    return render(request, 'admin_panel/muassasa_form.html', {'form': form, 'title': _('Admin ma\'lumotlarini tahrirlash'), 'cancel_url': reverse('frontend_admin:all_users_list')})

@login_required(login_url='login')
@superuser_required
def profile(request):
    return render(request, 'admin_panel/profile.html')

@login_required(login_url='login')
@superuser_required
def change_password(request):
    from django.contrib.auth.forms import PasswordChangeForm
    from django.contrib.auth import update_session_auth_hash
    from django.contrib import messages
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.raw_password = form.cleaned_data.get('new_password1')
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, _('Parolingiz muvaffaqiyatli o\'zgartirildi!'))
            return redirect('frontend_admin:profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'admin_panel/password_change.html', {'form': form})


# News Management
@login_required(login_url='login')
@superuser_required
def news_list(request):
    # Only superadmins should see global news management
    if not request.user.is_superuser:
        return redirect('login')
    news = News.objects.filter(school__isnull=True).order_by('-created_at')
    return render(request, 'admin_panel/news/list.html', {'news': news})

@login_required(login_url='login')
@superuser_required
def news_add(request):
    if not request.user.is_superuser:
        return redirect('login')
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES)
        if form.is_valid():
            news = form.save(commit=False)
            news.school = None # Explicitly set to None for global news
            news.save()
            return redirect('frontend_admin:news_list')
    else:
        form = NewsForm()
    return render(request, 'admin_panel/news/form.html', {'form': form, 'title': _("Yangi xabar qo'shish")})

@login_required(login_url='login')
@superuser_required
def news_edit(request, pk):
    if not request.user.is_superuser:
        return redirect('login')
    news = get_object_or_404(News, pk=pk, school__isnull=True)
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES, instance=news)
        if form.is_valid():
            form.save()
            return redirect('frontend_admin:news_list')
    else:
        form = NewsForm(instance=news)
    return render(request, 'admin_panel/news/form.html', {'form': form, 'title': _("Xabarni tahrirlash")})

@login_required(login_url='login')
@superuser_required
def news_delete(request, pk):
    if not request.user.is_superuser:
        return redirect('login')
    news = get_object_or_404(News, pk=pk, school__isnull=True)
    if request.method == 'POST':
        news.delete()
        return redirect('frontend_admin:news_list')
    return render(request, 'admin_panel/confirm_delete.html', {'object': news, 'type': 'yangilikni'})
