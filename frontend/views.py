from django.shortcuts import render,redirect
from django.contrib.auth import authenticate,login as auth_login,logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import StaffProfile

PATIENTS={
"rahul":{
"id":"rahul",
"name":"Rahul Kumar",
"initials":"RK",
"gender":"Male",
"age":44,
"phone":"+91 XXXXX XXXXX",
"procedure":"Colonoscopy",
"procedure_time":"Tomorrow, 8:00 AM",
"physician":"Dr. Sharma",
"suite":"Endo Suite 2",
"steps":[
{"name":"Avoid solid foods","time":"18:00","status":"confirmed","message":"Confirmed (Yesterday 18:14)"},
{"name":"Take first prep dose","time":"20:00","status":"confirmed","message":"Confirmed (Yesterday 20:22)"},
{"name":"Take second prep dose","time":"02:00","status":"risk","message":"Not confirmed · Overdue window (SMS)"},
{"name":"Final confirmation","time":"05:00","status":"pending","message":"Pending confirmation"}
]},
"priya":{
"id":"priya",
"name":"Priya Nair",
"initials":"PN",
"gender":"Female",
"age":39,
"phone":"+91 XXXXX XXXXX",
"procedure":"Colonoscopy",
"procedure_time":"Today, 8:30 PM",
"physician":"Dr. Sharma",
"suite":"Endo Suite 1",
"steps":[
{"name":"Avoid solid foods","time":"14:30","status":"confirmed","message":"Confirmed (Today 14:32)"},
{"name":"Take first prep dose","time":"16:30","status":"confirmed","message":"Confirmed (Today 16:40)"},
{"name":"Take second prep dose","time":"18:30","status":"risk","message":"Not confirmed · Overdue window (SMS)"},
{"name":"Final confirmation","time":"19:30","status":"pending","message":"Pending confirmation"}
]},
"ananya":{
"id":"ananya",
"name":"Ananya Sharma",
"initials":"AS",
"gender":"Female",
"age":36,
"phone":"+91 XXXXX XXXXX",
"procedure":"Colonoscopy",
"procedure_time":"Today, 7:00 PM",
"physician":"Dr. Sharma",
"suite":"Endo Suite 1",
"steps":[
{"name":"Avoid solid foods","time":"13:00","status":"confirmed","message":"Confirmed"},
{"name":"Take first prep dose","time":"15:00","status":"confirmed","message":"Confirmed"},
{"name":"Take second prep dose","time":"17:00","status":"confirmed","message":"Confirmed"},
{"name":"Final confirmation","time":"18:00","status":"confirmed","message":"Confirmed"}
]}}

DEFAULT_PATIENT_STEPS=[
    {"name":"Avoid solid foods","time":"18:00","status":"pending","message":"Pending confirmation"},
    {"name":"Take first prep dose","time":"20:00","status":"pending","message":"Pending confirmation"},
    {"name":"Take second prep dose","time":"02:00","status":"pending","message":"Pending confirmation"},
    {"name":"Final confirmation","time":"05:00","status":"pending","message":"Pending confirmation"},
]


def get_custom_patients(request):
    return request.session.get("custom_patients", {})


def save_custom_patients(request, patients):
    request.session["custom_patients"] = patients
    request.session.modified = True


def build_patient_payload(data):
    patient = {"id": str(data.get("patient_id") or data.get("id") or "").strip().lower()}
    patient["name"] = (data.get("name") or "").strip()
    patient["initials"] = ("".join(part[0].upper() for part in patient["name"].split()[:2]) if patient["name"] else "PT")
    patient["gender"] = (data.get("gender") or "Unknown").strip()
    patient["age"] = int(data.get("age") or 0)
    patient["phone"] = (data.get("phone") or "").strip()
    patient["email"] = (data.get("email") or "").strip()
    patient["procedure"] = (data.get("procedure") or "General Procedure").strip()
    patient["procedure_time"] = data.get("procedure_time") or "TBD"
    patient["physician"] = (data.get("physician") or "Dr. Sharma").strip()
    patient["suite"] = (data.get("suite") or "Clinic Suite").strip()
    patient["protocol"] = (data.get("protocol") or "colonoscopy").strip()
    patient["steps"] = [
        {"name": step.get("name"), "time": step.get("time"), "status": step.get("status", "pending"), "message": step.get("message", "Pending confirmation")} for step in (data.get("steps") or DEFAULT_PATIENT_STEPS)
    ]
    patient["total_steps"] = len(patient["steps"])
    patient["completed_steps"] = sum(1 for step in patient["steps"] if step["status"] == "confirmed")
    if patient["completed_steps"] == patient["total_steps"]:
        patient["status"] = "ready"
    elif any(step["status"] == "risk" for step in patient["steps"]):
        patient["status"] = "risk"
    else:
        patient["status"] = "pending"
    return patient


def get_patient_data(request):
    patients={}
    actions=request.session.get("timeline_actions",{})
    custom_patients=get_custom_patients(request)
    for patient_id,data in {**PATIENTS, **custom_patients}.items():
        patient={**data}
        patient["steps"]=[step.copy() for step in data.get("steps", DEFAULT_PATIENT_STEPS)]
        patient_actions=actions.get(patient_id,{})
        for index,step in enumerate(patient["steps"]):
            saved_action=patient_actions.get(str(index))
            if saved_action:
                step["status"]=saved_action["status"]
                if saved_action["status"]=="confirmed":
                    step["message"]="Confirmed by clinic staff"
                elif saved_action["status"]=="risk":
                    step["message"]="Not confirmed · Staff action required"
        patient["total_steps"]=len(patient["steps"])
        patient["completed_steps"]=sum(1 for step in patient["steps"] if step["status"]=="confirmed")
        if patient["completed_steps"]==patient["total_steps"]:
            patient["status"]="ready"
        elif any(step["status"]=="risk" for step in patient["steps"]):
            patient["status"]="risk"
        else:
            patient["status"]="pending"
        patients[patient_id]=patient
    return patients


def set_session_user(request, user):
    profile = getattr(user, "staff_profile", None)
    request.session["user_id"]=user.id
    request.session["user_name"]=user.get_full_name() or user.username
    request.session["user_role"]=profile.role if profile else "clinic_staff"
    request.session.modified=True

@login_required
def dashboard(request):
    patients=get_patient_data(request)
    patient_list=list(patients.values())

    for patient in patient_list:
        patient["risk_steps"]=[
            step for step in patient.get("steps", [])
            if step.get("status") == "risk"
        ]
        patient["primary_risk_index"] = next(
            (
                index
                for index, step in enumerate(patient.get("steps", []))
                if step.get("status") == "risk"
            ),
            0,
        )

    procedures_count=len(patient_list)
    ready_count=sum(1 for patient in patient_list if patient["status"]=="ready")
    pending_count=sum(1 for patient in patient_list if patient["status"]=="pending")
    risk_count=sum(1 for patient in patient_list if patient["status"]=="risk")

    search=request.GET.get("search","").strip().lower()

    def matches_search(patient):
        if not search:
            return True
        searchable_text=" ".join([
            patient["id"],
            patient["name"],
            patient["procedure"],
            patient["physician"],
            patient["suite"]
        ]).lower()
        return search in searchable_text

    risk_patients=[patient for patient in patient_list if patient["status"]=="risk" and matches_search(patient)]
    upcoming_patients=[patient for patient in patient_list if matches_search(patient)]

    return render(request,"dashboard.html",{
        "procedures":procedures_count,
        "ready":ready_count,
        "pending":pending_count,
        "risk":len(risk_patients) if search else risk_count,
        "risk_patients":risk_patients,
        "patients":upcoming_patients,
        "search":request.GET.get("search","")
    })

@login_required
def patient_list(request):
    patients=get_patient_data(request)
    patient_list=list(patients.values())

    search=request.GET.get("search","").strip().lower()
    status_filter=request.GET.get("status","all").lower()

    def matches_search(patient):
        if not search:
            return True
        searchable_text=" ".join([patient.get("id",""), patient.get("name",""), patient.get("procedure",""), patient.get("physician",""), patient.get("suite","")]).lower()
        return search in searchable_text

    def matches_status(patient):
        if status_filter == "all":
            return True
        return patient.get("status") == status_filter

    filtered_patients=[patient for patient in patient_list if matches_search(patient) and matches_status(patient)]

    return render(request,"patient_list.html",{
        "patients":filtered_patients,
        "search":search,
        "status_filter":status_filter,
        "total_patients":len(patient_list),
        "ready_count":sum(1 for patient in patient_list if patient.get("status") == "ready"),
        "pending_count":sum(1 for patient in patient_list if patient.get("status") == "pending"),
        "risk_count":sum(1 for patient in patient_list if patient.get("status") == "risk"),
    })


@login_required
def add_patient(request):
    if request.method == "POST":
        patient_id=request.POST.get("patient_id","").strip().lower()
        name=request.POST.get("name","").strip()
        gender=request.POST.get("gender","").strip()
        age=request.POST.get("age","").strip()
        phone=request.POST.get("phone","").strip()
        email=request.POST.get("email","").strip()
        procedure=request.POST.get("procedure","").strip()
        procedure_date=request.POST.get("procedure_date","").strip()
        procedure_time=request.POST.get("procedure_time","").strip()
        physician=request.POST.get("physician","").strip()
        suite=request.POST.get("suite","").strip()
        protocol=request.POST.get("protocol","").strip()

        if not all([patient_id, name, gender, age, phone, email, procedure, procedure_date, procedure_time, physician, suite, protocol]):
            messages.error(request, "Please fill in all patient fields.")
            return render(request, "patient_form.html", {"mode": "add", "patient": {"patient_id": patient_id, "name": name, "gender": gender, "age": age, "phone": phone, "email": email, "procedure": procedure, "procedure_date": procedure_date, "procedure_time": procedure_time, "physician": physician, "suite": suite, "protocol": protocol}, "errors": True})

        if not age.isdigit() or int(age) <= 0:
            messages.error(request, "Age must be a valid number.")
            return render(request, "patient_form.html", {"mode": "add", "patient": {"patient_id": patient_id, "name": name, "gender": gender, "age": age, "phone": phone, "email": email, "procedure": procedure, "procedure_date": procedure_date, "procedure_time": procedure_time, "physician": physician, "suite": suite, "protocol": protocol}, "errors": True})

        custom_patients=get_custom_patients(request)
        if patient_id in PATIENTS or patient_id in custom_patients:
            messages.error(request, "A patient with this ID already exists.")
            return render(request, "patient_form.html", {"mode": "add", "patient": {"patient_id": patient_id, "name": name, "gender": gender, "age": age, "phone": phone, "email": email, "procedure": procedure, "procedure_date": procedure_date, "procedure_time": procedure_time, "physician": physician, "suite": suite, "protocol": protocol}, "errors": True})

        formatted_time = f"{procedure_date} {procedure_time}"
        patient_payload = {
            "patient_id": patient_id,
            "name": name,
            "gender": gender,
            "age": int(age),
            "phone": phone,
            "email": email,
            "procedure": procedure,
            "procedure_time": formatted_time,
            "physician": physician,
            "suite": suite,
            "protocol": protocol,
            "steps": [
                {"name": "Avoid solid foods","time": "18:00","status": "pending","message": "Pending confirmation"},
                {"name": "Take first prep dose","time": "20:00","status": "pending","message": "Pending confirmation"},
                {"name": "Take second prep dose","time": "02:00","status": "pending","message": "Pending confirmation"},
                {"name": "Final confirmation","time": "05:00","status": "pending","message": "Pending confirmation"},
            ],
        }
        custom_patients[patient_id] = build_patient_payload(patient_payload)
        save_custom_patients(request, custom_patients)
        messages.success(request, "Patient added successfully.")
        return redirect("patient_detail", patient_id=patient_id)

    return render(request, "patient_form.html", {"mode": "add", "patient": None})


@login_required
def edit_patient(request, patient_id):
    patients=get_patient_data(request)
    patient=patients.get((patient_id or "").lower())
    if not patient:
        return render(request, "patient_form.html", {"mode": "edit", "patient": None, "patient_id": patient_id})

    if request.method == "POST":
        patient_id_value=request.POST.get("patient_id","").strip().lower()
        name=request.POST.get("name","").strip()
        gender=request.POST.get("gender","").strip()
        age=request.POST.get("age","").strip()
        phone=request.POST.get("phone","").strip()
        email=request.POST.get("email","").strip()
        procedure=request.POST.get("procedure","").strip()
        procedure_date=request.POST.get("procedure_date","").strip()
        procedure_time=request.POST.get("procedure_time","").strip()
        physician=request.POST.get("physician","").strip()
        suite=request.POST.get("suite","").strip()
        protocol=request.POST.get("protocol","").strip()

        if not all([patient_id_value, name, gender, age, phone, email, procedure, procedure_date, procedure_time, physician, suite, protocol]):
            messages.error(request, "Please fill in all patient fields.")
            return render(request, "patient_form.html", {"mode": "edit", "patient": {"patient_id": patient_id_value, "name": name, "gender": gender, "age": age, "phone": phone, "email": email, "procedure": procedure, "procedure_date": procedure_date, "procedure_time": procedure_time, "physician": physician, "suite": suite, "protocol": protocol}, "patient_id": patient_id})

        custom_patients=get_custom_patients(request)
        existing_patients = {**PATIENTS, **custom_patients}
        if patient_id_value.lower() != patient_id.lower() and patient_id_value.lower() in existing_patients:
            messages.error(request, "A patient with this ID already exists.")
            return render(request, "patient_form.html", {"mode": "edit", "patient": {"patient_id": patient_id_value, "name": name, "gender": gender, "age": age, "phone": phone, "email": email, "procedure": procedure, "procedure_date": procedure_date, "procedure_time": procedure_time, "physician": physician, "suite": suite, "protocol": protocol}, "patient_id": patient_id})

        refreshed = build_patient_payload({
            "patient_id": patient_id_value,
            "name": name,
            "gender": gender,
            "age": age,
            "phone": phone,
            "email": email,
            "procedure": procedure,
            "procedure_time": f"{procedure_date} {procedure_time}",
            "physician": physician,
            "suite": suite,
            "protocol": protocol,
            "steps": patient.get("steps", DEFAULT_PATIENT_STEPS),
        })

        if patient_id.lower() != patient_id_value.lower() and patient_id.lower() in custom_patients:
            del custom_patients[patient_id.lower()]
        custom_patients[patient_id_value.lower()] = refreshed
        save_custom_patients(request, custom_patients)

        messages.success(request, "Patient updated successfully.")
        return redirect("patient_detail", patient_id=patient_id_value.lower())

    form_data = {
        "patient_id": patient.get("id"),
        "name": patient.get("name"),
        "gender": patient.get("gender"),
        "age": patient.get("age"),
        "phone": patient.get("phone"),
        "email": patient.get("email", ""),
        "procedure": patient.get("procedure"),
        "procedure_date": patient.get("procedure_time", "")[:10] if patient.get("procedure_time") and len(patient.get("procedure_time")) >= 10 else "",
        "procedure_time": patient.get("procedure_time", "").split()[-1] if patient.get("procedure_time") and " " in patient.get("procedure_time") else "08:00",
        "physician": patient.get("physician"),
        "suite": patient.get("suite"),
        "protocol": patient.get("protocol", "colonoscopy"),
    }
    return render(request, "patient_form.html", {"mode": "edit", "patient": form_data, "patient_id": patient_id})


@login_required
def delete_patient(request, patient_id):
    patients=get_patient_data(request)
    patient=patients.get((patient_id or "").lower())
    if not patient:
        return render(request, "patient_delete.html", {"patient": None, "patient_id": patient_id})

    if request.method == "POST":
        custom_patients=get_custom_patients(request)
        if patient_id.lower() in custom_patients:
            del custom_patients[patient_id.lower()]
            save_custom_patients(request, custom_patients)
        messages.success(request, "Patient deleted successfully.")
        return redirect("patients")

    return render(request, "patient_delete.html", {"patient": patient, "patient_id": patient_id})


@login_required
def patient_detail(request,patient_id=None):
    patients=get_patient_data(request)
    patient=patients.get((patient_id or "").lower())
    if not patient:
        return render(request,"patient_detail.html",{
            "patient":None,
            "patient_id":patient_id
        })
    return render(request,"patient_detail.html",{
        "patient":patient,
        "patient_id":patient_id
    })

@login_required
def procedures(request):
    patients=get_patient_data(request)
    patient_list=[]
    for patient in patients.values():
        patient_status = patient.get("status", "pending")
        if patient_status == "ready":
            status_label = "✓ Ready"
        elif patient_status == "risk":
            status_label = "⚠ At Risk"
        else:
            status_label = "Pending"

        patient_list.append({
            "id": patient.get("id"),
            "name": patient.get("name"),
            "initials": patient.get("initials"),
            "procedure": patient.get("procedure"),
            "procedure_time": patient.get("procedure_time"),
            "physician": patient.get("physician"),
            "suite": patient.get("suite"),
            "status": patient_status,
            "status_label": status_label,
        })

    return render(request, "procedures.html", {
        "patients": patient_list,
        "total_procedures": len(patient_list),
    })

@login_required
def procedure_timeline(request,patient_id=None):
    timeline_patients={
    "rahul":{
    "name":"Rahul Kumar",
    "procedure":"Colonoscopy",
    "procedure_time":"Tomorrow — 8:00 AM",
    "physician":"Dr. Sharma",
    "suite":"Endo Suite 2",
    "risk":True,
    "steps":[
    {"time":"18:00","name":"Avoid solid foods","status":"confirmed","description":"Patient acknowledged digital meal transition checklist via WhatsApp reply \"1\".","channel":"WhatsApp","sent":"Yesterday 17:30","action":False},
    {"time":"20:00","name":"Take first prep dose","status":"confirmed","description":"First liter of PEG-electrolyte solution consumed smoothly.","channel":"WhatsApp","sent":"Yesterday 19:45","action":False},
    {"time":"02:00","name":"Take second prep dose","status":"risk","description":"Automated micro-reminder sent at 01:45. No confirmation logged by 02:30. Flagged as At Risk.","channel":"SMS","sent":"Today 01:45 (Automated SMS + WhatsApp)","action":True},
    {"time":"05:00","name":"Final confirmation","status":"pending","description":"Final preparation clearance before procedure.","channel":"WhatsApp","sent":"Scheduled: Today 04:45","action":False}
    ]},
    "priya":{
    "name":"Priya Nair",
    "procedure":"Colonoscopy",
    "procedure_time":"Today — 8:30 PM",
    "physician":"Dr. Sharma",
    "suite":"Endo Suite 1",
    "risk":True,
    "steps":[
    {"time":"14:30","name":"Avoid solid foods","status":"confirmed","description":"Patient acknowledged the meal transition checklist.","channel":"WhatsApp","sent":"Today 14:00","action":False},
    {"time":"16:30","name":"Take first prep dose","status":"confirmed","description":"First preparation dose confirmation received.","channel":"WhatsApp","sent":"Today 16:10","action":False},
    {"time":"18:30","name":"Take second prep dose","status":"risk","description":"Automated reminder sent. No confirmation received within the expected window.","channel":"SMS","sent":"Today 18:15 (Automated SMS + WhatsApp)","action":True},
    {"time":"19:30","name":"Final confirmation","status":"pending","description":"Final preparation clearance before procedure.","channel":"WhatsApp","sent":"Scheduled: Today 19:15","action":False}
    ]},
    "ananya":{
    "name":"Ananya Sharma",
    "procedure":"Colonoscopy",
    "procedure_time":"Today — 7:00 PM",
    "physician":"Dr. Sharma",
    "suite":"Endo Suite 1",
    "risk":False,
    "steps":[
    {"time":"13:00","name":"Avoid solid foods","status":"confirmed","description":"Meal transition checklist confirmed.","channel":"WhatsApp","sent":"Today 12:30","action":False},
    {"time":"15:00","name":"Take first prep dose","status":"confirmed","description":"First preparation dose confirmed.","channel":"WhatsApp","sent":"Today 14:40","action":False},
    {"time":"17:00","name":"Take second prep dose","status":"confirmed","description":"Second preparation dose confirmed.","channel":"WhatsApp","sent":"Today 16:40","action":False},
    {"time":"18:00","name":"Final confirmation","status":"confirmed","description":"Final preparation clearance confirmed.","channel":"WhatsApp","sent":"Today 17:45","action":False}
    ]}}

    patient=timeline_patients.get((patient_id or "").lower())

    if not patient:
        return render(request,"procedure_timeline.html",{
            "patient":None,
            "patient_id":patient_id
        })

    patient["steps"]=[step.copy() for step in patient["steps"]]

    actions=request.session.get("timeline_actions",{})
    patient_actions=actions.get((patient_id or "").lower(),{})

    for index,step in enumerate(patient["steps"]):
        saved_action=patient_actions.get(str(index))
        if saved_action:
            if saved_action["status"]=="confirmed":
                step["status"]="confirmed"
                step["action"]=False
                step["description"]=saved_action.get("description",step["description"])
            elif saved_action["status"]=="risk":
                step["status"]="risk"
                step["action"]=True
                step["description"]=saved_action.get("description",step["description"])

    patient["risk"]=any(step["status"]=="risk" for step in patient["steps"])

    return render(request,"procedure_timeline.html",{
        "patient":patient,
        "patient_id":patient_id
    })

@login_required
def confirm_step(request,patient_id,step_index):
    patient_id=patient_id.lower()
    actions=request.session.get("timeline_actions",{})
    patient_actions=actions.setdefault(patient_id,{})
    patient_actions[str(step_index)]={
        "status":"confirmed",
        "description":"Preparation step confirmed by clinic staff."
    }
    request.session["timeline_actions"]=actions
    request.session.modified=True
    return redirect("procedure_timeline",patient_id=patient_id)

@login_required
def undo_step(request,patient_id,step_index):
    patient_id=patient_id.lower()
    actions=request.session.get("timeline_actions",{})
    patient_actions=actions.setdefault(patient_id,{})
    patient_actions[str(step_index)]={
        "status":"risk",
        "description":"Confirmation was undone. Step requires staff attention."
    }
    request.session["timeline_actions"]=actions
    request.session.modified=True
    return redirect("procedure_timeline",patient_id=patient_id)

@login_required
def send_reminder(request,patient_id,step_index):
    patient_id=patient_id.lower()
    actions=request.session.get("timeline_actions",{})
    patient_actions=actions.setdefault(patient_id,{})
    patient_actions[str(step_index)]={
        "status":"risk",
        "description":"Reminder sent by clinic staff. Awaiting patient confirmation."
    }
    request.session["timeline_actions"]=actions
    request.session.modified=True
    return redirect("procedure_timeline",patient_id=patient_id)

@login_required
def protocols(request):
    return render(request,"protocols.html")

@login_required
def protocol_detail(request,protocol_type):
    protocols={
    "colonoscopy":{
    "title":"Colonoscopy Preparation",
    "department":"Gastroenterology",
    "steps":"4 Steps",
    "description":"Standard split-dose bowel lavage preparation protocol",
    "items":[
    ("01","Avoid solid foods","18:00","Patient should transition to the approved clear-liquid diet before the procedure."),
    ("02","Take first prep dose","20:00","First dose of the prescribed bowel preparation solution."),
    ("03","Take second prep dose","02:00","Second preparation dose followed by the required clear-liquid intake."),
    ("04","Final confirmation","05:00","Final preparation clearance before the scheduled procedure.")
    ]},
    "upper-gi":{
    "title":"Upper GI Endoscopy",
    "department":"Gastroenterology",
    "steps":"3 Steps",
    "description":"Gastric emptying fasting protocol for clear visualization and airway safety",
    "items":[
    ("01","Begin fasting","22:00","Stop solid food according to the approved fasting protocol."),
    ("02","Continue clear liquids","05:00","Continue approved clear liquids within the permitted preparation window."),
    ("03","Final confirmation","06:00","Confirm fasting completion before the procedure.")
    ]},
    "sigmoidoscopy":{
    "title":"Flexible Sigmoidoscopy",
    "department":"Colorectal",
    "steps":"3 Steps",
    "description":"Targeted distal bowel evacuation preparation protocol",
    "items":[
    ("01","Light diet","18:00","Follow the approved light-diet instructions before preparation."),
    ("02","Administer enema","06:00","Complete the prescribed bowel evacuation step."),
    ("03","Final confirmation","07:00","Confirm preparation completion before the procedure.")
    ]}}

    protocol=protocols.get(protocol_type,protocols["colonoscopy"])
    return render(request,"protocol_detail.html",{"protocol":protocol})

def login(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method=="POST":
        email=request.POST.get("email","").strip().lower()
        password=request.POST.get("password","")

        user=authenticate(request,username=email,password=password)

        if user is not None:
            auth_login(request,user)
            set_session_user(request, user)
            return redirect("dashboard")

        messages.error(request,"Invalid email or password.")

    return render(request,"login.html")

def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method=="POST":
        name=request.POST.get("name","").strip()
        email=request.POST.get("email","").strip().lower()
        role=request.POST.get("role","clinic_staff")
        password=request.POST.get("password","")
        confirm_password=request.POST.get("confirm_password","")

        if not name or not email or not password or not confirm_password:
            messages.error(request,"Please fill in all required fields.")
            return render(request,"register.html")

        if password!=confirm_password:
            messages.error(request,"Passwords do not match.")
            return render(request,"register.html")

        if len(password)<6:
            messages.error(request,"Password must be at least 6 characters.")
            return render(request,"register.html")

        if role not in ["clinic_staff","doctor"]:
            role="clinic_staff"

        if User.objects.filter(username=email).exists():
            messages.error(request,"An account with this email already exists.")
            return render(request,"register.html")

        user=User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name
        )

        StaffProfile.objects.create(
            user=user,
            role=role
        )

        messages.success(request,"Account created successfully. Please sign in.")
        return redirect("login")

    return render(request,"register.html")

@login_required
def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect("login")