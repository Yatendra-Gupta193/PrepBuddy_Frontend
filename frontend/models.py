from django.db import models
from django.contrib.auth.models import User

class StaffProfile(models.Model):
    ROLE_CHOICES=[
        ("clinic_staff","Clinic Staff"),
        ("doctor","Doctor"),
    ]
    user=models.OneToOneField(User,on_delete=models.CASCADE,related_name="staff_profile")
    role=models.CharField(max_length=30,choices=ROLE_CHOICES,default="clinic_staff")
    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.role}"