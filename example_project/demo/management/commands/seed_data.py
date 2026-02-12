"""
Management command to seed the database with benchmark data.

Usage:
    python manage.py seed_data [--tags N] [--wide N] [--departments N] [--teams-per-dept N] [--employees-per-team N] [--clear]

All counts have sensible defaults for benchmarking:
    --tags              100
    --wide              100
    --departments       5
    --teams-per-dept    4
    --employees-per-team 10
    --clear             Drop all demo data before seeding
"""

import random
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from django.core.management.base import BaseCommand

from demo.models import Department, Employee, Tag, Team, WideModel

RANDOM_SEED = 42


class Command(BaseCommand):
    help = "Seed database with demo/benchmark data."

    def add_arguments(self, parser):
        parser.add_argument("--tags", type=int, default=100)
        parser.add_argument("--wide", type=int, default=100)
        parser.add_argument("--departments", type=int, default=5)
        parser.add_argument("--teams-per-dept", type=int, default=4)
        parser.add_argument("--employees-per-team", type=int, default=10)
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all demo data before seeding.",
        )

    def handle(self, **options):
        rng = random.Random(RANDOM_SEED)

        if options["clear"]:
            self.stdout.write("Clearing existing demo data...")
            Employee.objects.all().delete()
            Team.objects.all().delete()
            Department.objects.all().delete()
            WideModel.objects.all().delete()
            Tag.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared."))

        self._seed_tags(options["tags"], rng)
        self._seed_wide(options["wide"], rng)
        self._seed_hierarchy(
            options["departments"],
            options["teams_per_dept"],
            options["employees_per_team"],
            rng,
        )

        self.stdout.write(self.style.SUCCESS("Seeding complete."))

    def _seed_tags(self, count, rng):
        existing = set(Tag.objects.values_list("name", flat=True))
        tags = []
        for i in range(count):
            name = f"tag-{i:04d}"
            if name not in existing:
                tags.append(Tag(name=name))
        Tag.objects.bulk_create(tags, ignore_conflicts=True)
        self.stdout.write(f"  Tags: {Tag.objects.count()} total")

    def _seed_wide(self, count, rng):
        existing_count = WideModel.objects.count()
        if existing_count >= count:
            self.stdout.write(f"  WideModel: {existing_count} total (already seeded)")
            return
        batch = []
        for i in range(existing_count, count):
            batch.append(
                WideModel(
                    char_field=f"char-{i:04d}",
                    text_field=f"Lorem ipsum text block {i}",
                    slug_field=f"slug-{i:04d}",
                    email_field=f"user{i}@example.com",
                    url_field=f"https://example.com/{i}",
                    ip_field=f"192.168.{rng.randint(0,255)}.{rng.randint(1,254)}",
                    int_field=rng.randint(-10000, 10000),
                    bigint_field=rng.randint(0, 10**12),
                    smallint_field=rng.randint(-100, 100),
                    pos_int_field=rng.randint(0, 100000),
                    float_field=rng.uniform(-1000.0, 1000.0),
                    decimal_field=Decimal(str(round(rng.uniform(0, 99999), 4))),
                    bool_field=rng.choice([True, False]),
                    date_field=date(2020, 1, 1) + timedelta(days=rng.randint(0, 1500)),
                    datetime_field=datetime(
                        2020, 1, 1, tzinfo=timezone.utc
                    ) + timedelta(seconds=rng.randint(0, 86400 * 1500)),
                    time_field=time(rng.randint(0, 23), rng.randint(0, 59)),
                    duration_field=timedelta(seconds=rng.randint(0, 86400)),
                    uuid_field=uuid.UUID(int=rng.getrandbits(128)),
                    json_field={"key": f"value-{i}", "nested": {"a": rng.randint(0, 100)}},
                )
            )
        WideModel.objects.bulk_create(batch)
        self.stdout.write(f"  WideModel: {WideModel.objects.count()} total")

    def _seed_hierarchy(self, dept_count, teams_per, employees_per, rng):
        if Department.objects.count() >= dept_count:
            self.stdout.write(
                f"  Departments: {Department.objects.count()}, "
                f"Teams: {Team.objects.count()}, "
                f"Employees: {Employee.objects.count()} (already seeded)"
            )
            return
        first_names = [
            "Alice", "Bob", "Carol", "Dave", "Eve", "Frank",
            "Grace", "Hank", "Ivy", "Jack", "Kara", "Leo",
        ]
        last_names = [
            "Smith", "Jones", "Brown", "Davis", "Wilson",
            "Clark", "Lewis", "Young", "Hall", "Allen",
        ]

        for d in range(dept_count):
            dept = Department.objects.create(
                name=f"Department {d}",
                code=f"DEPT-{d:03d}",
                budget=Decimal(str(rng.randint(100000, 10000000))),
                is_active=True,
            )
            for t in range(teams_per):
                team = Team.objects.create(
                    name=f"Team {d}-{t}",
                    department=dept,
                    focus_area=rng.choice(
                        ["Backend", "Frontend", "Data", "DevOps", "QA"]
                    ),
                )
                emps = []
                for e in range(employees_per):
                    fn = rng.choice(first_names)
                    ln = rng.choice(last_names)
                    emps.append(
                        Employee(
                            first_name=fn,
                            last_name=ln,
                            email=f"{fn.lower()}.{ln.lower()}.{d}.{t}.{e}@example.com",
                            team=team,
                            hire_date=date(2018, 1, 1)
                            + timedelta(days=rng.randint(0, 2000)),
                            salary=Decimal(str(rng.randint(50000, 200000))),
                            is_manager=(e == 0),
                            metadata={"level": rng.randint(1, 5)},
                        )
                    )
                Employee.objects.bulk_create(emps)

        self.stdout.write(
            f"  Departments: {Department.objects.count()}, "
            f"Teams: {Team.objects.count()}, "
            f"Employees: {Employee.objects.count()}"
        )
