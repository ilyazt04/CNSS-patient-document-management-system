import random
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from doctors.models import Doctor
from patients.models import InsuranceProvider, Patient

User = get_user_model()

FIRST_NAMES_M = ['Youssef', 'Omar', 'Karim', 'Ahmed', 'Rachid', 'Hamza', 'Anas', 'Mehdi', 'Younes', 'Ismail']
FIRST_NAMES_F = ['Fatima', 'Salma', 'Khadija', 'Amina', 'Sara', 'Nadia', 'Zineb', 'Hanane', 'Meryem', 'Imane']
LAST_NAMES = ['Bennani', 'Amrani', 'Idrissi', 'Tazi', 'Fassi', 'Alaoui', 'Chraibi', 'Benjelloun', 'Berrada', 'Squalli']

DOCTORS = [
    {'name': 'Dr. Karim Idrissi', 'specialty': 'Médecine générale', 'contact': '0522-000-001', 'inpe_number': 'INPE001', 'if_number': 'IF001'},
    {'name': 'Dr. Salma Tazi', 'specialty': 'Pédiatrie', 'contact': '0522-000-002', 'inpe_number': 'INPE002', 'if_number': 'IF002'},
    {'name': 'Dr. Omar Fassi', 'specialty': 'Chirurgie générale', 'contact': '0522-000-003', 'inpe_number': 'INPE003', 'if_number': 'IF003'},
    {'name': 'Dr. Nadia Berrada', 'specialty': 'Gynécologie-obstétrique', 'contact': '0522-000-004', 'inpe_number': 'INPE004', 'if_number': 'IF004'},
    {'name': 'Dr. Hamza Squalli', 'specialty': 'Orthopédie', 'contact': '0522-000-005', 'inpe_number': 'INPE005', 'if_number': 'IF005'},
]

INSURANCE_PROVIDERS = ['CNSS', 'CNOPS', 'RMA Assurance', 'AXA Assurance', 'Saham Assurance']


def random_date(start_year=1950, end_year=2015):
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def random_cnss_number():
    return ''.join(str(random.randint(0, 9)) for _ in range(9))


def random_cin_number():
    letter = random.choice('ABCDEFGHJK')
    digits = ''.join(str(random.randint(0, 9)) for _ in range(6))
    return f'{letter}{digits}'


class Command(BaseCommand):
    help = "Seeds demo doctors, insurance providers, and patients for local testing."

    def add_arguments(self, parser):
        parser.add_argument(
            '--patients', type=int, default=20,
            help='Number of demo patients to create (default: 20).',
        )

    def handle(self, *args, **options):
        # --- Users (front-desk accounts) ---
        for username, first, last in [
            ('reception1', 'Fatima', 'Bennani'),
            ('reception2', 'Youssef', 'Amrani'),
        ]:
            user, created = User.objects.get_or_create(
                username=username, defaults={'first_name': first, 'last_name': last},
            )
            if created:
                user.set_password('clinic1234')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Utilisateur créé : {username}'))

        seed_user = User.objects.filter(username='reception1').first()

        # --- Doctors ---
        doctors = []
        for d in DOCTORS:
            doctor, created = Doctor.objects.get_or_create(name=d['name'], defaults=d)
            doctors.append(doctor)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Médecin créé : {doctor.name}'))

        # --- Insurance providers ---
        providers = []
        for name in INSURANCE_PROVIDERS:
            provider, created = InsuranceProvider.objects.get_or_create(name=name)
            providers.append(provider)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Organisme d'assurance créé : {provider.name}"))

        # --- Patients ---
        count_created = 0
        target = options['patients']
        for _ in range(target):
            sex = random.choice(['M', 'F'])
            first_name = random.choice(FIRST_NAMES_M if sex == 'M' else FIRST_NAMES_F)
            last_name = random.choice(LAST_NAMES)
            cnss_number = random_cnss_number()

            # Avoid collisions if the command is re-run
            if Patient.objects.filter(cnss_number=cnss_number).exists():
                continue

            relationship = random.choices(
                ['SELF', 'CHILD', 'SPOUSE'], weights=[0.7, 0.2, 0.1],
            )[0]

            patient = Patient(
                first_name=first_name,
                last_name=last_name,
                cnss_number=cnss_number,
                cin_number=random_cin_number(),
                date_of_birth=random_date(),
                address=f'{random.randint(1, 200)} Rue {random.choice(LAST_NAMES)}, Tanger',
                doctor=random.choice(doctors),
                insurance_provider=random.choice(providers),
                relationship_to_insured=relationship,
                created_by=seed_user,
                updated_by=seed_user,
            )

            if relationship != 'SELF':
                insured_first = random.choice(FIRST_NAMES_M + FIRST_NAMES_F)
                patient.insured_first_name = insured_first
                patient.insured_last_name = last_name
                patient.insured_cnss_number = random_cnss_number()
                patient.insured_cin_number = random_cin_number()
                patient.insured_address = patient.address
                patient.insured_affiliation_country = 'Maroc'

            patient.save()
            count_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Terminé : {len(doctors)} médecins, {len(providers)} organismes, {count_created} patients créés.'
        ))