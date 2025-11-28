"""
Create test projects and leads
Run: python create_projects_and_leads.py
"""
import os
import django
from datetime import datetime, timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from accounts.models import User
from projects.models import Project, ProjectConfiguration
from leads.models import Lead
from channel_partners.models import ChannelPartner

# Get users
mandate_owner = User.objects.filter(role='mandate_owner').first()
site_head1 = User.objects.filter(username='sitehead1').first()
site_head2 = User.objects.filter(username='sitehead2').first()

if not mandate_owner:
    print("[ERROR] No Mandate Owner found. Please create a Mandate Owner first.")
    exit(1)

print("=" * 60)
print("Creating Projects and Leads")
print("=" * 60)

# Create projects
projects_data = [
    {
        'name': 'Green Valley Residency',
        'builder_name': 'Green Builders Pvt Ltd',
        'location': 'Andheri West, Mumbai',
        'rera_id': 'P52100001234',
        'project_type': 'residential',
        'starting_price': 8500000,
        'number_of_towers': 3,
        'floors_per_tower': 15,
        'units_per_floor': 4,
        'has_commercial': True,
        'commercial_floors': 2,
        'commercial_units_per_floor': 6,
        'site_head': site_head1,
    },
    {
        'name': 'Luxury Heights',
        'builder_name': 'Premium Developers',
        'location': 'Powai, Mumbai',
        'rera_id': 'P52100005678',
        'project_type': 'residential',
        'starting_price': 12000000,
        'number_of_towers': 2,
        'floors_per_tower': 20,
        'units_per_floor': 3,
        'has_commercial': False,
        'commercial_floors': 0,
        'commercial_units_per_floor': 0,
        'site_head': site_head2,
    },
    {
        'name': 'Business Hub Commercial',
        'builder_name': 'Commercial Spaces Ltd',
        'location': 'Bandra Kurla Complex, Mumbai',
        'rera_id': 'P52100009876',
        'project_type': 'commercial',
        'starting_price': 25000000,
        'number_of_towers': 1,
        'floors_per_tower': 10,
        'units_per_floor': 8,
        'has_commercial': True,
        'commercial_floors': 10,
        'commercial_units_per_floor': 8,
        'site_head': site_head1,
    },
]

created_projects = []
for proj_data in projects_data:
    if Project.objects.filter(name=proj_data['name']).exists():
        project = Project.objects.get(name=proj_data['name'])
        print(f"[SKIP] Project {proj_data['name']} already exists, using existing...")
    else:
        project = Project.objects.create(
            mandate_owner=mandate_owner,
            **{k: v for k, v in proj_data.items() if k != 'site_head'},
            site_head=proj_data.get('site_head'),
            is_active=True
        )
        print(f"[OK] Created Project: {project.name}")
    
    # Add configurations
    configs = ['1BHK', '2BHK', '3BHK', '4BHK']
    for config_name in configs:
        if not ProjectConfiguration.objects.filter(project=project, name=config_name).exists():
            ProjectConfiguration.objects.create(project=project, name=config_name)
    
    created_projects.append(project)

print(f"\n[OK] Created/Updated {len(created_projects)} projects")

# Create Channel Partners
cp_data = [
    {'firm_name': 'Mumbai Realty', 'cp_name': 'Rajesh Kumar', 'phone': '9876543210'},
    {'firm_name': 'Property Solutions', 'cp_name': 'Priya Sharma', 'phone': '9876543211'},
    {'firm_name': 'Dream Homes Agency', 'cp_name': 'Amit Patel', 'phone': '9876543212'},
]

cps = []
for cp_info in cp_data:
    cp, created = ChannelPartner.objects.get_or_create(
        phone=cp_info['phone'],
        defaults={
            'firm_name': cp_info['firm_name'],
            'cp_name': cp_info['cp_name'],
            'is_active': True
        }
    )
    if created:
        print(f"[OK] Created CP: {cp.cp_name} ({cp.firm_name})")
    cps.append(cp)

# Create leads
lead_names = [
    ('Rahul Sharma', '9876500001', 'rahul.sharma@email.com'),
    ('Priya Patel', '9876500002', 'priya.patel@email.com'),
    ('Amit Kumar', '9876500003', 'amit.kumar@email.com'),
    ('Sneha Desai', '9876500004', 'sneha.desai@email.com'),
    ('Vikram Singh', '9876500005', 'vikram.singh@email.com'),
    ('Anjali Mehta', '9876500006', 'anjali.mehta@email.com'),
    ('Rohit Gupta', '9876500007', 'rohit.gupta@email.com'),
    ('Kavita Joshi', '9876500008', 'kavita.joshi@email.com'),
    ('Manish Shah', '9876500009', 'manish.shah@email.com'),
    ('Divya Reddy', '9876500010', 'divya.reddy@email.com'),
    ('Suresh Nair', '9876500011', 'suresh.nair@email.com'),
    ('Meera Iyer', '9876500012', 'meera.iyer@email.com'),
    ('Arjun Menon', '9876500013', 'arjun.menon@email.com'),
    ('Pooja Nair', '9876500014', 'pooja.nair@email.com'),
    ('Karan Malhotra', '9876500015', 'karan.malhotra@email.com'),
]

statuses = ['new', 'contacted', 'visit_scheduled', 'visit_completed', 'discussion', 'hot']
purposes = ['investment', 'first_home', 'second_home', 'retirement_home']
occupations = ['self_emp', 'service', 'business', 'homemaker']

sourcing_manager = User.objects.filter(role='sourcing_manager').first()
closer = User.objects.filter(role='closing_manager').first()

created_leads = []
for i, (name, phone, email) in enumerate(lead_names):
    project = random.choice(created_projects)
    cp = random.choice(cps) if random.random() > 0.3 else None  # 70% have CP
    
    # Some leads are pretagged
    is_pretagged = random.random() > 0.6  # 40% are pretagged
    
    lead = Lead.objects.create(
        name=name,
        phone=phone,
        email=email,
        project=project,
        configuration=project.configurations.first() if project.configurations.exists() else None,
        budget=random.randint(5000000, 20000000),
        purpose=random.choice(purposes),
        occupation=random.choice(occupations),
        status=random.choice(statuses),
        channel_partner=cp,
        cp_firm_name=cp.firm_name if cp else '',
        cp_name=cp.cp_name if cp else '',
        cp_phone=cp.phone if cp else '',
        is_pretagged=is_pretagged,
        pretag_status='pending_verification' if is_pretagged else '',
        phone_verified=False if is_pretagged else random.choice([True, False]),
        created_by=sourcing_manager if is_pretagged else (sourcing_manager if sourcing_manager else None),
        created_at=datetime.now() - timedelta(days=random.randint(0, 30)),
    )
    created_leads.append(lead)

print(f"\n[OK] Created {len(created_leads)} leads")
print(f"\nSummary:")
print(f"   Projects: {len(created_projects)}")
print(f"   Leads: {len(created_leads)}")
print(f"   Channel Partners: {len(cps)}")
print(f"   Pretagged Leads: {sum(1 for l in created_leads if l.is_pretagged)}")

print("\n" + "=" * 60)
print("[SUCCESS] DONE! Projects and leads created successfully!")
print("=" * 60)

