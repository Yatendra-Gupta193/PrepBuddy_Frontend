from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import StaffProfile


User = get_user_model()


class FrontendAuthFlowTests(TestCase):
    def test_login_sets_session_profile_data(self):
        user = User.objects.create_user(
            username="doctor@prepbuddy.ai",
            email="doctor@prepbuddy.ai",
            password="secret123",
            first_name="Dr. Sharma",
        )
        StaffProfile.objects.create(user=user, role="doctor")

        response = self.client.post(
            "/login/",
            {"email": "doctor@prepbuddy.ai", "password": "secret123"},
            follow=True,
        )

        self.assertRedirects(response, "/")
        self.assertEqual(self.client.session["user_name"], "Dr. Sharma")
        self.assertEqual(self.client.session["user_id"], user.id)
        self.assertEqual(self.client.session["user_role"], "doctor")

    def test_login_page_hides_primary_navigation_for_guest_users(self):
        response = self.client.get("/login/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Dashboard")
        self.assertNotContains(response, "Logout")

    def test_dashboard_search_and_session_state_sync(self):
        user = User.objects.create_user(
            username="staff@prepbuddy.ai",
            email="staff@prepbuddy.ai",
            password="secret123",
            first_name="Prep Staff",
        )
        StaffProfile.objects.create(user=user, role="clinic_staff")
        self.client.post(
            "/login/",
            {"email": "staff@prepbuddy.ai", "password": "secret123"},
        )

        dashboard = self.client.get("/?search=rahul")
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "Rahul Kumar")
        self.assertNotContains(dashboard, "Priya Nair")

        response = self.client.post("/procedures/rahul/confirm/2/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session["timeline_actions"]["rahul"]["2"]["status"], "confirmed")

        patient = self.client.get("/patients/rahul/")
        self.assertContains(patient, "Confirmed by clinic staff")

    def test_protected_pages_redirect_guest_and_logout_flushes_session(self):
        unauth = self.client.get("/")
        self.assertEqual(unauth.status_code, 302)
        self.assertIn("/login/", unauth.url)

        user = User.objects.create_user(
            username="logout@prepbuddy.ai",
            email="logout@prepbuddy.ai",
            password="secret123",
            first_name="Logout User",
        )
        StaffProfile.objects.create(user=user, role="doctor")
        self.client.post(
            "/login/",
            {"email": "logout@prepbuddy.ai", "password": "secret123"},
        )

        logout = self.client.post("/logout/", follow=True)
        self.assertEqual(logout.status_code, 200)
        self.assertContains(logout, "Welcome to PrepBuddy")
        self.assertNotIn("user_id", self.client.session)

    def test_patient_list_page_and_add_patient_flow(self):
        user = User.objects.create_user(
            username="patientadmin@prepbuddy.ai",
            email="patientadmin@prepbuddy.ai",
            password="secret123",
            first_name="Patient Admin",
        )
        StaffProfile.objects.create(user=user, role="clinic_staff")
        self.client.post(
            "/login/",
            {"email": "patientadmin@prepbuddy.ai", "password": "secret123"},
        )

        patient_list = self.client.get("/patients/")
        self.assertEqual(patient_list.status_code, 200)
        self.assertContains(patient_list, "Patient List")

        add_response = self.client.post(
            "/patients/add/",
            {
                "patient_id": "kavya",
                "name": "Kavya Patel",
                "gender": "Female",
                "age": "29",
                "phone": "+91 98765 43210",
                "email": "kavya@example.com",
                "procedure": "Colonoscopy",
                "procedure_date": "2026-10-12",
                "procedure_time": "08:00",
                "physician": "Dr. Sharma",
                "suite": "Endo Suite 3",
                "protocol": "colonoscopy",
            },
            follow=True,
        )
        self.assertEqual(add_response.status_code, 200)
        self.assertContains(add_response, "Kavya Patel")
        self.assertIn("kavya", self.client.session.get("custom_patients", {}))

    def test_new_patient_starts_pending_and_not_risk(self):
        user = User.objects.create_user(
            username="rohan@prepbuddy.ai",
            email="rohan@prepbuddy.ai",
            password="secret123",
            first_name="Rohan",
        )
        StaffProfile.objects.create(user=user, role="clinic_staff")
        self.client.post(
            "/login/",
            {"email": "rohan@prepbuddy.ai", "password": "secret123"},
        )

        self.client.post(
            "/patients/add/",
            {
                "patient_id": "rohan",
                "name": "Rohan Verma",
                "gender": "Male",
                "age": "30",
                "phone": "+91 99999 12345",
                "email": "rohan@example.com",
                "procedure": "Colonoscopy",
                "procedure_date": "2026-10-15",
                "procedure_time": "08:00",
                "physician": "Dr. Sharma",
                "suite": "Endo Suite 4",
                "protocol": "colonoscopy",
            },
        )

        patient = self.client.session["custom_patients"]["rohan"]
        self.assertEqual(patient["status"], "pending")
        self.assertTrue(all(step["status"] == "pending" for step in patient["steps"]))

        dashboard = self.client.get("/?search=rohan")
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "Rohan Verma")
        self.assertNotContains(dashboard, "Take second prep dose")

    def test_procedure_timeline_overview_lists_patients(self):
        user = User.objects.create_user(
            username="timelineview@prepbuddy.ai",
            email="timelineview@prepbuddy.ai",
            password="secret123",
            first_name="Timeline View",
        )
        StaffProfile.objects.create(user=user, role="clinic_staff")
        self.client.post(
            "/login/",
            {"email": "timelineview@prepbuddy.ai", "password": "secret123"},
        )

        response = self.client.get("/procedures/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Procedure Timeline")
        self.assertContains(response, "Rahul Kumar")
        self.assertContains(response, "Priya Nair")
        self.assertContains(response, "Ananya Sharma")
        self.assertContains(response, "Open Timeline")

    def test_dashboard_groups_risk_actions_per_patient(self):
        user = User.objects.create_user(
            username="dashboardrisk@prepbuddy.ai",
            email="dashboardrisk@prepbuddy.ai",
            password="secret123",
            first_name="Dashboard Risk",
        )
        StaffProfile.objects.create(user=user, role="clinic_staff")
        self.client.post(
            "/login/",
            {"email": "dashboardrisk@prepbuddy.ai", "password": "secret123"},
        )

        response = self.client.get("/")
        html = response.content.decode()

        self.assertContains(response, "Take second prep dose")
        self.assertNotContains(response, "Final confirmation")
        self.assertEqual(html.count("Nudge"), 2)
        self.assertEqual(html.count("Verify"), 2)

    def test_edit_and_delete_patient_flow(self):
        user = User.objects.create_user(
            username="patienteditor@prepbuddy.ai",
            email="patienteditor@prepbuddy.ai",
            password="secret123",
            first_name="Patient Editor",
        )
        StaffProfile.objects.create(user=user, role="clinic_staff")
        self.client.post(
            "/login/",
            {"email": "patienteditor@prepbuddy.ai", "password": "secret123"},
        )

        self.client.post(
            "/patients/add/",
            {
                "patient_id": "rhea",
                "name": "Rhea Shah",
                "gender": "Female",
                "age": "31",
                "phone": "+91 90000 11111",
                "email": "rhea@example.com",
                "procedure": "Upper GI",
                "procedure_date": "2026-11-02",
                "procedure_time": "09:30",
                "physician": "Dr. Gupta",
                "suite": "Suite 5",
                "protocol": "upper-gi",
            },
        )

        edit_response = self.client.post(
            "/patients/rhea/edit/",
            {
                "patient_id": "rhea",
                "name": "Rhea S. Shah",
                "gender": "Female",
                "age": "31",
                "phone": "+91 90000 11111",
                "email": "rhea@example.com",
                "procedure": "Upper GI",
                "procedure_date": "2026-11-02",
                "procedure_time": "10:00",
                "physician": "Dr. Gupta",
                "suite": "Suite 6",
                "protocol": "upper-gi",
            },
            follow=True,
        )
        self.assertEqual(edit_response.status_code, 200)
        self.assertContains(edit_response, "Rhea S. Shah")

        delete_response = self.client.post("/patients/rhea/delete/", follow=True)
        self.assertEqual(delete_response.status_code, 200)
        self.assertNotIn("rhea", self.client.session.get("custom_patients", {}))
