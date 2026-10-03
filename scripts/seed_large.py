import os
import sys
import django
import random
from datetime import timedelta
from django.utils import timezone

# Add project root directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from schools.models import School, District, Subject, Institution
from books.models import Book, Category, BookIssue, BookRequest
from frontend_school.models import News
from accounts.models import CustomUser

def seed():
    print("Starting Karakalpakstan data seeding...")

    # Optional: Clear existing data to avoid mixing Tashkent and Karakalpakstan
    print("Clearing old districts and schools data...")
    Book.objects.all().delete()
    School.objects.all().delete()
    District.objects.all().delete()
    Institution.objects.all().delete()
    # Keep superusers, but maybe delete other demo users
    CustomUser.objects.filter(is_superuser=False).delete()

    # 1. Create Districts (Karakalpakstan)
    districts_names = [
        "Nukus shahri", "Amudaryo tumani", "Beruniy tumani", "Chimboy tumani", 
        "Ellikqala tumani", "Kegeyli tumani", "Mo'ynoq tumani", "Nukus tumani", 
        "Qonliko'l tumani", "Qorao'zak tumani", "Qo'ng'irot tumani", "Shumanay tumani", 
        "Taxtako'pir tumani", "To'rtko'l tumani", "Xo'jayli tumani", "Taxiatosh tumani", 
        "Bo'zatov tumani"
    ]
    districts = []
    for name in districts_names:
        d, _ = District.objects.get_or_create(name=name)
        districts.append(d)
    print(f"Created {len(districts)} districts in Karakalpakstan.")

    # 2. Create Subjects
    subjects_names = [
        "Matematika", "Fizika", "Kimyo", "Biologiya", "Informatika", 
        "O'zbek tili", "Qoraqalpoq tili", "Rus tili", "Ingliz tili", "Tarix", 
        "Geografiya", "Adabiyot", "Tasviriy san'at", "Musiqa", "Jismoniy tarbiya"
    ]
    subjects = []
    for name in subjects_names:
        s, _ = Subject.objects.get_or_create(name=name)
        subjects.append(s)
    print(f"Created/found {len(subjects)} subjects.")

    # 3. Create Categories
    categories_names = [
        "Badiiy adabiyot", "Ilmiy-ommabop", "Tarixiy", "Darslik", 
        "Xorijiy tillar", "Psixologiya", "Bolalar adabiyoti", "Detektiv"
    ]
    categories = []
    for name in categories_names:
        c, _ = Category.objects.get_or_create(name=name)
        categories.append(c)
    print(f"Created/found {len(categories)} categories.")

    # 4. Create Schools and Users
    first_names = ["Anvar", "Baxit", "Daulet", "Erkin", "Farhod", "Gulmira", "Inju", "Jalgas", "Kuanish", "Madiyar", "Nurbek", "Oydin", "Polat", "Qural"]
    last_names = ["Kidirbaev", "Embergenov", "Dauletov", "Saparov", "Jumanazarov", "Oralbaev", "Tadjibaev", "Mamutov", "Begjanov", "Ametov"]

    book_titles = [
        "O'tkan kunlar", "Mehrobdan chayon", "Sariq devni minib", "Shum bola", 
        "Ufq", "Ikki eshik orasi", "Dunyoning ishlari", "Yulduzli tunlar", 
        "Avlodlar dovoni", "Kecha va kunduz", "Navoiy", "Jimjitlik", 
        "Sohibqiron", "Temur tuzuklari", "Al-Kimyogar", "1984", 
        "Kichik shahzoda", "Sherlok Xolms", "Garri Potter", "Raqamli qal'a",
        "Boy ota, kambag'al ota", "Muvaffaqiyat kaliti", "O'z-o'ziga yordam",
        "Fizika 7-sinf", "Algebra 8-sinf", "Kimyo 9-sinf", "Ingliz tili darsligi"
    ]

    def clean_name(name):
        return "".join(c for c in name.lower() if c.isalnum() or c == '_').strip('_')

    for d_idx, district in enumerate(districts):
        # 2 schools per district for Karakalpakstan (since there are more districts)
        num_schools = 2 if d_idx > 0 else 3 # 3 for Nukus city
        for i in range(1, num_schools + 1): 
            school_name = f"{district.name} {i}-sonli maktab"
            school = School.objects.create(
                name=school_name,
                address=f"{district.name}, Markaziy ko'chasi, {random.randint(1, 150)}-uy",
                contact=f"+99861{random.randint(222, 999)}{random.randint(1000, 9999)}",
                district=district
            )
            
            print(f"  Seeding {school_name}...")

            district_part = clean_name(school.district.name if school.district else "no")
            school_part = clean_name(school.name)

            # School Admin (Librarian)
            admin = CustomUser.objects.create_user(
                username=f"temp_adm_{d_idx}_{i}", 
                password="password123", 
                role="school_admin", 
                school=school,
                first_name=random.choice(first_names),
                last_name=random.choice(last_names)
            )
            admin.username = f"{district_part}_{school_part}_adm_{admin.id}"
            admin.raw_password = 'password123'
            admin.save()

            # Teachers
            for t in range(10): # Increased to 10
                teacher = CustomUser.objects.create_user(
                    username=f"temp_t_{d_idx}_{i}_{t}",
                    password="password123",
                    role="teacher",
                    school=school,
                    first_name=random.choice(first_names),
                    last_name=random.choice(last_names),
                    subject=random.choice(subjects).name
                )
                teacher.username = f"{district_part}_{school_part}_{teacher.id}"
                teacher.raw_password = 'password123'
                teacher.save()

            # Students
            grades = ["7-A", "7-B", "8-A", "8-B", "9-A", "9-V", "10-A", "11-B"]
            students = []
            for s in range(100): # Increased to 100
                student = CustomUser.objects.create_user(
                    username=f"temp_st_{d_idx}_{i}_{s}",
                    password="password123",
                    role="student",
                    school=school,
                    first_name=random.choice(first_names),
                    last_name=random.choice(last_names),
                    grade=random.choice(grades)
                )
                student.username = f"{district_part}_{school_part}_{student.id}"
                student.raw_password = 'password123'
                student.save()
                students.append(student)


            # Books
            books = []
            for b in range(150): # Increased to 150
                title = f"{random.choice(book_titles)} {random.randint(1, 1000)}" if b > len(book_titles) else book_titles[b % len(book_titles)]
                total = random.randint(10, 100)
                book = Book.objects.create(
                    school=school,
                    title=title,
                    description=f"Bu '{title}' kitobi haqida qisqacha ma'lumot. Kitob juda qiziqarli va foydali.",
                    category=random.choice(categories),
                    total_count=total,
                    available_count=total,
                    borrow_count=random.randint(0, 500)
                )
                books.append(book)

            # Book Issues (Loans)
            for _ in range(30): # 30 issues per school
                student = random.choice(students)
                book = random.choice(books)
                if book.available_count > 0:
                    is_returned = random.choice([True, False])
                    issued_at = timezone.now() - timedelta(days=random.randint(1, 30))
                    
                    issue = BookIssue.objects.create(
                        book=book,
                        user=student,
                        issued_at=issued_at,
                        is_returned=is_returned
                    )
                    
                    if is_returned:
                        issue.returned_at = issue.issued_at + timedelta(days=random.randint(1, 14))
                        issue.save()
                    else:
                        book.available_count -= 1
                        book.save()

            # News
            for n in range(3):
                News.objects.create(
                    school=school,
                    title=f"Maktab yangiligi #{n+1}",
                    body=f"Hurmatli o'quvchilar! Maktabimizda kitobxonlik haftaligi e'lon qilindi. Barcha o'quvchilarni kutubxonamizga taklif qilamiz.",
                    is_published=True
                )

    # 5. Institutions (Karakalpakstan)
    kk_institutions = [
        "Qoraqalpoq davlat universiteti",
        "Nukus davlat pedagogika instituti",
        "Toshkent tibbiyot akademiyasi Nukus filiali",
        "O'zbekiston davlat san'at va madaniyat instituti Nukus filiali",
        "Toshkent axborot texnologiyalari universiteti Nukus filiali",
        "Beruniy nomidagi Qoraqalpoq davlat universiteti",
        "Nukus innovatsion instituti"
    ]
    for name in kk_institutions:
        Institution.objects.create(
            name=name,
            address="Nukus shahri, Markaz"
        )

    # 6. Create exact Demo Accounts from User Specification/Screenshot
    first_school = School.objects.first()

    # 1) Superuser (admin / superadmin)
    admin_user, _ = CustomUser.objects.get_or_create(username="admin")
    admin_user.set_password("superadmin")
    admin_user.is_superuser = True
    admin_user.is_staff = True
    admin_user.role = "superuser"
    admin_user.raw_password = "superadmin"
    admin_user.first_name = "System"
    admin_user.last_name = "Superadmin"
    admin_user.save()

    # 2) School Admin (school_admin / password123)
    s_admin, _ = CustomUser.objects.get_or_create(username="school_admin")
    s_admin.set_password("password123")
    s_admin.role = "school_admin"
    s_admin.school = first_school
    s_admin.raw_password = "password123"
    s_admin.first_name = "School"
    s_admin.last_name = "Admin"
    s_admin.save()

    # 3) Teacher (teacher_demo / password123)
    t_demo, _ = CustomUser.objects.get_or_create(username="teacher_demo")
    t_demo.set_password("password123")
    t_demo.role = "teacher"
    t_demo.school = first_school
    t_demo.subject = "Matematika"
    t_demo.raw_password = "password123"
    t_demo.first_name = "Demo"
    t_demo.last_name = "O'qituvchi"
    t_demo.save()

    # 4) Student (student_demo / password123)
    st_demo, _ = CustomUser.objects.get_or_create(username="student_demo")
    st_demo.set_password("password123")
    st_demo.role = "student"
    st_demo.school = first_school
    st_demo.grade = "9-A"
    st_demo.raw_password = "password123"
    st_demo.first_name = "Demo"
    st_demo.last_name = "O'quvchi"
    st_demo.save()

    print("\nKarakalpakstan data seeding & Demo Accounts creation completed successfully!")
    print(f"Total Schools: {School.objects.count()}")
    print(f"Total Users: {CustomUser.objects.count()}")
    print(f"Total Books: {Book.objects.count()}")
    print("\nDemo Accounts Created:")
    print("  Superuser:    login: admin        | pass: superadmin")
    print("  School Admin: login: school_admin | pass: password123")
    print("  Teacher:      login: teacher_demo | pass: password123")
    print("  Student:      login: student_demo | pass: password123")

if __name__ == '__main__':
    seed()
