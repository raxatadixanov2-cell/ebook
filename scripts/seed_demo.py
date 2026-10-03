import os
import sys
import django

# Add project root directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from schools.models import School
from books.models import Book, Category
from accounts.models import CustomUser

def seed():
    # Create Schools
    s1 = School.objects.create(name="Toshkent 1-sonli maktab", address="Toshkent sh., Yunusobod", contact="+998901234567")
    s2 = School.objects.create(name="Samarqand 12-sonli maktab", address="Samarqand sh., Registon", contact="+998912345678")
    
    # Create Categories
    c1 = Category.objects.create(name="Badiiy adabiyot")
    c2 = Category.objects.create(name="Ilmiy-ommabop")
    
    # Create Books
    Book.objects.create(
        school=s1, title="O'tkan kunlar", description="Abdulla Qodiriyning shoh asari.", 
        category=c1, total_count=10, available_count=8, borrow_count=25
    )
    Book.objects.create(
        school=s1, title="Mehrobdan chayon", description="Tarixiy roman.", 
        category=c1, total_count=5, available_count=5, borrow_count=12
    )
    Book.objects.create(
        school=s2, title="Fizika asoslari", description="Maktab darsligi.", 
        category=c2, total_count=20, available_count=20, borrow_count=5
    )
    
    # 1) Superuser (admin / superadmin)
    admin_user, _ = CustomUser.objects.get_or_create(username="admin")
    admin_user.set_password("superadmin")
    admin_user.is_superuser = True
    admin_user.is_staff = True
    admin_user.role = "superuser"
    admin_user.raw_password = "superadmin"
    admin_user.save()

    # 2) School Admin (school_admin / password123)
    s_admin, _ = CustomUser.objects.get_or_create(username="school_admin")
    s_admin.set_password("password123")
    s_admin.role = "school_admin"
    s_admin.school = s1
    s_admin.raw_password = "password123"
    s_admin.save()

    # 3) Teacher (teacher_demo / password123)
    t_demo, _ = CustomUser.objects.get_or_create(username="teacher_demo")
    t_demo.set_password("password123")
    t_demo.role = "teacher"
    t_demo.school = s1
    t_demo.subject = "Matematika"
    t_demo.raw_password = "password123"
    t_demo.save()

    # 4) Student (student_demo / password123)
    st_demo, _ = CustomUser.objects.get_or_create(username="student_demo")
    st_demo.set_password("password123")
    st_demo.role = "student"
    st_demo.school = s1
    st_demo.grade = "9-A"
    st_demo.raw_password = "password123"
    st_demo.save()

    print("Demo data seeded successfully with picture accounts!")

if __name__ == '__main__':
    seed()
